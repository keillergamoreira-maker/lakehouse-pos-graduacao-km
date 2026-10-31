import os
import time
import pandas as pd
import boto3
from pathlib import Path

# ==========================================
# CONFIGURAÇÕES GERAIS
# ==========================================
AWS_PROFILE = "etl_engenharia_dados"
AWS_REGION = "us-east-2"

ATHENA_DATABASE = "lakehouse-curated"
ATHENA_OUTPUT = "s3://pos-graduacao-lakehouse-km/athena-query-results/"

CURATED_BUCKET = "pos-graduacao-lakehouse-km"
CURATED_BASE_PREFIX = "curated"

POLL_INTERVAL_SECONDS = 2

# ==========================================
# CAMINHOS PATH DO PROJETO
# ==========================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SQL_FOLDER = PROJECT_ROOT / "sql" / "curated_ctas"

# ==========================================
# SESSÃO AWS
# ==========================================
session = boto3.Session(
    profile_name=AWS_PROFILE,
    region_name=AWS_REGION
)
athena_client = session.client('athena')
s3_client = session.client('s3')

# ==========================================
# FUNÇÃO: LIMPAR PREFIXO S3
# ==========================================
def limpar_s3_prefix(bucket: str, prefix: str):
    print(f"Limpar S3: s3://{bucket}/{prefix}")
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    
    objects_to_delete = []
    
    for page in pages:
        if "Contents" in page:
            for obj in page["Contents"]:
                objects_to_delete.append({"Key": obj["Key"]})
                
    if objects_to_delete:
        s3_client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": objects_to_delete}
        )
        print(f"Dados antigos removidos do S3")
    else:
        print("Nenhum dado antigo encontrado no S3")

# ==========================================
# FUNÇÃO: EXECUTAR SQL (COMPLETA)
# ==========================================
def executar_ctas(sql_file: Path):
    table_name = sql_file.stem
    print(f"\n[EXECUÇÃO] Iniciando processamento da tabela: {table_name}")
    
    # 1. Limpa o diretório de destino na camada Curated antes de rodar a CTAS
    prefix_destino = f"{CURATED_BASE_PREFIX}/{table_name}/"
    limpar_s3_prefix(CURATED_BUCKET, prefix_destino)
    
    # 2. Dropa a tabela antiga do catálogo para evitar o erro TABLE_ALREADY_EXISTS
    print(f"Removendo metadados da tabela antiga no catálogo do Athena: {table_name}")
    query_drop = f'DROP TABLE IF EXISTS {table_name}'
    try:
        drop_response = athena_client.start_query_execution(
            QueryString=query_drop,
            QueryExecutionContext={'Database': ATHENA_DATABASE},
            ResultConfiguration={'OutputLocation': ATHENA_OUTPUT}
        )
        drop_id = drop_response['QueryExecutionId']
        
        # Aguarda a tabela sumir de fato do catálogo antes de prosseguir
        while True:
            drop_status = athena_client.get_query_execution(QueryExecutionId=drop_id)['QueryExecution']['Status']['State']
            if drop_status in ['SUCCEEDED']:
                print(f"Tabela antiga removida do catálogo.")
                break
            elif drop_status in ['FAILED', 'CANCELLED']:
                print(f"Aviso: Não foi possível dropar a tabela via catálogo (pode não existir ainda).")
                break
            time.sleep(POLL_INTERVAL_SECONDS)
    except Exception as e:
        print(f"Aviso ao tentar executar DROP TABLE: {e}")

    # 3. Lê o conteúdo do arquivo SQL
    with open(sql_file, "r", encoding="utf-8") as f:
        query_contingency = f.read()
        
    # 4. Dispara a execução da Query no Athena (CTAS)
    response = athena_client.start_query_execution(
        QueryString=query_contingency,
        QueryExecutionContext={'Database': ATHENA_DATABASE},
        ResultConfiguration={'OutputLocation': ATHENA_OUTPUT}
    )
    
    query_execution_id = response['QueryExecutionId']
    print(f"Query CTAS disparada no Athena. ID: {query_execution_id}")
    
    # 5. Loop de checagem (Poll) para aguardar a finalização da query
    while True:
        status_response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        status = status_response['QueryExecution']['Status']['State']
        
        if status in ['SUCCEEDED']:
            print(f"CTAs concluída com sucesso: {table_name}")
            break
        elif status in ['FAILED', 'CANCELLED']:
            reason = status_response['QueryExecution']['Status'].get('StateChangeReason', 'Sem motivo especificado')
            raise Exception(f"Erro ao executar a query da tabela {table_name}. Status: {status}. Motivo: {reason}")
            
        time.sleep(POLL_INTERVAL_SECONDS)

# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("INÍCIO PIPELINE CURATED")
    print("="*50 + "\n")
    
    if not SQL_FOLDER.exists():
        raise FileNotFoundError(f"Pasta SQL não encontrada: {SQL_FOLDER}")
        
    sql_files = sorted(SQL_FOLDER.glob("*.sql"))
    
    if not sql_files:
        raise Exception("Nenhum arquivo SQL encontrado")
        
    print(f"Pasta de SQL encontrada: {SQL_FOLDER}")
    print(f"CTAs encontradas: {len(sql_files)}")
    
    for sql_file in sql_files:
        executar_ctas(sql_file)
        
    print("\n" + "="*50)
    print("PIPELINE CURATED FINALIZADO COM SUCESSO")
    print("="*50 + "\n")
