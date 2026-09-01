#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""决定性测试：Android dlink × 多种请求头组合下载"""
import json, sys, subprocess, time
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

surl, pwd, fid = sys.argv[1], sys.argv[2], sys.argv[3]
CK = get_baidu_cookie()
cookies = []
for part in CK.split(";"):
    part = part.strip()
    if "=" in part:
        k, v = part.split("=", 1)
        cookies.append({"name": k.strip(), "value": v.strip(), "domain": ".baidu.com", "path": "/"})

# 重试拿 dlink（最多 3 次，防限流）
dlink = ""
for attempt in range(3):
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
            ctx = b.new_context(viewport={"width": 1440, "height": 1000},
                                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")
            page = ctx.new_page()
            ctx.add_cookies(cookies)
            page.goto("https://pan.baidu.com/s/1%s?pwd=%s" % (surl, pwd), wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(8000)
            res = page.evaluate("""async ({surl, fid}) => {
                const DEVICE_ID = "BB91C9B818963851F99A99261A70E37E|VUFQKX5JL";
                const KEY = "B8ec24caf34ef7227c66767d29ffd3fb";
                const ts = Math.floor(Date.now()/1000);
                const sekey = window.currentSekey || "";
                const post = "encrypt=0&uk=1101495852727&product=share&primaryid=7512369792&fid_list=" +
                    encodeURIComponent("[" + fid + "]") + "&extra=" + encodeURIComponent(JSON.stringify({sekey: sekey}));
                const enc = new TextEncoder();
                const kd = await crypto.subtle.importKey("raw", enc.encode(KEY), {name: "HMAC", hash: "SHA-1"}, false, ["sign"]);
                const sig = await crypto.subtle.sign("HMAC", kd, enc.encode(post + "_" + DEVICE_ID + "_" + ts));
                const sign = Array.from(new Uint8Array(sig)).map(x => x.toString(16).padStart(2, "0")).join("");
                const url = "https://pan.baidu.com/api/sharedownload?sign=" + sign + "&timestamp=" + ts +
                    "&devuid=" + encodeURIComponent(DEVICE_ID) + "&channel=android&clienttype=1&version=11.10.4&web=1&app_id=250528";
                const r = await fetch(url, {method: "POST",
                    headers: {"Content-Type": "application/x-www-form-urlencoded", "Referer": "https://pan.baidu.com/s/1" + surl},
                    body: post});
                const j = await r.json();
                const lst = j.list;
                if (Array.isArray(lst) && lst[0] && lst[0].dlink) {
                    return {ok: 1, dlink: lst[0].dlink, md5: lst[0].md5 || ""};
                }
                return {ok: 0, errno: j.errno, list_type: typeof lst, raw: JSON.stringify(j).slice(0, 150)};
            }""", {"surl": surl, "fid": fid})
            b.close()
        if res.get("ok"):
            dlink = res["dlink"]
            print("[DLINK]", dlink)
            print("[MD5]", res.get("md5", ""))
            break
        else:
            print("[TRY%d]" % (attempt + 1), json.dumps(res)[:150])
            time.sleep(5)
    except Exception as e:
        print("[TRY%d ERR]" % (attempt + 1), str(e)[:100])
        time.sleep(5)

if not dlink:
    print("[FAIL] 无法获取 dlink")
    raise SystemExit(1)

# 下载测试（多请求头组合）
ck_all = "; ".join("%s=%s" % (c["name"], c["value"]) for c in cookies)
combos = [
    ("UA=Transmission/2.77", {"User-Agent": "Transmission/2.77", "Cookie": ck_all}),
    ("UA=Transmission + Referer=pan.baidu.com", {"User-Agent": "Transmission/2.77", "Referer": "https://pan.baidu.com/", "Cookie": ck_all}),
    ("UA=netdisk + Referer", {"User-Agent": "netdisk;11.4.51.4.19", "Referer": "https://pan.baidu.com/", "Cookie": ck_all}),
    ("UA=Chrome + Referer", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36", "Referer": "https://pan.baidu.com/", "Cookie": ck_all}),
]
for label, hdrs in combos:
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}|%{size_download}|%{speed_download}", "-r", "0-1048575", "-m", "30"]
    for k, v in hdrs.items():
        cmd += ["-H", "%s: %s" % (k, v)]
    cmd.append(dlink)
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    print("[DL %s] %s" % (label, out))
