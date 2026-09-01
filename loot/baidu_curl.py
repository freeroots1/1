"""
Step 1: 解析新链接拿 fs_id
Step 2: 用 fs_id 调 detail 看子文件
"""
import json, urllib.request, urllib.parse

URL = "https://pan.baidu.com/s/1iZvGy3WB2uZKY1l61BmLJw"
PASS = "yvih"
BASE = "http://localhost:3000"

def post(path, body, timeout=90):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

# Step 1
r1 = post("/api/baidu/share", {"url": URL, "pass_code": PASS})
res1 = r1.get("result") or {}
files1 = res1.get("files") or []
print("=== share ===")
print("ok:", r1.get("ok"), "| files:", len(files1), "| full_tree:", len(res1.get("full_tree") or []))
if files1:
    print(" root fs_id:", files1[0].get("fs_id"))
    print(" root isdir:", files1[0].get("isdir"))
    print(" root name:", files1[0].get("server_filename"))
    fsid = files1[0].get("fs_id", "")
else:
    fsid = ""

# Step 2
if fsid:
    r2 = post("/api/baidu/detail", {"share_url": URL, "parent_file_id": fsid, "pass_code": PASS})
    res2 = r2.get("result") or {}
    files2 = res2.get("files") or []
    print("\n=== detail (fs_id=" + fsid + ") ===")
    print("ok:", r2.get("ok"), "| err:", str(r2.get("error") or "")[:100])
    print("files:", len(files2), "| full_tree:", len(res2.get("full_tree") or []))
    for x in files2[:5]:
        print(" -", "DIR" if x.get("isdir") else "FILE", x.get("server_filename") or x.get("filename"), "|fsid:", x.get("fs_id"), "|size:", x.get("size"))
