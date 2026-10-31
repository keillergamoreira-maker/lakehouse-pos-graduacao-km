import os
import pandas as pd
import boto3
import tempfile
from datetime import datetime
import unicodedata

# ==========================================
# CONFIGURAÇÕES
# ==========================================
AWS_PROFILE = "dados"
BUCKET_NAME = "pos-graduacao-lakehouse-km"

RAW_PREFIX = "raw/base_dados/"
TRUSTED_PREFIX = "trusted/base_dados"

# ==========================================
# FUNÇÃO: NORMALIZAR COLUNAS
# ==========================================
def normalize_column(col):
    col = col.strip().lower()
    col = unicodedata.normalize('NFKD', col)
    col = col.encode('ascii', 'ignore').decode('utf-8')
    col = col.replace(" ", "_")
    return col

# ==========================================
# SESSÃO AWS
# ==========================================
session = boto3.Session(profile_name=AWS_PROFILE)
s3_client = session.client('s3')

# ==========================================
# BUSCAR ÚLTIMO ARQUIVO RAW
# ==========================================
objects = s3_client.list_objects_v2(
    Bucket=BUCKET_NAME,
    Prefix=RAW_PREFIX
).get('Contents', [])

if not objects:
    raise Exception("Nenhum arquivo encontrado na camada RAW")

latest_object = max(objects, key=lambda x: x['LastModified'])
latest_key = latest_object['Key']

print(f"[INFO] Último arquivo RAW encontrado: {latest_key}")
print(f"s3://{BUCKET_NAME}/{latest_key}")

# ==========================================
# DOWNLOAD E LEITURA DO EXCEL
# ==========================================
tmp_excel = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
tmp_excel_path = tmp_excel.name
tmp_excel.close()  # Fecha o arquivo para permitir que o S3 e o Pandas escrevam/leiam nele

try:
    print("[INFO] Baixando arquivo do S3...")
    s3_client.download_file(BUCKET_NAME, latest_key, tmp_excel_path)
    
    print("[INFO] Carregando dados no Pandas...")
    df = pd.read_excel(tmp_excel_path)
    
    # Normalizar o nome das colunas antes do tratamento (para garantir letras minúsculas e sem espaços)
    df.columns = [normalize_column(col) for col in df.columns]

finally:
    # Garante a remoção do arquivo temporário do seu computador após o uso
    if os.path.exists(tmp_excel_path):
        os.unlink(tmp_excel_path)


# ==========================================
# TRATAMENTO DE DATAS
# ==========================================
df['dataemissao_dt'] = pd.to_datetime(df['dataemissao'], errors='coerce')
df['datavencimento_dt'] = pd.to_datetime(df['datavencimento'], errors='coerce')

# Data final como STRING (SEM AMBIGUIDADE)
df['dataemissao'] = df['dataemissao_dt'].dt.strftime('%Y-%m-%d %H:%M:%S')
df['datavencimento'] = df['datavencimento_dt'].dt.strftime('%Y-%m-%d %H:%M:%S')

df = df.drop(columns=['dataemissao_dt', 'datavencimento_dt'])

# ==========================================
# TIPAGEM DE DADOS
# ==========================================
df['qtditens'] = pd.to_numeric(df['qtditens'], errors='coerce')
df['valorunitario'] = pd.to_numeric(df['valorunitario'], errors='coerce')
df['peso_liquido'] = pd.to_numeric(df['peso_liquido'], errors='coerce')

df['nfe'] = df['nfe'].astype(str)
df['cliente'] = df['cliente'].astype(str)    # <-- Alterado para 'cliente'
df['vendedor'] = df['vendedor'].astype(str)  # <-- Alterado para 'vendedor'

# ==========================================
# COLUNAS TÉCNICAS
# ==========================================
df['data_ingestao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ==========================================
# PARTICIONAMENTO (USANDO dataemissao_dt)
# ==========================================
df['ano'] = pd.to_datetime(df['dataemissao']).dt.year
df['mes'] = pd.to_datetime(df['dataemissao']).dt.month
df['dia'] = pd.to_datetime(df['dataemissao']).dt.day

# --- ADICIONE ESTAS TRÊS LINHAS DE DIAGNÓSTICO AQUI ---
print(f"[DEBUG] Total de linhas no Excel: {len(df)}")
print(f"[DEBUG] Quantidade de linhas com datas válidas: {df['ano'].notna().sum()}")
print(f"[DEBUG] Anos encontrados para particionar: {df['ano'].dropna().unique()}")

# ==========================================
# ESCRITA PARQUET + UPLOAD (GARANTA QUE ESTE BLOCO ESTEJA AQUI)
# ==========================================
tmp_dir = tempfile.mkdtemp()

print("[INFO] Criando partições Parquet e enviando para a camada TRUSTED...")

# Agrupa e remove nulos para evitar erros de ponto flutuante nos nomes das pastas
df_valid = df.dropna(subset=['ano', 'mes', 'dia'])

for (ano, mes, dia), df_group in df_valid.groupby(["ano", "mes", "dia"]):
    # Força os valores a virarem inteiros para a pasta não ficar como 'ano=2017.0'
    ano_int = int(ano)
    mes_int = int(mes)
    dia_int = int(dia)
    
    partition_path = f"{TRUSTED_PREFIX}/ano={ano_int}/mes={mes_int:02d}/dia={dia_int:02d}"
    s3_key = f"{partition_path}/dados_tratados.parquet"
    
    local_file_name = f"trusted_{ano_int}_{mes_int:02d}_{dia_int:02d}.parquet"
    local_file_path = os.path.join(tmp_dir, local_file_name)
    
    try:
        df_group.to_parquet(local_file_path, index=False)
        s3_client.upload_file(local_file_path, BUCKET_NAME, s3_key)
        print(f"[SUCCESS] Enviado: s3://{BUCKET_NAME}/{s3_key}")
        
    except Exception as e:
        print(f"[ERROR] Falha ao enviar partição ano={ano_int}/mes={mes_int}/dia={dia_int}")
        raise e
    finally:
        if os.path.exists(local_file_path):
            os.unlink(local_file_path)

os.rmdir(tmp_dir)
print("[INFO] Processo de ETL para a camada TRUSTED concluído com sucesso!")