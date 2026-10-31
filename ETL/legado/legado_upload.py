import os
import boto3
from botocore.exceptions import ClientError

# ==========================================
# CONFIGURAÇÕES
# ==========================================
AWS_PROFILE = "dados"
BUCKET_NAME = "pos-graduacao-lakehouse-km"
S3_PREFIX = "legado"

LOCAL_BASE_PATH = "C:/Users/User/Documents"
FILE_NAME = "Base_2.xlsx"
# LOCAL_BASE_PATH = "eti_engenharia_dados"

LOCAL_FILE_PATH = os.path.join(LOCAL_BASE_PATH, FILE_NAME)
S3_KEY = f"{S3_PREFIX}/{FILE_NAME}"

# ==========================================
# FUNÇÕES
# ==========================================
def upload_file_to_s3(local_path, bucket, s3_key):
    session = boto3.Session(profile_name=AWS_PROFILE)
    s3_client = session.client("s3")
    
    try:
        print(f"[INFO] Iniciando upload do arquivo:")
        print(f"  Origem: {local_path}")
        print(f"  Destino: {s3_key}")
        
        s3_client.upload_file(local_path, bucket, s3_key)
        
        print('[SUCCESS] Upload realizado com sucesso!')
    except ClientError as e:
        print(f"[ERROR] Erro ao realizar upload: {e}")
        return False
    return True

# ==========================================
# EXECUÇÃO
# ==========================================
if __name__ == "__main__":
    if not os.path.exists(LOCAL_FILE_PATH):
        raise FileNotFoundError(
            f"Arquivo não encontrado em: {LOCAL_FILE_PATH}"
        )
        
    upload_file_to_s3(
        local_path=LOCAL_FILE_PATH,
        bucket=BUCKET_NAME,
        s3_key=S3_KEY
    )
