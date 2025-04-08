import subprocess
import re
import time
from block import block_suspicious_traffic
import ipaddress
import sqlite3
from datetime import datetime

DB_FILE = "block_log.db"

def log_event_to_db(status, source, destination, resolved_hostname=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (timestamp, source, destination, resolved_hostname, status)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), source, destination, resolved_hostname, status))
    conn.commit()
    conn.close()
    print(f"[LOGGED] {status}: {destination}")

WHITELIST = [
    "google.com", "googleapis.com", "gstatic.com", "1e100.net",
    "wikipedia.org", "amazonaws.com", "apple.com",
    "localhost", "127.0.0.1",
    "mdns.mcast.net",
    "RT-AX53U-2410", "andrew-GEM12", "esp32s3-7B9554"
]

def is_trusted(destination):
    # Allow exact or suffix matches from whitelist
    for trusted in WHITELIST:
        if destination == trusted or destination.endswith('.' + trusted):
            return True

    # Check if it's a private/reserved IP
    try:
        ip = ipaddress.ip_address(destination)
        if ip.is_private or ip.is_loopback or ip.is_multicast:
            return True
    except ValueError:
        pass  # Not an IP

    return False

def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def parse_tcpdump_line(line):
    # Match IPv4 traffic
    ip_match = re.search(r'IP\s+(\d+\.\d+\.\d+\.\d+)\.\d+\s+>\s+(\d+\.\d+\.\d+\.\d+)\.\d+', line)
    if ip_match:
        return ip_match.groups()

    # Match hostnames (basic)
    host_match = re.search(r'IP\s+\S+\.\d+\s+>\s+([a-zA-Z0-9.-]+)\.\w+', line)
    if host_match:
        return None, host_match.group(1)

    return None, None

def monitor_traffic():
    print("[Monitor] Starting traffic monitoring...")
    process = subprocess.Popen(
        ["sudo", "tcpdump", "-i", "wlp3s0", "-l", "port", "not", "22"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    for line in process.stdout:
        print(f"[TCPDUMP] {line.strip()}")

        src, dst = parse_tcpdump_line(line)
        if dst:
            print(f"[PARSED] Detected: {src or '?'} -> {dst}")

            if is_trusted(dst):
                print(f"[TRUSTED] Skipping trusted destination: {dst}")
                continue

            print(f"[ALERT] Suspicious activity: {src or '?'} -> {dst}")

            if is_valid_ip(dst):
                print(f"[BLOCK] Trying to block IP: {dst}")
                # log_block_event(src, dst)
                log_event_to_db("Blocked", src, dst)
                block_suspicious_traffic(dst)
            else:
                print(f"[SKIP] Hostname detected: {dst}. Will try to resolve in block script.")
                # log_block_event(src, dst)
                log_event_to_db("Blocked", src, dst)
                block_suspicious_traffic(dst)

        time.sleep(0.1)

if __name__ == '__main__':
    monitor_traffic()
