#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度下载直链混合方案：Playwright 页面上下文（sekey/uk/shareid + sharedownload）→ Python locatedownload"""
import json, sys, subprocess, urllib.request, urllib.error, urllib.parse, re
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
    uk_share = {}
    def on_req(r):
        u = r.url
        m = re.search(r"risklabel\?[^ ]*uk=(\d+)&share_id=(\d+)", u)
        if m:
            uk_share["uk"] = m.group(1)
            uk_share["share_id"] = m.group(2)
    page.on("request", on_req)
    ctx.add_cookies(cookies)
    full_surl = surl if surl.startswith("1") else "1" + surl
    page.goto("https://pan.baidu.com/s/%s?pwd=%s" % (full_surl, pwd), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(8000)
    print("[UK]", uk_share, file=sys.stderr)

    # 页面上下文：gettemplatevariable → tplconfig → sharedownload（gopeed 全套）
    res = page.evaluate("""async ({surl, fid, uk, pid}) => {
        const out = {};
        const REF = "https://pan.baidu.com/disk/main";
        try {
            const bd = await fetch('https://pan.baidu.com/api/gettemplatevariable?fields=["bdstoken"]', {headers: {Referer: REF}});
            const bdj = await bd.json();
            out.bdstoken = (bdj.result && bdj.result.bdstoken) || "";
        } catch(e) { out.bdstoken_err = String(e); }
        const logid = "Rjg4QThGNzY3QkNFRkY4Qjc3MDVEM0ExMkE0MEQyNDA6Rkc9MQ==";
        try {
            const tc = await fetch('https://pan.baidu.com/share/tplconfig?surl=' + surl +
                '&fields=sign,timestamp&channel=chunlei&web=1&app_id=250528&bdstoken=' + out.bdstoken +
                '&logid=' + logid + '&clienttype=0&dp-logid=' + Date.now(), {headers: {Referer: REF}});
            const tcj = await tc.json();
            out.sign = (tcj.data && tcj.data.sign) || "";
            out.ts = (tcj.data && tcj.data.timestamp) || "";
            out.tpl_errno = tcj.errno;
        } catch(e) { out.tpl_err = String(e); }
        const sekey = window.currentSekey || "";
        try {
            const body = 'encrypt=0&extra=' + encodeURIComponent(JSON.stringify({sekey: sekey})) +
                '&product=share&timestamp=' + out.ts + '&uk=' + uk + '&primaryid=' + pid +
                '&fid_list=' + encodeURIComponent('[' + fid + ']') + '&type=nolimit';
            const sd = await fetch('https://pan.baidu.com/api/sharedownload?channel=chunlei&clienttype=5&web=1&app_id=250528&sign=' +
                encodeURIComponent(out.sign) + '&timestamp=' + out.ts,
                {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded', Referer: REF}, body: body});
            const sdj = await sd.json();
            out.sd_errno = sdj.errno;
            const lst = sdj.list;
            if (Array.isArray(lst) && lst[0]) {
                out.dlink = lst[0].dlink || "";
                out.md5 = lst[0].md5 || "";
            } else if (typeof lst === "string") {
                out.encrypted = lst.slice(0, 30);
            } else {
                out.sd_raw = JSON.stringify(sdj).slice(0, 150);
            }
        } catch(e) { out.sd_err = String(e); }
        return out;
    }""", {"surl": full_surl, "fid": fid, "uk": uk_share.get("uk", ""), "pid": uk_share.get("share_id", "")})
    print("[SD]", json.dumps(res, ensure_ascii=False), file=sys.stderr)
    b.close()

dlink = res.get("dlink", "")
md5 = res.get("md5", "")
ts = res.get("ts", 0)
if not dlink:
    print("[FAIL] 未拿到 dlink:", json.dumps(res)[:200])
    raise SystemExit(1)
dlinkParts = dlink.split("?")[1] if "?" in dlink else dlink.replace("https://d.pcs.baidu.com", "").replace("http://d.pcs.baidu.com", "")
dlinkParts = dlinkParts.replace("|", "%7C")
true_md5 = decrypt_md5(md5)
print("[MD5]", md5, "->", true_md5, file=sys.stderr)
loc = ("https://d.pcs.baidu.com/rest/2.0/pcs/file?app_id=250528&method=locatedownload&check_blue=1&es=1&esl=1&ant=1"
       "&path=%s&%s&ver=4.0&dtype=1&err_ver=1.0&ehps=1&eck=1&vip=2&open_pflag=0&wp_retry_num=2&dpkg=1&sd=0&clienttype=9"
       "&version=3.0.20.18&time=%s&rand=92f0d4559f696c68a0dc3f5c2d9b98e916d21752"
       "&devuid=BDIMXV2-O_5C2E29F6772E440AB445B1E38F6FF2BF-C_0-D_E823_8FA6_BF53_0001_001B_448B_4A23_0665.-M_581122B7C835-V_04B71596"
       "&channel=0&version_app=7.44.7.1" % (urllib.parse.quote(true_md5, safe=""), dlinkParts, ts))
req = urllib.request.Request(loc, headers={"User-Agent": "netdisk;11.4.51.4.19", "Referer": "https://pan.baidu.com/", "Cookie": CK})
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
    print("[LOC] errno=%s urls=%d" % (lj.get("errno"), len(urls)))
    print("[LOC-RAW]", json.dumps(lj)[:200])
    if real_url:
        print("[REAL]", real_url[:150])
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "HTTP %{http_code} | %{size_download}B | %{speed_download}B/s",
               "-r", "0-1048575", "-m", "40", "-H", "User-Agent: netdisk;11.4.51.4.19",
               "-H", "Referer: https://pan.baidu.com/", "-H", "Cookie: " + CK, real_url]
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        print("[DL]", out)
except urllib.error.HTTPError as e:
    print("[LOC-ERR] HTTP", e.code, e.read().decode()[:200])
except Exception as e:
    print("[LOC-ERR]", str(e)[:200])
