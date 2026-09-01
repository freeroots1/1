#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度 share/transfer 转存（Python 直调，带完整登录 cookie）→ 轮询 → 列网盘 → locatedownload"""
import json, sys, subprocess, time, urllib.request, urllib.error, urllib.parse

SETTINGS = "/home/ubuntu/app/coolink/data/settings.json"
NODE = "/usr/bin/node"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
REF = "https://pan.baidu.com/disk/main"

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

def req(method, url, body=None, cookie="", ua=UA, ref=REF):
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

# 1) bdstoken
st, j = req("GET", 'https://pan.baidu.com/api/gettemplatevariable?fields=["bdstoken"]', None, CK)
bdstoken = ((j.get("result") or {}).get("bdstoken")) or ""
print("[BDSTOKEN]", bdstoken[:20], file=sys.stderr)

# 2) share/transfer 转存到网盘根目录
body = "path=" + urllib.parse.quote("/") + "&fsidlist=" + urllib.parse.quote("[" + fid + "]")
st, tj = req("POST", "https://pan.baidu.com/share/transfer?async=1&ondup=newcopy&channel=chunlei&web=1&app_id=250528&bdstoken=" + bdstoken + "&clienttype=0",
             body, CK)
print("[TRANSFER]", st, json.dumps(tj, ensure_ascii=False)[:300])
taskid = tj.get("taskid") or tj.get("task_id") or ""
if not taskid:
    print("[FAIL] 无 taskid")
    raise SystemExit(1)

# 3) 轮询转移任务
for i in range(10):
    time.sleep(2)
    st, qj = req("GET", "https://pan.baidu.com/share/querytransfer?taskid=%s&channel=chunlei&web=1&app_id=250528&bdstoken=%s&clienttype=0" % (taskid, bdstoken), None, CK)
    info = qj.get("info") or qj.get("task_info") or []
    print("[Q%d]" % i, json.dumps(qj, ensure_ascii=False)[:250])
    if isinstance(info, list) and info:
        st0 = info[0].get("status") or ""
        if str(st0) in ("1", "2", "success", "SUCCESS"):
            print("[TRANSFER-OK]")
            break
    elif qj.get("errno") == 0 or qj.get("success"):
        break

# 4) 列出网盘根目录（找转存的文件）
st, lj = req("GET", "https://pan.baidu.com/api/list?dir=" + urllib.parse.quote("/") + "&num=100&order=time&desc=1&page=1&showempty=0&web=1&channel=chunlei&app_id=250528&bdstoken=" + bdstoken + "&clienttype=0",
             None, CK)
print("[LIST]", st, json.dumps(lj, ensure_ascii=False)[:400])
files = lj.get("list") or []
if files:
    newest = files[0]
    print("[NEWEST]", newest.get("server_filename"), newest.get("fs_id"), newest.get("path"), file=sys.stderr)
    # 5) 对网盘内文件 locatedownload（转存后是"我的网盘文件"，不需要分享 sekey！）
    fid2 = newest.get("fs_id")
    path2 = newest.get("path")
    st, mj = req("GET", "https://pan.baidu.com/api/filemetas?targets=" + urllib.parse.quote(json.dumps([{"path": path2}], ensure_ascii=False)) + "&dlink=1&clienttype=0&web=1&channel=chunlei&app_id=250528&bdstoken=" + bdstoken, None, CK, ua="netdisk;11.4.51.4.19", ref="https://pan.baidu.com/disk/main")
    print("[FILEMETAS]", st, json.dumps(mj, ensure_ascii=False)[:400])
    dlist = mj.get("info") or []
    if dlist:
        dlink = dlist[0].get("dlink") or ""
        print("[DLINK]", dlink[:200])
        if dlink:
            cmd = ["curl", "-s", "-o", "/dev/null", "-w", "HTTP %{http_code} | %{size_download}B",
                   "-r", "0-1048575", "-m", "30", "-H", "User-Agent: netdisk;11.4.51.4.19",
                   "-H", "Referer: https://pan.baidu.com/", "-H", "Cookie: " + CK, dlink]
            out = subprocess.run(cmd, capture_output=True, text=True).stdout
            print("[DL]", out)
