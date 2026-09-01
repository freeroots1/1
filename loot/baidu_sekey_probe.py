#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测百度页面 sekey/uk/shareid + 自己发 sharedownload 拿明文 dlink"""
import json, sys, subprocess
from playwright.sync_api import sync_playwright

SETTINGS = '/home/ubuntu/app/coolink/data/settings.json'
NODE = '/usr/bin/node'

def get_baidu_cookie():
    js = """
const fs=require('fs'),crypto=require('crypto');
const j=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
const key=crypto.scryptSync(process.env.ADMIN_PASSWORD||'AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});
const b=Buffer.from(j.data,'base64');
const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
const o=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));
process.stdout.write(o.cookies.baidu||'');
"""
    r = subprocess.run([NODE, '-e', js, SETTINGS], capture_output=True, text=True, timeout=15)
    return r.stdout.strip()

surl, pwd, fs_id, dl_name = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
CK = get_baidu_cookie()
cookies = []
for part in CK.split(';'):
    part = part.strip()
    if '=' in part:
        k, v = part.split('=', 1)
        cookies.append({'name': k.strip(), 'value': v.strip(), 'domain': '.baidu.com', 'path': '/'})

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'])
    ctx = b.new_context(viewport={'width': 1440, 'height': 1000},
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    page = ctx.new_page()
    share_list = []
    infos = []
    def on_resp(r):
        u = r.url
        try:
            if 'share/list' in u:
                j = json.loads(r.text())
                if j.get('errno') == 0:
                    share_list.append(j)
            if 'wxlist' in u or 'share/init' in u or 'subscribe' in u:
                infos.append((u[:120], r.text()[:300]))
        except Exception:
            pass
    page.on('response', on_resp)
    ctx.add_cookies(cookies)
    full_surl = surl if surl.startswith('1') else '1' + surl
    page.goto('https://pan.baidu.com/s/%s?pwd=%s' % (full_surl, pwd), wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(8000)
    # 进文件夹
    for fid in str(fs_id).split('/'):
        target = ''
        for j in reversed(share_list):
            for it in (j.get('list') or []):
                if str(it.get('fs_id')) == fid:
                    target = it.get('server_filename') or ''
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
    # 探测 sekey：从 window 变量 / localStorage / performance entries
    probe = page.evaluate("""() => {
        const out = {win_keys: [], ls_keys: [], sekey: '', uk: '', shareid: ''};
        try {
            out.win_keys = Object.keys(window).filter(k => /seckey|sekey|share/i.test(k)).slice(0, 20);
        } catch(e) {}
        try {
            out.ls_keys = Object.keys(localStorage).filter(k => /seckey|sekey|share|rand/i.test(k)).slice(0, 20);
        } catch(e) {}
        // performance entries 里找 subscribe sekey
        try {
            const es = performance.getEntriesByType('resource').map(e => e.name);
            for (const u of es) {
                const m = u.match(/sekey=([^&]+)/);
                if (m) { out.sekey = decodeURIComponent(m[1]); break; }
            }
        } catch(e) {}
        return out;
    }""")
    print("[PROBE]", json.dumps(probe, ensure_ascii=False), file=sys.stderr)
    print("[INFOS]", json.dumps(infos, ensure_ascii=False)[:600], file=sys.stderr)
    b.close()
