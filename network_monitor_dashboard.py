import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import subprocess
import os
import re
import matplotlib.pyplot as plt
import calplot

DB_FILE = "block_log.db"

st.set_page_config(layout="centered")  # or 'wide' if targeting tablets

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

# Pagination
st.subheader("🚫 Blocked Network Events")

block_tab1, block_tab2 = st.tabs(["📊 Block Graph", "📜 Live Logs"])

with block_tab1:
    st.markdown("### Blocked Events Over Time")
    chart_df = df[df['status'] == "Blocked"].copy()
    chart_df['day'] = chart_df['timestamp'].dt.floor('d')
    daily = chart_df.groupby('day').size()
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    daily_counts = daily.reindex(date_range, fill_value=0)
    daily_counts.index.name = 'day'
    st.line_chart(daily_counts)

with block_tab2:
    st.markdown("### Block Log History")
    page_size = 10
    total_pages = max(1, (len(df) - 1) // page_size + 1)
    page_num = st.selectbox("Page", options=list(range(1, total_pages + 1)), index=0, key="block_page")
    start_i = (page_num - 1) * page_size
    end_i = start_i + page_size

    for _, row in df.iloc[start_i:end_i].iterrows():
        with st.expander(f"{row['timestamp']} | {row['destination']} ({row['status']})", expanded=False):
            st.markdown(f"**Source:** {row['source'] or '?'}")
            st.markdown(f"**Destination:** {row['destination']}")
            st.markdown(f"**Resolved Hostname:** {row['resolved_hostname'] or 'N/A'}")
            st.markdown(f"**Status:** `{row['status']}`")

            if row['status'] == 'Blocked':
                if st.button(f"Unblock {row['destination']}", key=f"unblock-{row['id']}"):
                    try:
                        subprocess.run(['sudo', 'iptables', '-D', 'OUTPUT', '-d', row['destination'], '-j', 'DROP'], check=True)
                        st.success(f"✅ Unblocked {row['destination']}")
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        deleted = c.execute("DELETE FROM logs WHERE destination = ?", (row['destination'],)).rowcount
                        conn.commit()
                        conn.close()
                        st.success(f"🗑️ Removed {deleted} log(s) from database.")
                        st.rerun()
                    except subprocess.CalledProcessError:
                        st.error("❌ Failed to unblock. Check iptables or sudo permissions.")

    st.caption(f"Showing {start_i + 1} to {min(end_i, len(df))} of {len(df)} total entries.")

st.divider()
st.subheader("💾 Backup Overview")

tab1, tab2, tab3 = st.tabs(["Status", "Log History", "Calendar"])

# Compliance policy: how often backups are expected
expected_backup_interval_hrs = 24

# Load backup log entries
log_base = "/home/andrew/logs"
log_entries = []

if os.path.exists(log_base):
    for root, dirs, files in os.walk(log_base):
        for file in files:
            if "sync-backups.sh" in file and file.endswith(".log"):
                log_path = os.path.join(root, file)
                try:
                    match = re.search(r"sync-backups\.sh-(\d{4}-\d{2}-\d{2}_\d{6})\.log", file)
                    if match:
                        ts = match.group(1)
                        ts_fmt = datetime.strptime(ts, "%Y-%m-%d_%H%M%S")
                        with open(log_path, "r") as f:
                            content = f.read()
                            success = "Step 5. Success" in content
                            log_entries.append({
                                "timestamp": ts_fmt,
                                "filename": file,
                                "path": log_path,
                                "status": "Success" if success else "Failed"
                            })
                except Exception:
                    continue

# Tab 1: Compliance Status + Manual Backup
with tab1:
    st.markdown("### Backup Compliance Status")
    if log_entries:
        logs_df = pd.DataFrame(log_entries).sort_values(by="timestamp", ascending=False)
        success_logs = logs_df[logs_df["status"] == "Success"]
        if not success_logs.empty:
            latest_success = success_logs.iloc[0]
            now = datetime.now()
            last_time = latest_success["timestamp"]
            time_since = now - last_time
            hours_since = round(time_since.total_seconds() / 3600, 1)
            hours_remaining = expected_backup_interval_hrs - hours_since

            st.caption(f"Last Successful Backup: {last_time.strftime('%Y-%m-%d %H:%M:%S')} ({hours_since} hrs ago)")

            if hours_since <= expected_backup_interval_hrs:
                st.success("✅ On track with backup policy.")
                if hours_remaining <= 4:
                    st.info(f"Next backup due in ~{round(hours_remaining, 1)} hours")
                else:
                    st.caption(f"Next backup due in ~{round(hours_remaining, 1)} hours")
            else:
                st.warning(f"⚠️ Overdue by {round(-hours_remaining, 1)} hours! Expected every {expected_backup_interval_hrs}h.")
        else:
            st.error("❌ No successful backup found.")
    else:
        st.info("No backup logs found yet.")

    st.markdown("### Run Backup Now")
    if st.button("Run Backup Now"):
        try:
            result = subprocess.run(["/bin/bash", "sync-backups.sh"], capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                st.success("✅ Backup completed.")
            else:
                st.error("❌ Backup failed. See details:")
            st.code(result.stdout + "\n" + result.stderr, language="bash")
        except Exception as e:
            st.error(f"⚠️ Backup error: {e}")

# Tab 2: Backup History
with tab2:
    st.markdown("### Backup Log History")
    if log_entries:
        page_size = 5
        total_pages = max(1, (len(log_entries) - 1) // page_size + 1)
        page_num = st.selectbox("Page", options=list(range(1, total_pages + 1)), index=0, key="log_page")
        start_i = (page_num - 1) * page_size
        end_i = start_i + page_size

        for _, row in pd.DataFrame(log_entries).sort_values(by="timestamp", ascending=False).iloc[start_i:end_i].iterrows():
            with st.expander(f"{row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | {row['status']}", expanded=False):
                st.markdown(f"**Log File:** `{row['filename']}`")
                st.markdown(f"**Status:** `{row['status']}`")
                with open(row['path'], "r") as f:
                    st.code(f.read(), language="bash")
        st.caption(f"Showing {start_i + 1} to {min(end_i, len(log_entries))} of {len(log_entries)} logs.")
    else:
        st.info("No logs found.")

# Tab 3: Calendar Heatmap
with tab3:
    st.markdown("### Backup Calendar")
    if log_entries:
        calendar_data = pd.DataFrame(log_entries)
        calendar_data['date'] = pd.to_datetime(calendar_data['timestamp'].dt.date)
        calendar_data['score'] = calendar_data['status'].apply(lambda s: 1 if s == "Success" else -1)
        heatmap_series = calendar_data.groupby('date')['score'].sum()
        if not heatmap_series.empty:
            heatmap_series.index = pd.to_datetime(heatmap_series.index)
            fig, ax = calplot.calplot(
                heatmap_series,
                how='sum',
                cmap='RdYlGn',
                colorbar=False,
                suptitle='Backup Health Calendar',
                fillcolor='lightgrey',
                linewidth=1,
                edgecolor='black',
            )
            st.pyplot(fig)
        else:
            st.info("No heatmap data available.")
    else:
        st.info("No backup data.")
