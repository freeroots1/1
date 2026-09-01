#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证后删除生效：列出各网盘根目录，确认转存文件已清理（无残留）"""
import json, subprocess, sys, urllib.request, urllib.parse

sys.path.insert(0, "/home/ubuntu/pwand-playwright")

def baidu_root_files():
    js = """
const fs=require('fs'),crypto=require('crypto');
const j=JSON.parse(fs.readFileSync('/home/ubuntu/app/coolink/data/settings.json','utf8'));
const key=crypto.scryptSync('AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});
const b=Buffer.from(j.data,'base64');
const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
const o=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));
process.stdout.write(o.cookies.baidu||'');
"""
    CK = subprocess.run(["/usr/bin/node", "-e", js], capture_output=True, text=True).stdout.strip()
    # gettemplatevariable → bdstoken → list
    h = {"User-Agent": "netdisk;11.4.51.4.19", "Referer": "https://pan.baidu.com/", "Cookie": CK}
    r = urllib.request.Request("https://pan.baidu.com/api/gettemplatevariable?fields=%5B%22bdstoken%22%5D", headers=h)
    with urllib.request.urlopen(r, timeout=15) as x:
        bd = (json.loads(x.read().decode()).get("result") or {}).get("bdstoken", "")
    url = "https://pan.baidu.com/api/list?dir=%2F&num=100&order=time&desc=1&page=1&showempty=0&web=1&channel=chunlei&app_id=250528&bdstoken=" + bd + "&clienttype=0"
    r2 = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(r2, timeout=15) as x:
        j = json.loads(x.read().decode())
    return [f.get("server_filename") for f in (j.get("list") or [])]

def xunlei_root_files():
    from xunlei_download import req, load_cache, get_captcha
    cache = load_cache()
    jwt = cache.get("jwt", "")
    tok = get_captcha()
    st, j = req("GET", "https://api-pan.xunlei.com/drive/v1/files?parent_id=&limit=100&page_token=&order_by=", token=tok, jwt=jwt)
    return [f.get("name") for f in (j.get("files") or [])]

print("=== 百度网盘根目录 ===")
try:
    print(" ", baidu_root_files())
except Exception as e:
    print("  错误:", str(e)[:120])
print("=== 迅雷云盘根目录 ===")
try:
    print(" ", xunlei_root_files())
except Exception as e:
    print("  错误:", str(e)[:120])
