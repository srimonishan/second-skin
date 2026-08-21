"""
Thin DynamoDB helpers. Table names come from environment variables wired in
by CDK (see infra/.../constructs/lambdas.py) -- never hardcoded here.
"""
import os
import time
import uuid
from decimal import Decimal

import boto3

_resource = None


def _ddb():
    global _resource
    if _resource is None:
        _resource = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION"))
    return _resource


def designs_table():
    return _ddb().Table(os.environ["DESIGNS_TABLE_NAME"])


def words_table():
    return _ddb().Table(os.environ["WORDS_TABLE_NAME"])


def put_design(item: dict) -> None:
    designs_table().put_item(Item=item)


def get_design(date: str) -> dict | None:
    resp = designs_table().get_item(Key={"date": date})
    return resp.get("Item")


def recent_style_notes(limit: int = 10) -> list[str]:
    """
    Style memory is derived, not stored separately: scan SecondSkinDesigns
    (trivially small at this project's data volume) and return the most
    recent `styleNote` values, oldest-first, so the brief prompt reads them
    as a chronological progression.
    """
    resp = designs_table().scan(ProjectionExpression="#d, styleNote", ExpressionAttributeNames={"#d": "date"})
    items = [i for i in resp.get("Items", []) if i.get("styleNote")]
    items.sort(key=lambda i: i["date"])
    return [i["styleNote"] for i in items[-limit:]]


def all_designs() -> list[dict]:
    """Full table scan, newest-first. Fine at this project's data volume (one item/day)."""
    items = []
    resp = designs_table().scan()
    items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = designs_table().scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    items.sort(key=lambda i: i["date"], reverse=True)
    return items


def latest_design() -> dict | None:
    resp = designs_table().scan(ProjectionExpression="#d, imageKey, imageGenerated", ExpressionAttributeNames={"#d": "date"})
    items = resp.get("Items", [])
    if not items:
        return None
    items.sort(key=lambda i: i["date"])
    return items[-1]


def submit_word(word: str, status: str, reason: str | None = None) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "word": word,
        "status": status,
        "submittedAt": Decimal(str(time.time())),
    }
    if reason:
        item["moderationReason"] = reason
    words_table().put_item(Item=item)
    return item


def oldest_pending_word() -> dict | None:
    resp = words_table().query(
        IndexName="StatusIndex",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("status").eq("pending"),
        Limit=1,
        ScanIndexForward=True,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def mark_word_used(word_id: str) -> None:
    words_table().update_item(
        Key={"id": word_id},
        UpdateExpression="SET #s = :used",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":used": "used"},
    )
