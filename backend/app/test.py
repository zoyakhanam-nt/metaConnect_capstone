"""
Test script to verify connection to CockroachDB Cloud cluster.

Before running:
    pip install psycopg2-binary

Set your password as an environment variable (recommended, don't hardcode it):
    export COCKROACH_PASSWORD="your_actual_password"

Then run:
    python test_cockroachdb.py
"""

import os
import psycopg2

# --- Connection details ---
DB_HOST = "metaconnect-cluster-33528.j77.aws-ap-south-1.cockroachlabs.cloud"
DB_PORT = 26257
DB_NAME = "defaultdb"
DB_USER = "zoya"
DB_PASSWORD = "db1gfRQx1lI1GWUcPOn5WA" 
DB_SSLMODE = "verify-full"

if not DB_PASSWORD:
    raise ValueError(
        "COCKROACH_PASSWORD environment variable not set. "
        "Run: export COCKROACH_PASSWORD='your_actual_password'"
    )

# Build connection string
CONN_STRING = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?sslmode={DB_SSLMODE}"
)


def test_connection():
    try:
        print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER} ...")
        conn = psycopg2.connect(CONN_STRING)
        cursor = conn.cursor()

        # Basic sanity check
        cursor.execute("SELECT now();")
        result = cursor.fetchone()
        print(f"Connected successfully. Server time: {result[0]}")

        # Show CockroachDB version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"CockroachDB version: {version[0]}")

        cursor.close()
        conn.close()
        print("Connection closed cleanly.")

    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    test_connection()