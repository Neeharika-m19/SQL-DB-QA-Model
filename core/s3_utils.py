# core/s3_utils.py

import boto3
import json
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from typing import List
from datetime import datetime

# Load environment variables
load_dotenv()

# Set up static S3 client and bucket name
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = "db-llm-1"  # Replace this with your actual S3 bucket name

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)


def save_query_to_s3(user_id: int, query_key: str, question: str, sql_query: str, answer: str):
    file_path = f"saved_queries/{user_id}/{query_key}.json"

    payload = {
        "question": question,
        "sql_query": sql_query,
        "answer": answer,
        "timestamp": datetime.utcnow().isoformat()
    }

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=file_path,
        Body=json.dumps(payload),
        ContentType="application/json"
    )


def list_saved_queries_from_s3(user_id: int) -> List[str]:
    prefix = f"saved_queries/{user_id}/"
    results = []

    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        for obj in response.get("Contents", []):
            key = obj["Key"]
            file_content = s3.get_object(Bucket=BUCKET_NAME, Key=key)["Body"].read().decode("utf-8")
            parsed = json.loads(file_content)

            question = parsed.get("question", "Unknown question")
            sql_query = parsed.get("sql_query", "Unknown SQL query")
            answer = parsed.get("answer", "No answer")

            # Format answer summary
            if isinstance(answer, list):
                answer_summary = f"{len(answer)} rows returned"
                if len(answer) > 0 and isinstance(answer[0], dict):
                    first_col = list(answer[0].keys())[0]
                    values = [row[first_col] for row in answer[:3]]  # show top 3
                    answer_summary += f": " + ", ".join(map(str, values))
            else:
                answer_summary = str(answer)

            sentence = f"For the question **'{question}'**, the generated SQL was **`{sql_query}`**, and the answer was **{answer_summary}**."
            results.append(sentence)

    except ClientError as e:
        raise RuntimeError(f"Error listing queries from S3: {e}")

    return results


def delete_query_from_s3(user_id: int, query_key: str):
    file_path = f"saved_queries/{user_id}/{query_key}.json"
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=file_path)
        return f"Query {query_key} deleted from S3 for user {user_id}"
    except ClientError as e:
        raise RuntimeError(f"Error deleting query from S3: {e}")
