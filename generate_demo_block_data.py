import sqlite3
import random
from datetime import datetime, timedelta

# Database file path
DB_FILE = "block_log.db"

# Connect to SQLite
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Ensure table exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source TEXT,
    destination TEXT,
    resolved_hostname TEXT,
    status TEXT CHECK(status IN ('Blocked', 'Trusted')) NOT NULL
)
""")

# Generate demo data
statuses = ["Blocked", "Trusted"]
domains = ["example.com", "badactor.io", "safehost.org", "unknown.ai", "malware.cc"]
ips = ["192.168.1.2", "10.0.0.5", "172.16.4.12", "192.168.100.14", "10.1.2.3"]

entries = []

for day_offset in range(5):
    date = datetime.now() - timedelta(days=day_offset)
    for _ in range(10):  # 10 logs per day
        ts = (date + timedelta(minutes=random.randint(0, 1440))).isoformat()
        status = random.choice(statuses)
        dst = random.choice(["93.184.216.34", "8.8.8.8", "203.0.113.42", "198.51.100.1"])
        source = random.choice(ips)
        host = random.choice(domains)
        entries.append((ts, source, dst, host, status))

# Insert into DB
cursor.executemany("""
INSERT INTO logs (timestamp, source, destination, resolved_hostname, status)
VALUES (?, ?, ?, ?, ?)
""", entries)

conn.commit()
conn.close()

print(f"✅ Inserted {len(entries)} demo entries into block_log.db")
