import time
import json
import datetime
import os
import re

OUTPUT_FILE = "/var/www/html/ysf/status.json"
LOCAL_CALLSIGN = "VK5PK"
VERSION = "1.16"

TX_HOLD_SECONDS = 20

last_tx_callsign = None
last_tx_time = None


def get_log_file():
    base = "/root/DVReflectors/YSFReflector/YSFReflector-"
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    file_today = base + today + ".log"

    if os.path.exists(file_today):
        return file_today

    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    return base + yesterday + ".log"


def format_relative(seconds):
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    else:
        return f"{int(seconds // 3600)}h ago"


def parse_log():
    global last_tx_callsign, last_tx_time

    connected_users = []
    connections = {}
    last_heard = []
    last_seen_map = {}

    transmitting = None
    tx_duration = 0

    now = datetime.datetime.now(datetime.timezone.utc)
    log_file = get_log_file()

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
    except:
        return

    # ✅ FIND CONNECTION BLOCK
    start_index = None
    for i in range(len(lines) - 1, -1, -1):
        if "Currently linked repeaters/gateways" in lines[i]:
            start_index = i
            break

    if start_index is not None:
        i = start_index + 1

        while i < len(lines):
            line = lines[i].strip()

            if not line.startswith("M:"):
                break

            match = re.search(r"\s([A-Z0-9/-]+)\s+:\s+([0-9.]+):", line)

            if match:
                callsign = match.group(1).split('-')[0]
                ip = match.group(2)

                if callsign not in connected_users:
                    connected_users.append(callsign)

                if callsign not in connections:
                    connections[callsign] = []

                if not any(entry["ip"] == ip for entry in connections[callsign]):
                    connections[callsign].append({
                        "ip": ip,
                        "last_seen": 9999
                    })

            i += 1

    # ✅ PARSE ACTIVITY (expanded window)
    seen = set()

    for line in reversed(lines[-1500:]):   # ✅ FIXED HERE

        if "Received data from" in line:
            try:
                after = line.split("Received data from")[1].strip()
                callsign = after.split()[0].split('-')[0]

                raw_time = " ".join(line.split()[1:3])
                dt = datetime.datetime.strptime(
                    raw_time, "%Y-%m-%d %H:%M:%S.%f"
                ).replace(tzinfo=datetime.timezone.utc)

                diff = (now - dt).total_seconds()

                last_seen_map[callsign] = diff

                # TX detection
                if diff < 5:
                    transmitting = callsign
                    last_tx_callsign = callsign
                    last_tx_time = now

                if callsign not in seen:
                    last_heard.append({
                        "callsign": callsign,
                        "time": format_relative(diff)
                    })
                    seen.add(callsign)

            except:
                continue

        if len(last_heard) >= 10:
            break

    # ✅ APPLY last_seen
    for callsign in connections:
        if callsign in last_seen_map:
            for entry in connections[callsign]:
                entry["last_seen"] = int(last_seen_map[callsign])
        else:
            for entry in connections[callsign]:
                entry["last_seen"] = 9999

    # ✅ TX HOLD
    if last_tx_callsign and last_tx_time:
        diff = (now - last_tx_time).total_seconds()

        if diff < TX_HOLD_SECONDS:
            transmitting = last_tx_callsign
            tx_duration = int(diff)
        else:
            last_tx_callsign = None
            last_tx_time = None
            transmitting = None

    # ✅ OUTPUT
    data = {
        "status": "ONLINE",
        "connected_users": sorted(set(connected_users)),
        "connection_count": len(set(connected_users)),
        "connections": connections,
        "last_heard": last_heard,
        "transmitting": transmitting,
        "tx_duration": tx_duration,
        "local_callsign": LOCAL_CALLSIGN,
        "version": VERSION
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)


while True:
    parse_log()
    time.sleep(2)
