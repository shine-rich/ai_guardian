
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

DB_FILE = "block_log.db"

st.title("🛡️ SQLite-Based Network Monitor Dashboard")

# Load data from SQLite
def query_logs(keyword="", status_filter=None, start=None, end=None):
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT id, timestamp, source, destination, resolved_hostname, status FROM logs WHERE 1=1"
    params = []

    if keyword:
        query += " AND (destination LIKE ? OR resolved_hostname LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if start:
        query += " AND timestamp >= ?"
        params.append(datetime.combine(start, datetime.min.time()).isoformat())
    if end:
        query += " AND timestamp <= ?"
        params.append(datetime.combine(end, datetime.max.time()).isoformat())

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# Sidebar filters
st.sidebar.header("🔧 Filters")
keyword = st.sidebar.text_input("🔍 Keyword search")
status_filter = st.sidebar.selectbox("Filter by status", ["", "Blocked", "Trusted"])
start_date = st.sidebar.date_input("Start Date", datetime.now() - timedelta(days=5))
end_date = st.sidebar.date_input("End Date", datetime.now())

# Query and paginate
df = query_logs(keyword, status_filter if status_filter else None, start_date, end_date)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.sort_values(by="timestamp", ascending=False, inplace=True)

# Show chart (Blocked only)
chart_df = df[df['status'] == "Blocked"].copy()
chart_df['day'] = chart_df['timestamp'].dt.floor('d')
daily = chart_df.groupby('day').size()
st.subheader("📊 Blocked Events Over Time")
date_range = pd.date_range(start=start_date, end=end_date, freq='D')
daily_counts = daily.reindex(date_range, fill_value=0)
daily_counts.index.name = 'day'
st.line_chart(daily_counts)

# Pagination
st.subheader("🔍 Live Logs")
page_size = 10
page_num = st.number_input("Page", min_value=1, max_value=max(1, (len(df) - 1) // page_size + 1), step=1)
start_i = (page_num - 1) * page_size
end_i = start_i + page_size

# Unblock logic
for _, row in df.iloc[start_i:end_i].iterrows():
    with st.expander(f"{row['timestamp']} | {row['destination']} ({row['status']})"):
        st.markdown(f"**Source:** {row['source'] or '?'}")
        st.markdown(f"**Destination:** {row['destination']}")
        st.markdown(f"**Resolved Hostname:** {row['resolved_hostname'] or 'N/A'}")
        st.markdown(f"**Status:** {row['status']}")

        if row['status'] == 'Blocked':
            if st.button(f"Unblock {row['destination']}", key=f"unblock-{row['id']}"):
                import subprocess
                try:
                    subprocess.run(['sudo', 'iptables', '-D', 'OUTPUT', '-d', row['destination'], '-j', 'DROP'], check=True)
                    st.success(f"Unblocked {row['destination']}")

                    # Remove from DB
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    deleted = c.execute("DELETE FROM logs WHERE destination = ?", (row['destination'],)).rowcount
                    conn.commit()
                    conn.close()
                    st.success(f"Unblocked {row['destination']} and removed {deleted} log(s)")
                    st.rerun()
                except subprocess.CalledProcessError:
                    st.error("Failed to unblock. Check iptables or sudo settings.")

st.caption(f"Showing {start_i + 1} to {min(end_i, len(df))} of {len(df)} total entries.")
