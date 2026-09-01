#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度最终方案：Playwright 拿 sekey → share/transfer 转存到管理员网盘 → filemetas 拿 dlink → 下载"""
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

# 1) Playwright 拿 sekey + uk/shareid
sekey, uk, shareid = "", "", ""
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 1440, "height": 1000},
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")
    page = ctx.new_page()
    def on_req(r):
        nonlocal uk, shareid
        m = re.search(r"risklabel\?[^ ]*?uk=(\d+)&share_id=(\d+)", r.url)
        if m:
            uk, shareid = m.group(1), m.group(2)
    page.on("request", on_req)
    ctx.add_cookies(cookies)
    page.goto("https://pan.baidu.com/s/1%s?pwd=%s" % (surl, pwd), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(8000)
    sekey = page.evaluate("() => window.currentSekey || ''")
    b.close()
print("[SEKEY]", sekey[:20], "uk=", uk, "shareid=", shareid, file=sys.stderr)
if not sekey or not uk:
    print("[FAIL] 未拿到 sekey/uk")
    raise SystemExit(1)

# 2) bdstoken
st, j = req("GET", 'https://pan.baidu.com/api/gettemplatevariable?fields=["bdstoken"]', None, CK)
bdstoken = ((j.get("result") or {}).get("bdstoken")) or ""
print("[BDSTOKEN]", bdstoken[:16], file=sys.stderr)

# 3) share/transfer（query 带 shareid/from/sekey/bdstoken）
sekey_enc = urllib.parse.quote(sekey, safe="")
body = "path=" + urllib.parse.quote("/") + "&fsidlist=" + urllib.parse.quote("[" + fid + "]")
tf_url = ("https://pan.baidu.com/share/transfer?async=1&ondup=newcopy&channel=chunlei&web=1&app_id=250528"
          "&bdstoken=" + bdstoken + "&shareid=" + shareid + "&from=" + uk + "&sekey=" + sekey_enc + "&clienttype=0")
st, tj = req("POST", tf_url, body, CK)
print("[TRANSFER]", st, json.dumps(tj, ensure_ascii=False)[:200], file=sys.stderr)
taskid = tj.get("taskid") or tj.get("task_id") or ""
if not taskid:
    print("[FAIL] 无 taskid:", json.dumps(tj)[:200])
    raise SystemExit(1)

# 4) 轮询
for i in range(8):
    time.sleep(2)
    st, qj = req("GET", "https://pan.baidu.com/share/querytransfer?taskid=%s&channel=chunlei&web=1&app_id=250528&bdstoken=%s&clienttype=0" % (taskid, bdstoken), None, CK)
    info = qj.get("info") or []
    if isinstance(info, list) and info:
        st0 = str(info[0].get("status") or "")
        print("[Q%d] status=%s %s" % (i, st0, info[0].get("to_path") or ""), file=sys.stderr)
        if st0 in ("1", "2", "success", "SUCCESS"):
            break
    elif qj.get("errno") == 0:
        break

# 5) 列网盘根目录（找最新转存的文件）
st, lj = req("GET", "https://pan.baidu.com/api/list?dir=" + urllib.parse.quote("/") + "&num=50&order=time&desc=1&page=1&showempty=0&web=1&channel=chunlei&app_id=250528&bdstoken=" + bdstoken + "&clienttype=0", None, CK)
files = lj.get("list") or []
print("[LIST] files=%d" % len(files), file=sys.stderr)
for f in files[:3]:
    print("   ", f.get("server_filename"), f.get("fs_id"), f.get("path"), file=sys.stderr)
if not files:
    print("[FAIL] 网盘列表空")
    raise SystemExit(1)
target = files[0]
# 6) filemetas 拿 dlink（自己网盘文件，dlink=1）
targets = json.dumps([{"path": target.get("path")}], ensure_ascii=False)
st, mj = req("GET", "https://pan.baidu.com/api/filemetas?targets=" + urllib.parse.quote(targets) + "&dlink=1&clienttype=0&web=1&channel=chunlei&app_id=250528&bdstoken=" + bdstoken, None, CK, ua="netdisk;11.4.51.4.19", ref="https://pan.baidu.com/disk/main")
dlist = mj.get("info") or []
print("[FILEMETAS] errno=%s items=%d" % (mj.get("errno"), len(dlist)), file=sys.stderr)
if dlist:
    dlink = dlist[0].get("dlink") or ""
    print("[DLINK]", dlink[:150], file=sys.stderr)
    if dlink:
        # 下载验证（带 Referer + Cookie）
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "HTTP %{http_code} | %{size_download}B | %{speed_download}B/s",
               "-r", "0-1048575", "-m", "40", "-H", "User-Agent: netdisk;11.4.51.4.19",
               "-H", "Referer: https://pan.baidu.com/", "-H", "Cookie: " + CK, dlink]
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        print("[DL]", out)
        print("[RESULT]", json.dumps({"ok": True, "url": dlink, "name": target.get("server_filename"), "size": target.get("size", 0)}))
