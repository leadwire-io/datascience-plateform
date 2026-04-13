from minio import Minio
import os

mc = Minio(
    os.getenv("MINIO_ENDPOINT", "minio:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "admin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "Minio@2026!"),
    secure=os.getenv("MINIO_SECURE", "false").lower() == "true"
)

def ensure_bucket(username):
    bucket = f"user-{username}"
    try:
        if not mc.bucket_exists(bucket):
            mc.make_bucket(bucket)
            print(f"Bucket {bucket} cree")
    except Exception as e:
        print(f"MinIO error: {e}")
