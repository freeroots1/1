#!/usr/bin/env python3
"""Add note to IMA knowledge base with correct format."""
import json
import subprocess
import sys
import os

SKILL_DIR = "/home/ubuntu/.hermes/skills/ima-skill"
NOTE_ID = "7496009080906191"
KB_ID = "R2pr0-dHaKEcCBe7Aqa4doBoGpPG6UF7S1s0vcBnG8g="
FOLDER_ID = "folder_7481875509557716"  # 平台监控 folder

def run_ima_api(api_path, body):
    client_id = os.environ.get("IMA_OPENAPI_CLIENTID", "")
    api_key = os.environ.get("IMA_OPENAPI_APIKEY", "")
    if not client_id:
        with open(os.path.expanduser("~/.config/ima/client_id"), "r") as f:
            client_id = f.read().strip()
    if not api_key:
        with open(os.path.expanduser("~/.config/ima/api_key"), "r") as f:
            api_key = f.read().strip()
    
    opts = json.dumps({"clientId": client_id, "apiKey": api_key})
    body_str = json.dumps(body, ensure_ascii=False)
    cmd = ["node", f"{SKILL_DIR}/ima_api.cjs", api_path, body_str, opts]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if result.returncode != 0:
        print(f"API error: {result.stderr}", file=sys.stderr)
        return None
    if result.stdout.strip():
        return json.loads(result.stdout)
    return {}

# Add note to knowledge base
print("Adding note to knowledge base...")
add_body = {
    "media_type": 11,
    "note_info": {"content_id": NOTE_ID},
    "title": "平台状态监控报告_2026-08-20",
    "knowledge_base_id": KB_ID,
    "folder_id": FOLDER_ID
}

resp = run_ima_api("openapi/wiki/v1/add_knowledge", add_body)
print(f"Response: {json.dumps(resp, ensure_ascii=False, indent=2)}")

if resp and resp.get("code") == 0:
    print("\nSUCCESS: Note added to IMA knowledge base '平台监控' folder")
else:
    print(f"\nResult: {resp.get('msg', 'Unknown')}", file=sys.stderr)
