#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度下载直链 - 纯 API 照抄 gopeed-extension-baiduwp 完整流程"""
import json, sys, subprocess, time, hmac, hashlib, urllib.request, urllib.error, urllib.parse

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

def req(method, url, body=None, cookie="", headers=None):
    h = {"User-Agent": UA, "Referer": REF}
    if cookie:
        h["Cookie"] = cookie
    if headers:
        h.update(headers)
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

def decrypt_md5(md5):
    try:
        c9 = ord(md5[9]) - ord('g')
        if c9 < 0:
            return md5
        key2 = md5[:9] + format(c9, 'x') + md5[10:]
        key3 = ''
        for i in range(len(key2)):
            key3 += format(int(key2[i], 16) ^ (15 & i), 'x')
        return key3[8:16] + key3[0:8] + key3[24:32] + key3[16:24]
    except Exception:
        return md5

surl, pwd, fid = sys.argv[1], sys.argv[2], sys.argv[3]
CK = get_baidu_cookie()
print("[CK]", CK[:60], "len=", len(CK))

# 1) wxlist root=1 → uk/shareid/seckey
st, j = req("POST", "https://pan.baidu.com/share/wxlist?channel=weixin&version=2.2.2&clienttype=25&web=1",
            "pwd=%s&shorturl=%s&root=1" % (urllib.parse.quote(pwd), surl), CK)
print("[WXLIST] errno=%s" % j.get("errno"))
if j.get("errno") != 0:
    print("[WXLIST-RAW]", json.dumps(j)[:200])
    raise SystemExit(1)
d = j.get("data") or {}
uk, shareid, seckey = d.get("uk", ""), d.get("shareid", ""), d.get("seckey", "")
print("[INFO] uk=%s shareid=%s seckey=%s" % (uk, shareid, str(seckey)[:30]))

# 2) gettemplatevariable → bdstoken
st, j = req("GET", 'https://pan.baidu.com/api/gettemplatevariable?fields=["bdstoken"]', None, CK)
bdstoken = ((j.get("result") or {}).get("bdstoken")) or ""
print("[BDSTOKEN]", bdstoken[:30] if bdstoken else "(empty)")

# 3) tplconfig（带 bdstoken + logid）→ sign/timestamp
logid = "Rjg4QThGNzY3QkNFRkY4Qjc3MDVEM0ExMkE0MEQyNDA6Rkc9MQ=="
st, j = req("GET", "https://pan.baidu.com/share/tplconfig?surl=%s&fields=sign,timestamp&channel=chunlei&web=1&app_id=250528&bdstoken=%s&logid=%s&clienttype=0&dp-logid=%d" % (surl, bdstoken, logid, int(time.time()*1000)), None, CK)
sign = ((j.get("data") or {}).get("sign")) or ""
timestamp = ((j.get("data") or {}).get("timestamp")) or ""
print("[TPL] sign=%s ts=%s" % (sign[:20], timestamp))

# 4) sharedownload（照抄 gopeed body）
body = 'encrypt=0&extra={"sekey":"%s"}&product=share&timestamp=%s&uk=%s&primaryid=%s&fid_list=[%s]&type=nolimit' % (
    seckey, timestamp, uk, shareid, fid)
st, j = req("POST", "https://pan.baidu.com/api/sharedownload?channel=chunlei&clienttype=5&web=1&app_id=250528&sign=%s&timestamp=%s" % (sign, timestamp),
            body, CK)
lst = j.get("list")
item = (lst or [{}])[0] if isinstance(lst, list) else None
print("[SD] errno=%s list_type=%s" % (j.get("errno"), type(lst).__name__))
if item and item.get("dlink"):
    dlink = item["dlink"]
    md5 = item.get("md5", "")
    print("[SD-OK] dlink=%s" % dlink[:80])
    # 5) locatedownload
    dlinkParts = dlink.split("?")[1] if "?" in dlink else dlink.replace("https://d.pcs.baidu.com", "").replace("http://d.pcs.baidu.com", "")
    dlinkParts = dlinkParts.replace("|", "%7C")
    true_md5 = decrypt_md5(md5)
    print("[MD5] %s -> %s" % (md5, true_md5))
    loc = ("https://d.pcs.baidu.com/rest/2.0/pcs/file?app_id=250528&method=locatedownload&check_blue=1&es=1&esl=1&ant=1"
           "&path=%s&%s&ver=4.0&dtype=1&err_ver=1.0&ehps=1&eck=1&vip=2&open_pflag=0&wp_retry_num=2&dpkg=1&sd=0&clienttype=9"
           "&version=3.0.20.18&time=%s&rand=92f0d4559f696c68a0dc3f5c2d9b98e916d21752"
           "&devuid=BDIMXV2-O_5C2E29F6772E440AB445B1E38F6FF2BF-C_0-D_E823_8FA6_BF53_0001_001B_448B_4A23_0665.-M_581122B7C835-V_04B71596"
           "&channel=0&version_app=7.44.7.1" % (urllib.parse.quote(true_md5, safe=""), dlinkParts, timestamp))
    st, lj = req("GET", loc, None, CK, headers={"User-Agent": "netdisk;11.4.51.4.19"})
    urls = lj.get("urls") or []
    real_url = ""
    for u in urls:
        if "allall" in (u.get("url") or ""):
            real_url = u["url"]
            break
    if not real_url and urls:
        real_url = urls[0].get("url") or ""
    print("[LOC] errno=%s urls=%d" % (lj.get("errno"), len(urls)))
    print("[LOC-RAW]", json.dumps(lj)[:300])
    if real_url:
        print("[REAL]", real_url[:150])
        # 下载验证
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "HTTP %{http_code} | %{size_download}B | %{speed_download}B/s",
               "-r", "0-1048575", "-m", "40", "-H", "User-Agent: netdisk;11.4.51.4.19",
               "-H", "Referer: https://pan.baidu.com/", "-H", "Cookie: " + CK, real_url]
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        print("[DL]", out)
else:
    print("[SD-RAW]", json.dumps(j)[:300])
