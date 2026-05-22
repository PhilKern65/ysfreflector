# YSF Reflector Knowledge Base

## Date
21 May 2026

## Purpose
This document captures system behaviour, architecture decisions, and troubleshooting knowledge for the KernWi‑Fi YSF Dashboard platform.

---

## SYSTEM ARCHITECTURE

YSFReflector (C++)
    ↓
Log Files (/backend)
    ↓
ysf_dashboard.py (Python parser)
    ↓
status.json
    ↓
Web UI (Rev 1.7.1 / 1.7.2)

---

## IMPORTANT DESIGN RULES

- UI does NOT calculate data — it only displays JSON
- Backend parser is authoritative
- Connection state comes from:
  "Currently linked repeaters/gateways"
- Event logs ("Adding") are NOT reliable for state

---

## PARSER EVOLUTION

v1.17.2
- Introduced dynamic last_heard

v1.17.3
- Fixed disappearing users

v1.17.4
- Switched to authoritative linked block

v1.17.5
- Fixed parsing offsets ("2026-05-21", "data" bugs)

v1.17.6
- Improved whitespace handling

v1.17.7 (FINAL)
- Fully stable parser
- Accurate connection state
- No dropped users
- Production-safe logic

---

## KEY FIXES IMPLEMENTED

### ✅ Connection Accuracy
- Now matches reflector live state exactly

### ✅ TX Behaviour
- Previously: stuck (never cleared)
- Fixed: timeout-based clearing

### ✅ Parsing Issues Resolved
- Wrong callsign parsing
- Missing users
- Log structure variation
- Incorrect indices

---

## UI NOTES

### Rev 1.7.1
- Stable rendering baseline

### Rev 1.7.2
- TX highlight
- Visual improvements

### ⚠ CRITICAL RULE
UI must NOT be rewritten — only minimally patched.

---

## STATUS.JSON FORMAT (FINAL)

```json
{
  "connected_users": [],
  "connections": {},
  "last_heard": [],
  "transmitting": null,
  "connection_count": 0
}
