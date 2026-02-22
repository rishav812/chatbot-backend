import os

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def upload_pdf(file_bytes: bytes, file_name: str) -> str:
    """
    Upload a PDF to S3.

    Args:
        file_bytes: Raw PDF content.
        file_name: Object key / filename in the bucket.

    Returns:
        The S3 object key of the uploaded file.
    """
    try:
        s3_client.put_object(
            Bucket=AWS_S3_BUCKET,
            Key=file_name,
            Body=file_bytes,
            ContentType="application/pdf",
        )
        return file_name
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}") from e


def download_pdf(key: str) -> bytes:
    """
    Download a PDF from S3.

    Args:
        key: The S3 object key.

    Returns:
        Raw bytes of the PDF file.
    """
    try:
        response = s3_client.get_object(Bucket=AWS_S3_BUCKET, Key=key)
        return response["Body"].read()
    except ClientError as e:
        raise RuntimeError(f"S3 download failed: {e}") from e


def list_pdfs() -> list[dict]:
    """List all objects in the S3 bucket."""
    try:
        response = s3_client.list_objects_v2(Bucket=AWS_S3_BUCKET)
        contents = response.get("Contents", [])
        return [{"key": obj["Key"], "size": obj["Size"]} for obj in contents]
    except ClientError as e:
        raise RuntimeError(f"S3 list failed: {e}") from e
