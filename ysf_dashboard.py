import time
import json
import os
from datetime import datetime, timezone

BASE_DIR = "/var/www/html/ysf/backend"
LOG_PREFIX = os.path.join(BASE_DIR, "YSFReflector-")
STATUS_FILE = "/var/www/html/ysf/status.json"

LOCAL_CALLSIGN = "VK5PK"
VERSION = "1.17.23.1"

TX_HOLD_SECONDS = 15

connected = {}
last_heard = []
last_seen_time = {}
transmitting = None
last_tx_time = None

# Track where we've read to for TX processing only
last_position = None
last_log_file = None


def get_log_file():
    return LOG_PREFIX + datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".log"


def format_elapsed(ts):
    now = datetime.now(timezone.utc).timestamp()
    diff = int(now - ts)

    if diff < 60:
        return f"{diff}s ago"
    elif diff < 3600:
        return f"{diff // 60}m ago"
    else:
        return f"{diff // 3600}h ago"


def normalise_callsign(raw):
    # Handles:
    # VK5PK-PHIL -> VK5PK
    # ZL3BHS/BRY -> ZL3BHS
    return raw.split('-')[0].split('/')[0].strip()


def is_valid_callsign(cs):
    if not cs or len(cs) < 3:
        return False
    if cs.upper() == "WIRESX":
        return False
    return True


def parse_connected_snapshot(log_file):
    """
    Rebuild connected users from the latest 'Currently linked repeaters/gateways'
    block found near the end of the log.
    """
    global connected

    if not os.path.exists(log_file):
        return

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()[-500:]  # latest window only
    except:
        return

    # Find the most recent block header
    start_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if "Currently linked repeaters/gateways" in lines[i]:
            start_idx = i
            break

    if start_idx is None:
        return

    new_connected = {}

    for line in lines[start_idx + 1:]:
        try:
            if not line.startswith("M:"):
                break

            parts = line.strip().split()

            # Expected format like:
            # M: 2026-05-23 00:56:10.476     VK5RKW    : 172.105.187.182:32780 0/60
            if len(parts) < 6:
                continue

            callsign = normalise_callsign(parts[3])

            # parts[5] should be IP:PORT
            ip_port = parts[5]
            if ":" not in ip_port:
                continue

            ip = ip_port.split(":")[0]

            if ip.count(".") != 3:
                continue

            if callsign not in new_connected:
                new_connected[callsign] = []

            if not any(entry["ip"] == ip for entry in new_connected[callsign]):
                new_connected[callsign].append({
                    "ip": ip,
                    "last_seen": 9999
                })

        except:
            continue

    if new_connected:
        connected.clear()
        connected.update(new_connected)


def parse_new_tx_lines(log_file):
    """
    Only process NEW lines appended since last read position.
    This prevents replaying old transmissions every loop.
    """
    global transmitting, last_tx_time, last_position, last_log_file

    if not os.path.exists(log_file):
        return

    # Handle daily log rollover
    if log_file != last_log_file:
        last_log_file = log_file
        last_position = None

    try:
        with open(log_file, "r") as f:

            # First run: start at end of file so we do NOT replay history
            if last_position is None:
                f.seek(0, os.SEEK_END)
                last_position = f.tell()
                return

            f.seek(last_position)
            new_lines = f.readlines()
            last_position = f.tell()

    except:
        return

    now_ts = datetime.now(timezone.utc).timestamp()

    for line in new_lines:
        try:
            if "Received" in line and "from" in line:
                after = line.split("from", 1)[1].strip()
                raw_callsign = after.split()[0]
                callsign = normalise_callsign(raw_callsign)

                if not is_valid_callsign(callsign):
                    continue

                # Packet spam suppression:
                # Many "Received data from ..." lines can happen within one TX.
                # Only count a new activity event if >1 second since same callsign.
                if callsign in last_seen_time and (now_ts - last_seen_time[callsign]) < 1:
                    continue

                print("TX:", callsign)

                last_seen_time[callsign] = now_ts

                # Keep last_heard unique and recent
                last_heard[:] = [x for x in last_heard if x["callsign"] != callsign]
                last_heard.insert(0, {
                    "callsign": callsign,
                    "timestamp": now_ts
                })
                last_heard[:] = last_heard[:10]

                transmitting = callsign
                last_tx_time = now_ts

            elif "Received end of transmission" in line:
                transmitting = None
                last_tx_time = None

        except Exception as e:
            print("TX parse error:", e)

    # Safety timeout if end-of-transmission line is missed
    if last_tx_time and (now_ts - last_tx_time > TX_HOLD_SECONDS):
        transmitting = None
        last_tx_time = None


def build_status():
    now_ts = datetime.now(timezone.utc).timestamp()

    # Apply last_seen to connected users
    for callsign in connected:
        for entry in connected[callsign]:
            if callsign in last_seen_time:
                entry["last_seen"] = int(now_ts - last_seen_time[callsign])
            else:
                entry["last_seen"] = 9999

    formatted_last_heard = [
        {
            "callsign": entry["callsign"],
            "time": format_elapsed(entry["timestamp"])
        }
        for entry in last_heard
    ]

    data = {
        "status": "ONLINE",
        "connected_users": sorted(connected.keys()),
        "connection_count": len(connected),
        "connections": connected,
        "last_heard": formatted_last_heard,
        "transmitting": transmitting,
        "tx_duration": 0,
        "local_callsign": LOCAL_CALLSIGN,
        "version": VERSION
    }

    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)


while True:
    try:
        log_file = get_log_file()
        parse_connected_snapshot(log_file)
        parse_new_tx_lines(log_file)
        build_status()
    except Exception as e:
        print("Error:", e)

    time.sleep(2)
