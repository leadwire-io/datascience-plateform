from minio import Minio
from minio.error import S3Error
import os

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS   = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET   = os.getenv("MINIO_SECRET_KEY", "Minio@2026!")
MINIO_SECURE   = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Quota par utilisateur en octets (défaut: 5 GB)
USER_QUOTA_BYTES = int(os.getenv("USER_QUOTA_BYTES", str(5 * 1024 * 1024 * 1024)))

def get_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=MINIO_SECURE
    )

def ensure_bucket(username):
    client = get_client()
    bucket = f"user-{username}"
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            print(f"Bucket créé : {bucket}")
    except S3Error as e:
        print(f"MinIO error: {e}")

def get_bucket_size(username):
    """Retourne la taille totale du bucket en octets."""
    client = get_client()
    bucket = f"user-{username}"
    total  = 0
    try:
        objects = client.list_objects(bucket, recursive=True)
        for obj in objects:
            total += obj.size
    except S3Error:
        pass
    return total

def get_storage_info(username):
    """Retourne les infos de stockage de l'utilisateur."""
    used  = get_bucket_size(username)
    quota = USER_QUOTA_BYTES
    pct   = round(used / quota * 100, 1) if quota > 0 else 0

    return {
        "used_bytes":  used,
        "quota_bytes": quota,
        "used_gb":     round(used / (1024**3), 2),
        "quota_gb":    round(quota / (1024**3), 2),
        "percent":     pct,
        "exceeded":    used >= quota,
        "warning":     pct >= 80,
    }
