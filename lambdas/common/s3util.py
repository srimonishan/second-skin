"""Thin S3 helpers. Bucket name comes from an env var wired in by CDK."""
import json
import os

import boto3
from botocore.exceptions import ClientError

_client = None


def _s3():
    global _client
    if _client is None:
        _client = boto3.client("s3", region_name=os.environ.get("AWS_REGION"))
    return _client


def bucket_name() -> str:
    return os.environ["ASSETS_BUCKET_NAME"]


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    _s3().put_object(Bucket=bucket_name(), Key=key, Body=data, ContentType=content_type)


def put_json(key: str, obj) -> None:
    put_bytes(key, json.dumps(obj, indent=2).encode("utf-8"), "application/json")


def get_bytes(key: str) -> bytes:
    resp = _s3().get_object(Bucket=bucket_name(), Key=key)
    return resp["Body"].read()


def object_exists(key: str) -> bool:
    try:
        _s3().head_object(Bucket=bucket_name(), Key=key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def public_url(key: str) -> str:
    region = os.environ.get("AWS_REGION", "us-east-1")
    return f"https://{bucket_name()}.s3.{region}.amazonaws.com/{key}"
