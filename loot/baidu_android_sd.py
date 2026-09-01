#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Android 签名方式 sharedownload（gopeed/foxxorcat 同款）"""
import json, sys, subprocess, hmac, hashlib, time
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

surl, pwd, fs_id = sys.argv[1], sys.argv[2], sys.argv[3]
TARGET_FID = '136719795820605'  # War3_1.28.zip
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
    # Android 签名 sharedownload（在页面上下文，用 window.currentSekey）
    res = page.evaluate("""async ({surl, fid}) => {
        const DEVICE_ID = 'BB91C9B818963851F99A99261A70E37E|VUFQKX5JL';
        const KEY = 'B8ec24caf34ef7227c66767d29ffd3fb';
        const ts = Math.floor(Date.now()/1000);
        const sekey = window.currentSekey || '';
        const post = 'encrypt=0&uk=1101495852727&product=share&primaryid=7512369792&fid_list=' +
            encodeURIComponent('[' + fid + ']') + '&extra=' + encodeURIComponent(JSON.stringify({sekey: sekey}));
        // HMAC-SHA1
        const enc = new TextEncoder();
        const keyData = await crypto.subtle.importKey('raw', enc.encode(KEY), {name: 'HMAC', hash: 'SHA-1'}, false, ['sign']);
        const sig = await crypto.subtle.sign('HMAC', keyData, enc.encode(post + '_' + DEVICE_ID + '_' + ts));
        const sign = Array.from(new Uint8Array(sig)).map(x => x.toString(16).padStart(2, '0')).join('');
        const url = 'https://pan.baidu.com/api/sharedownload?sign=' + sign + '&timestamp=' + ts +
            '&devuid=' + encodeURIComponent(DEVICE_ID) + '&channel=android&clienttype=1&version=11.10.4&web=1&app_id=250528';
        const r = await fetch(url, {method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded', 'Referer': 'https://pan.baidu.com/s/1' + surl},
            body: post});
        const j = await r.json();
        const lst = j.list;
        let dlink = '';
        if (Array.isArray(lst) && lst[0]) dlink = (lst[0].dlink || '').slice(0, 100);
        else if (typeof lst === 'string') dlink = lst.slice(0, 40) + '...(encrypted len=' + lst.length + ')';
        return {errno: j.errno, dlink: dlink, raw: JSON.stringify(j).slice(0, 250)};
    }""", {'surl': full_surl, 'fid': TARGET_FID})
    print("[ANDROID-SD]", json.dumps(res, ensure_ascii=False), file=sys.stderr)
    b.close()
