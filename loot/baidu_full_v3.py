#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度转存下载删除：Playwright 拿 sekey → share/transfer 转存管理员网盘 → filemetas 拿直链 → 下载 → 删除"""
import json, sys, subprocess, time, urllib.request, urllib.error, urllib.parse, re
from playwright.sync_api import sync_playwright

SETTINGS = "/home/ubuntu/app/coolink/data/settings.json"
NODE = "/usr/bin/node"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def get_baidu_cookie():
    js = """
const fs=require("fs"),crypto=require("crypto");
const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
const key=crypto.scryptSync(process.env.ADMIN_PASSWORD||"AeLnUxLVwcTVBDU5",Buffer.from("pandel-settings-v1","utf8"),32,{N:16384,r:8,p:1});
const b=Buffer.from(j.data,"base64");
const d=crypto.createDecipheriv("aes-256-gcm",key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
const o=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString("utf8"));
process.stdout.write(o.cookies.baidu||"");
"""
    r = subprocess.run([NODE, "-e", js, SETTINGS], capture_output=True, text=True, timeout=15)
    return r.stdout.strip()

def req(method, url, body=None, cookie="", ua=UA, ref="https://pan.baidu.com/disk/main"):
    h = {"User-Agent": ua, "Referer": ref}
    if cookie:
        h["Cookie"] = cookie
    data = body.encode() if isinstance(body, str) else body
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=30) as x:
            return x.status, json.loads(x.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)[:120]}

surl, pwd, fid = sys.argv[1], sys.argv[2], sys.argv[3]
CK = get_baidu_cookie()
cookies = []
for part in CK.split(";"):
    part = part.strip()
    if "=" in part:
        k, v = part.split("=", 1)
        cookies.append({"name": k.strip(), "value": v.strip(), "domain": ".baidu.com", "path": "/"})

