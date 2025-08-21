import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta


def analyze_logs(db_path="query_logs.db", days=7):
    conn = sqlite3.connect(db_path)

    # Get logs from the last X days
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    # Load logs into a pandas DataFrame
    df = pd.read_sql_query(
        f"SELECT * FROM query_logs WHERE timestamp > '{cutoff_date}'", conn
    )

    # Parse metadata
    df["metadata"] = df["metadata"].apply(json.loads)
    df["response_time"] = df["metadata"].apply(lambda x: x.get("response_time", 0))

    # Basic statistics
    total_queries = len(df)
    avg_response_time = df["response_time"].mean()

    # Query frequency by day
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    # daily_counts = df.groupby("date").size()

    # Common queries (simple frequency analysis)
    # common_queries = df["query"].value_counts().head(10)

    # Session analysis (repeat users)
    sessions_with_multiple_queries = df.groupby("session_id").filter(
        lambda x: len(x) > 1
    )
    repeat_query_percentage = len(sessions_with_multiple_queries) / total_queries * 100

    # Print results
    print(f"Total queries: {total_queries}")
    print(f"Average response time: {avg_response_time:.2f} seconds")
    print(
        f"Percentage of sessions with follow-up queries: {repeat_query_percentage:.2f}%"
    )

    # # Visualize daily query count
    # plt.figure(figsize=(10, 6))
    # daily_counts.plot(kind="bar")
    # plt.title("Daily Query Volume")
    # plt.ylabel("Number of Queries")
    # plt.tight_layout()
    # plt.savefig("daily_queries.png")

    return df


def main():
    db_path = "logging_database.db"
    days = 7
    analyze_logs(db_path, days)


if __name__ == "__main__":
    main()
