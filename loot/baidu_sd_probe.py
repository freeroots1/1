#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面上下文自建 sharedownload（带 currentSekey）→ 明文 dlink → locatedownload 真实 URL"""
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
    def on_resp(r):
        try:
            if 'share/list' in r.url:
                j = json.loads(r.text())
                if j.get('errno') == 0:
                    share_list.append(j)
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
    # 页面上下文：tplconfig → sharedownload（带 sekey）→ locatedownload
    result = page.evaluate("""async ({surl, fid}) => {
        const out = {sekey: '', sign: '', ts: 0, dlink: '', located: ''};
        try { out.sekey = window.currentSekey || ''; } catch(e) {}
        try {
            // 1) tplconfig 拿 sign/timestamp
            const tc = await fetch('https://pan.baidu.com/share/tplconfig?surl=' + surl +
                '&fields=sign,timestamp&channel=chunlei&web=1&app_id=250528&clienttype=0&dp-logid=' + Date.now(),
                {headers: {'Referer': 'https://pan.baidu.com/s/1' + surl}});
            const tcj = await tc.json();
            out.sign = (tcj.data && tcj.data.sign) || '';
            out.ts = (tcj.data && tcj.data.timestamp) || '';
            out.sign_raw = JSON.stringify(tcj).slice(0, 200);
            // 2) sharedownload（带 sekey + encrypt=0）
            // uk/primaryid 从页面 window 变量取（SHARE_INFO 等），兜底硬编码
            let uk = '', pid = '';
            try {
                if (window.shareInfo) { uk = window.shareInfo.uk || ''; pid = window.shareInfo.share_id || ''; }
            } catch(e) {}
            const body = 'encrypt=0&extra=' + encodeURIComponent(JSON.stringify({sekey: out.sekey})) +
                '&product=share&timestamp=' + out.ts + '&uk=' + (uk || '1101495852727') +
                '&primaryid=' + (pid || '7512369792') +
                '&fid_list=' + encodeURIComponent('[' + fid + ']') +
                '&type=nolimit';
            const sd = await fetch('https://pan.baidu.com/api/sharedownload?channel=chunlei&clienttype=5&web=1&app_id=250528&sign=' +
                encodeURIComponent(out.sign) + '&timestamp=' + out.ts,
                {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded', 'Referer': 'https://pan.baidu.com/s/1' + surl}, body: body});
            const sdj = await sd.json();
            out.sd_raw = JSON.stringify(sdj).slice(0, 300);
            const lst = sdj.list || [];
            if (Array.isArray(lst) && lst[0]) {
                out.dlink = lst[0].dlink || '';
            } else if (typeof lst === 'string') {
                out.dlink = lst.slice(0, 50) + '(encrypted-list)';
            }
        } catch(e) { out.err = String(e).slice(0, 150); }
        return out;
    }""", {'surl': full_surl, 'fid': '136719795820605'})  # War3_1.28.zip 的 fs_id
    print("[RESULT]", json.dumps(result, ensure_ascii=False), file=sys.stderr)
    b.close()
