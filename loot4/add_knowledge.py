import json
import subprocess
import sys
import time

# Read COS credentials
with open('/tmp/cos_creds.json') as f:
    creds = json.load(f)

# IMA credentials
client_id = "96ed9ae96bb15001b15cbc53ba22e13b"
api_key = "Xw3Bba5gSyCO6B5LiI6Gj3mHIKy2MHVMDO/Pe4CNX8HiaLb6AEhvo2vO+kfD4gniFpSPc8M9zA=="

# Build the add_knowledge request
kb_id = "R2pr0-dHaKEcCBe7Aqa4doBoGpPG6UF7S1s0vcBnG8g="
folder_id = "folder_7481875509557716"
media_id = creds['media_id']
cos_key = creds['cos_key']
file_size = 2650  # Size of the markdown file

body = {
    "knowledge_base_id": kb_id,
    "folder_id": folder_id,
    "media_id": media_id,
    "media_type": 7,
    "title": "平台状态监控报告_2026-07-20.md",
    "file_info": {
        "cos_key": cos_key,
        "file_size": file_size,
        "last_modify_time": int(time.time()),
        "file_name": "平台状态监控报告_2026-07-20.md"
    }
}

# Build the command
skill_dir = subprocess.run(
    ["bash", "-c", "echo $HOME/.hermes/skills/ima-skill"],
    capture_output=True, text=True
).stdout.strip()

opts = json.dumps({"clientId": client_id, "apiKey": api_key})

cmd = [
    "node",
    f"{skill_dir}/ima_api.cjs",
    "openapi/wiki/v1/add_knowledge",
    json.dumps(body),
    opts
]

print(f"Running add_knowledge...")
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    resp = json.loads(result.stdout)
    if resp.get('code') == 0:
        print("add_knowledge successful!")
        print(f"Response: {json.dumps(resp, indent=2)}")
    else:
        print(f"add_knowledge failed: {resp.get('msg')}")
        sys.exit(1)
else:
    print(f"add_knowledge failed: {result.stderr}")
    sys.exit(1)
