from datetime import datetime
import socket
import subprocess

from gasera.device_status_service import get_latest_gasera_status

def get_ip_address():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "0.0.0.0"

def get_wifi_ssid():
    try:
        ssid = subprocess.check_output(["iwgetid", "-r"], text=True).strip()
        return ssid if ssid else "No WiFi"
    except Exception:
        return "Unknown"

def get_gasera_status():
    gasera_status = get_latest_gasera_status()
    if gasera_status:
        online = gasera_status.get("online", False)
        return "Online" if online else "Offline"
    
    return "Checking"

def get_formatted_timestamp():
    return datetime.now().strftime("%d.%m.%Y %H:%M")

def format_duration(seconds, fixed=False):
    """Format seconds as duration.
    - If fixed=False: MM:SS for <1h, HH:MM:SS for >=1h
    - If fixed=True: always HH:MM:SS
    """
    if not isinstance(seconds, (int, float)) or seconds < 0:
        return "--:--"
    elapsed = int(seconds)
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    secs = elapsed % 60
    if fixed or hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"

def format_consistent_pair(t1, t2, fixed=False):
    """
    Return (et_str, tt_str) formatted consistently.
    - If fixed=True: both use HH:MM:SS
    - If fixed=False: choose HH:MM:SS if either has hours, else MM:SS for both
    """
    s1 = t1 if isinstance(t1, (int, float)) and t1 >= 0 else None
    s2 = t2 if isinstance(t2, (int, float)) and t2 >= 0 else None

    if fixed:
        return (
            format_duration(s1, fixed=True) if s1 is not None else "--:--",
            format_duration(s2, fixed=True) if s2 is not None else "--:--",
        )

    # dynamic: if any shows hours, both render as HH:MM:SS
    show_hours = (s1 or 0) >= 3600 or (s2 or 0) >= 3600
    if show_hours:
        return (
            format_duration(s1, fixed=True) if s1 is not None else "--:--",
            format_duration(s2, fixed=True) if s2 is not None else "--:--",
        )
    else:
        return (
            format_duration(s1, fixed=False) if s1 is not None else "--:--",
            format_duration(s2, fixed=False) if s2 is not None else "--:--",
        )