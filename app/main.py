import os
from fastapi import FastAPI
import psycopg2
import redis

app = FastAPI(title="Base Docker Environment")

@app.get("/")
def read_root():
    return {"status": "running", "environment": "docker"}

@app.get("/health")
def health_check():
    db_status = "unknown"
    cache_status = "unknown"

    # Проверка подключения к PostgreSQL
    try:
        conn = psycopg2.connect(
            host="db",
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            connect_timeout=3
        )
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Проверка подключения к Redis
    try:
        r = redis.Redis(
            host="cache",
            port=int(os.getenv("REDIS_PORT", 6379)),
            socket_timeout=3
        )
        if r.ping():
            cache_status = "connected"
    except Exception as e:
        cache_status = f"error: {str(e)}"

    return {
        "database": db_status,
        "cache": cache_status
    }