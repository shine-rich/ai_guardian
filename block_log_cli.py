# === CLI TOOL: block_log_cli.py ===
import sqlite3
import argparse
from datetime import datetime

DB_FILE = "block_log.db"

def query_logs(keyword=None, status=None, start=None, end=None):
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT timestamp, source, destination, resolved_hostname, status FROM logs WHERE 1=1"
    params = []

    if keyword:
        query += " AND (destination LIKE ? OR resolved_hostname LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if status:
        query += " AND status = ?"
        params.append(status)
    if start:
        query += " AND timestamp >= ?"
        params.append(start.isoformat())
    if end:
        query += " AND timestamp <= ?"
        params.append(end.isoformat())

    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def print_results(rows):
    if not rows:
        print("No matching records found.")
        return
    print("\n=== Matching Logs ===")
    for row in rows:
        print(f"[{row[0]}] {row[4]}: {row[2]} (resolved: {row[3]}) from {row[1] or '?'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="🔍 Query block_log.db")
    parser.add_argument("-k", "--keyword", help="Filter by keyword in IP or hostname")
    parser.add_argument("-s", "--status", choices=["Blocked", "Trusted"], help="Filter by status")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d") if args.start else None
    end_date = datetime.strptime(args.end, "%Y-%m-%d") if args.end else None

    results = query_logs(
        keyword=args.keyword,
        status=args.status,
        start=start_date,
        end=end_date
    )
    print_results(results)