# 1) Playwright 拿 sekey + uk/shareid（risklabel 请求 URL）
uk_share = {}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 1440, "height": 1000},
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")
    page = ctx.new_page()
    def on_req(r):
        m = re.search(r"risklabel\?[^ ]*?uk=(\d+)&share_id=(\d+)", r.url)
        if m and not uk_share:
            uk_share["uk"] = m.group(1)
            uk_share["share_id"] = m.group(2)
    page.on("request", on_req)
    ctx.add_cookies(cookies)
    page.goto("https://pan.baidu.com/s/1%s?pwd=%s" % (surl, pwd), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(8000)
    sekey = page.evaluate("() => window.currentSekey || ''")
    b.close()
uk = uk_share.get("uk", "")
shareid = uk_share.get("share_id", "")
print("[SEKEY]", (sekey or "")[:20], "uk=", uk, "shareid=", shareid, file=sys.stderr)
if not sekey or not uk:
    print("[FAIL] 未拿到 sekey/uk")
    raise SystemExit(1)

# 2) bdstoken
st, j = req("GET", 'https://pan.baidu.com/api/gettemplatevariable?fields=["bdstoken"]', None, CK)
bdstoken = ((j.get("result") or {}).get("bdstoken")) or ""
print("[BDSTOKEN]", bdstoken[:16], file=sys.stderr)

# 3) share/transfer 转存（query 带 shareid/from/sekey/bdstoken）
sekey_enc = urllib.parse.quote(sekey, safe="")
body = "path=" + urllib.parse.quote("/") + "&fsidlist=" + urllib.parse.quote("[" + fid + "]")
tf_url = ("https://pan.baidu.com/share/transfer?async=1&ondup=newcopy&channel=chunlei&web=1&app_id=250528"
          "&bdstoken=" + bdstoken + "&shareid=" + shareid + "&from=" + uk + "&sekey=" + sekey_enc + "&clienttype=0")
st, tj = req("POST", tf_url, body, CK)
print("[TRANSFER]", st, json.dumps(tj, ensure_ascii=False)[:200], file=sys.stderr)
# 4) transfer errno=0 且 extra.list 有 to 路径 = 转存已同步完成（无需 taskid 轮询）
to_path = ""
extra_list = (tj.get("extra") or {}).get("list") or []
if extra_list and extra_list[0].get("to"):
    to_path = extra_list[0]["to"]
    print("[TRANSFER-OK] to=%s to_fs_id=%s" % (to_path, extra_list[0].get("to_fs_id")), file=sys.stderr)
else:
    taskid = tj.get("taskid") or tj.get("task_id") or ""
    if not taskid:
        print("[FAIL] 无 taskid:", json.dumps(tj)[:200])
        raise SystemExit(1)
    for i in range(8):
        time.sleep(2)
        st, qj = req("GET", "https://pan.baidu.com/share/querytransfer?taskid=%s&channel=chunlei&web=1&app_id=250528&bdstoken=%s&clienttype=0" % (taskid, bdstoken), None, CK)
        info = qj.get("info") or []
        if isinstance(info, list) and info:
            st0 = str(info[0].get("status") or "")
            print("[Q%d] status=%s" % (i, st0), file=sys.stderr)
            if st0 in ("1", "2", "success", "SUCCESS"):
                break

# 5) 列网盘根目录找转存文件（按时间倒序第一个）
st, lj = req("GET", "https://pan.baidu.com/api/list?dir=" + urllib.parse.quote("/") + "&num=50&order=time&desc=1&page=1&showempty=0&web=1&channel=chunlei&app_id=250528&bdstoken=" + bdstoken + "&clienttype=0", None, CK)
files = lj.get("list") or []
print("[LIST] files=%d" % len(files), file=sys.stderr)
for f in files[:3]:
    print("   ", f.get("server_filename"), f.get("fs_id"), f.get("path"), file=sys.stderr)
if not files:
    print("[FAIL] 网盘列表空")
    raise SystemExit(1)
if to_path:
    # 转存返回的 to 路径直接定位（文件名可能重复，精确匹配）
    target = None
    for f in files:
        if f.get("path") == to_path:
            target = f
            break
    if not target:
        target = next((f for f in files if f.get("server_filename") == to_path.split("/")[-1]), files[0])
else:
    target = files[0]
tpath = target.get("path")
tfsid = target.get("fs_id")
# 6) filemetas 拿 dlink（自己网盘文件，dlink=1 → 不需 locatedownload）
targets = json.dumps([{"path": tpath}], ensure_ascii=False)
st, mj = req("GET", "https://pan.baidu.com/api/filemetas?targets=" + urllib.parse.quote(targets) + "&dlink=1&clienttype=0&web=1&channel=chunlei&app_id=250528&bdstoken=" + bdstoken, None, CK, ua="netdisk;11.4.51.4.19", ref="https://pan.baidu.com/disk/main")
dlist = mj.get("info") or []
print("[FILEMETAS] errno=%s items=%d" % (mj.get("errno"), len(dlist)), file=sys.stderr)
dlink = dlist[0].get("dlink") or "" if dlist else ""
print("[DLINK]", (dlink or "")[:150], file=sys.stderr)
if dlink:
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "HTTP %{http_code} | %{size_download}B | %{speed_download}B/s",
           "-r", "0-1048575", "-m", "40", "-H", "User-Agent: netdisk;11.4.51.4.19",
           "-H", "Referer: https://pan.baidu.com/", "-H", "Cookie: " + CK, dlink]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    print("[DL]", out)
# 7) 删除转存的文件（不占管理员空间）
st, dj = req("POST", "https://pan.baidu.com/api/filemanager?async=2&opera=delete&onnest=fail&channel=chunlei&web=1&app_id=250528&bdstoken=" + bdstoken + "&clienttype=0",
             "filelist=" + urllib.parse.quote(json.dumps([tpath], ensure_ascii=False)), CK)
print("[DELETE]", st, json.dumps(dj, ensure_ascii=False)[:150], file=sys.stderr)
print("[RESULT]", json.dumps({"ok": True, "url": dlink, "name": target.get("server_filename"), "size": target.get("size", 0), "deleted": bool(dj.get("errno") == 0 or not dj.get("errno"))}))
