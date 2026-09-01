#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面拿 dlink+md5 → Python/curl 调 locatedownload → 真实 URL → 下载验证"""
import json, sys, subprocess, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

SETTINGS = "/home/ubuntu/app/coolink/data/settings.json"
NODE = "/usr/bin/node"

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

surl, pwd, fs_id = sys.argv[1], sys.argv[2], sys.argv[3]
TARGET_FID = "136719795820605"
CK = get_baidu_cookie()
cookies = []
for part in CK.split(";"):
    part = part.strip()
    if "=" in part:
        k, v = part.split("=", 1)
        cookies.append({"name": k.strip(), "value": v.strip(), "domain": ".baidu.com", "path": "/"})

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 1440, "height": 1000},
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    page = ctx.new_page()
    share_list = []
    def on_resp(r):
        try:
            if "share/list" in r.url:
                j = json.loads(r.text())
                if j.get("errno") == 0:
                    share_list.append(j)
        except Exception:
            pass
    page.on("response", on_resp)
    ctx.add_cookies(cookies)
    full_surl = surl if surl.startswith("1") else "1" + surl
    page.goto("https://pan.baidu.com/s/%s?pwd=%s" % (full_surl, pwd), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(8000)
    for fid in str(fs_id).split("/"):
        target = ""
        for j in reversed(share_list):
            for it in (j.get("list") or []):
                if str(it.get("fs_id")) == fid:
                    target = it.get("server_filename") or ""
                    break
            if target:
                break
        if not target:
            break
        try:
            page.get_by_text(target, exact=True).first.click(timeout=6000)
            page.wait_for_timeout(6000)
        except Exception:
            pass
    res = page.evaluate("""async ({surl, fid}) => {
        const DEVICE_ID = "BB91C9B818963851F99A99261A70E37E|VUFQKX5JL";
        const KEY = "B8ec24caf34ef7227c66767d29ffd3fb";
        const ts = Math.floor(Date.now()/1000);
        const sekey = window.currentSekey || "";
        const post = "encrypt=0&uk=1101495852727&product=share&primaryid=7512369792&fid_list=" +
            encodeURIComponent("[" + fid + "]") + "&extra=" + encodeURIComponent(JSON.stringify({sekey: sekey}));
        const enc = new TextEncoder();
        const keyData = await crypto.subtle.importKey("raw", enc.encode(KEY), {name: "HMAC", hash: "SHA-1"}, false, ["sign"]);
        const sig = await crypto.subtle.sign("HMAC", keyData, enc.encode(post + "_" + DEVICE_ID + "_" + ts));
        const sign = Array.from(new Uint8Array(sig)).map(x => x.toString(16).padStart(2, "0")).join("");
        const url = "https://pan.baidu.com/api/sharedownload?sign=" + sign + "&timestamp=" + ts +
            "&devuid=" + encodeURIComponent(DEVICE_ID) + "&channel=android&clienttype=1&version=11.10.4&web=1&app_id=250528";
        const r = await fetch(url, {method: "POST",
            headers: {"Content-Type": "application/x-www-form-urlencoded", "Referer": "https://pan.baidu.com/s/1" + surl},
            body: post});
        const j = await r.json();
        const lst = j.list || [];
        const item = (Array.isArray(lst) && lst[0]) ? lst[0] : null;
        if (!item || !item.dlink) return {errno: j.errno, note: "no dlink"};
        return {errno: j.errno, dlink: item.dlink, md5: item.md5 || "", fid: fid, ts: ts};
    }""", {"surl": full_surl, "fid": TARGET_FID})
    b.close()

print("[SD]", json.dumps(res, ensure_ascii=False)[:300])
dlink = res.get("dlink", "")
md5 = res.get("md5", "")
ts = res.get("ts", 0)
if not dlink:
    raise SystemExit("no dlink")
# dlinkParts（去域名前缀，编码 |）
if "?" in dlink:
    dlinkParts = dlink.split("?")[1]
else:
    dlinkParts = dlink.replace("https://d.pcs.baidu.com", "").replace("http://d.pcs.baidu.com", "")
dlinkParts = dlinkParts.replace("|", "%7C")
# 2026-08-20 13:45：百度对 md5 加密（第9位替换 + 异或重排，见 foxxorcat helper.ts decryptMd5）
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
true_md5 = decrypt_md5(md5)
print("[MD5]", md5, "->", true_md5)
loc_path = "/War3_1.28.zip"  # 试文件路径
loc_url = ("https://d.pcs.baidu.com/rest/2.0/pcs/file?app_id=250528&method=locatedownload&check_blue=1&es=1&esl=1&ant=1"
           "&path=" + urllib.request.quote(loc_path, safe="") + "&" + dlinkParts +
           "&ver=4.0&dtype=1&err_ver=1.0&ehps=1&eck=1&vip=2&open_pflag=0&wp_retry_num=2&dpkg=1&sd=0&clienttype=9&version=3.0.20.18"
           "&time=" + str(ts) + "&rand=92f0d4559f696c68a0dc3f5c2d9b98e916d21752"
           "&devuid=BDIMXV2-O_5C2E29F6772E440AB445B1E38F6FF2BF-C_0-D_E823_8FA6_BF53_0001_001B_448B_4A23_0665.-M_581122B7C835-V_04B71596"
           "&channel=0&version_app=7.44.7.1")
print("[LOC]", loc_url[:150])
req = urllib.request.Request(loc_url, headers={
    "User-Agent": "netdisk;11.4.51.4.19",
    "Referer": "https://pan.baidu.com/",
    "Cookie": CK,
})
try:
    with urllib.request.urlopen(req, timeout=30) as x:
        lj = json.loads(x.read().decode())
    urls = lj.get("urls") or []
    real_url = ""
    for u in urls:
        if "allall" in (u.get("url") or ""):
            real_url = u["url"]
            break
    if not real_url and urls:
        real_url = urls[0].get("url") or ""
    print("[LOC-RESULT] errno=%s urls=%d real=%s" % (lj.get("errno"), len(urls), real_url[:120]))
    if real_url:
        # 下载验证
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "HTTP %{http_code} | %{size_download}B | %{speed_download}B/s",
               "-r", "0-1048575", "-m", "40", "-H", "User-Agent: netdisk;11.4.51.4.19",
               "-H", "Referer: https://pan.baidu.com/", "-H", "Cookie: " + CK, real_url]
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        print("[DL]", out)
except urllib.error.HTTPError as e:
    print("[LOC-ERR] HTTP", e.code, e.read().decode()[:200])
except Exception as e:
    print("[LOC-ERR]", str(e)[:200])
