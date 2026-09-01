#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度 share/transfer 转存到管理员网盘 → 列管理员网盘 → locatedownload 直链"""
import json, sys, subprocess, time, urllib.request, urllib.error, urllib.parse
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

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 1440, "height": 1000},
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36")
    page = ctx.new_page()
    ctx.add_cookies(cookies)
    page.goto("https://pan.baidu.com/s/1%s?pwd=%s" % (surl, pwd), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(8000)
    # 页面上下文：share/transfer 转存（管理员 cookie + 分享会话）
    res = page.evaluate("""async ({fid}) => {
        const out = {};
        try {
            const body = "path=" + encodeURIComponent("/") + "&fsidlist=" + encodeURIComponent("[" + fid + "]");
            const r = await fetch("https://pan.baidu.com/share/transfer?async=1&ondup=newcopy&channel=chunlei&web=1&app_id=250528&clienttype=0",
                {method: "POST",
                 headers: {"Content-Type": "application/x-www-form-urlencoded", "Referer": "https://pan.baidu.com/s/1" + location.pathname.split("/")[2]},
                 body: body});
            out.status = r.status;
            out.body = await r.text();
        } catch(e) { out.err = String(e).slice(0, 150); }
        return out;
    }""", {"fid": fid})
    print("[TRANSFER]", json.dumps(res, ensure_ascii=False)[:500])
    # 解析 transfer 响应
    try:
        tj = json.loads(res.get("body") or "{}")
        taskid = tj.get("taskid") or tj.get("task_id") or ""
        print("[TASKID]", taskid)
        if taskid:
            # 轮询任务
            for i in range(10):
                time.sleep(1)
                pr = page.evaluate("""async ({tid}) => {
                    const r = await fetch("https://pan.baidu.com/share/querytransfer?taskid=" + tid + "&channel=chunlei&web=1&app_id=250528&clienttype=0",
                        {headers: {"Referer": "https://pan.baidu.com/"}});
                    return await r.json();
                }""", {"tid": taskid})
                print("[QUERY%d]" % i, json.dumps(pr, ensure_ascii=False)[:200])
                info = pr.get("info") or pr.get("task_info") or {}
                if isinstance(info, list) and info:
                    st = info[0].get("status") or ""
                    if st in ("1", "2", "success", "SUCCESS"):
                        print("[TRANSFER-OK]", json.dumps(info[0], ensure_ascii=False)[:300])
                        break
    except Exception as e:
        print("[PARSE-ERR]", str(e)[:100])
    b.close()
