import socket
import subprocess
import ipaddress

def block_suspicious_traffic(ip_or_hostname):
    if not ip_or_hostname:
        print("[ERROR] No target specified.")
        return

    if len(ip_or_hostname) < 4 or ip_or_hostname.isdigit():
        print(f"[INVALID] Target too short or numeric-only: {ip_or_hostname}")
        return

    try:
        ip_obj = ipaddress.ip_address(ip_or_hostname)
        ip_str = str(ip_obj)
    except ValueError:
        try:
            if '.' in ip_or_hostname:
                ip_str = socket.gethostbyname(ip_or_hostname)
                print(f"[RESOLVE] Resolved {ip_or_hostname} to {ip_str}")
            else:
                print(f"[INVALID] Not a resolvable hostname: {ip_or_hostname}")
                return
        except socket.gaierror:
            print(f"[ERROR] Failed to resolve hostname: {ip_or_hostname}")
            return

    # Skip blocking private IPs
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_multicast:
            print(f"[SKIP] Not blocking private/reserved IP: {ip_str}")
            return
    except ValueError:
        print(f"[ERROR] Invalid resolved IP: {ip_str}")
        return

    # Check if already blocked
    try:
        check = subprocess.run(['sudo', 'iptables', '-C', 'OUTPUT', '-d', ip_str, '-j', 'DROP'],
                               stderr=subprocess.PIPE)
        if check.returncode == 0:
            print(f"[EXISTS] Already blocked: {ip_str}")
            return
    except subprocess.CalledProcessError:
        pass  # Will proceed to block

    # Attempt to block
    try:
        subprocess.run(['sudo', 'iptables', '-A', 'OUTPUT', '-d', ip_str, '-j', 'DROP'], check=True)
        print(f"[BLOCKED] Successfully blocked: {ip_str}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Block failed for {ip_str}: {e}")
