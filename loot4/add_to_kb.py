#!/usr/bin/env python3
"""Add note to knowledge base"""
import json
import subprocess
import sys
import os

IMA_DIR = os.path.expanduser("~/.hermes/skills/ima-skill")
CLIENT_ID = open(os.path.expanduser("~/.config/ima/client_id")).read().strip()
API_KEY = open(os.path.expanduser("~/.config/ima/api_key")).read().strip()
opts = json.dumps({"clientId": CLIENT_ID, "apiKey": API_KEY})

REPORT_DATE = "2026-08-24"
REPORT_TITLE = f"平台状态监控报告_{REPORT_DATE}.md"
NOTE_ID = "7497458674333236"  # Already created note
KB_ID = "R2pr0-dHaKEcCBe7Aqa4doBoGpPG6UF7S1s0vcBnG8g="  # 田妮妮 的知识库

def run_ima_api(api_path, body):
    """Run IMA API call"""
    result = subprocess.run(
        ["node", f"{IMA_DIR}/ima_api.cjs", api_path, body, opts],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"API FAILED: {result.stderr}", file=sys.stderr)
        return None
    return json.loads(result.stdout)

# Add note to knowledge base
print(f"Adding note {NOTE_ID} to knowledge base...")
add_body = json.dumps({
    "media_type": 11,
    "note_info": {"content_id": NOTE_ID},
    "title": REPORT_TITLE,
    "knowledge_base_id": KB_ID
})
add_resp = run_ima_api("openapi/wiki/v1/add_knowledge", add_body)

if add_resp and add_resp.get("code") == 0:
    print(f"Successfully added to KB!")
    print(f"Response: {json.dumps(add_resp, ensure_ascii=False, indent=2)}")
else:
    print(f"Failed to add to KB: {add_resp}")
    sys.exit(1)
