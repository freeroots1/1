# 调试：页面方案子目录 share/list 直调
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
    return r.stdout

CK = get_baidu_cookie()
cookies = []
for part in CK.split(';'):
    part = part.strip()
    if '=' in part:
        k, v = part.split('=', 1)
        cookies.append({'name': k.strip(), 'value': v.strip(), 'domain': '.baidu.com', 'path': '/'})

surl = '1t2OS-TdqY1ZVDes3ODrGpQ'
pwd = 'xja8'
fs_id = '1019263049549248'

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'])
    ctx = b.new_context(viewport={'width':1440,'height':1000}, user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122 Safari/537.36')
    page = ctx.new_page()
    ctx.add_cookies(cookies)
    page.goto(f'https://pan.baidu.com/s/{surl}?pwd={pwd}', wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(8000)
    # 1) wxlist 拿 uk
    uk_info = page.evaluate("""async ({surl, pwd}) => {
        const u = 'https://pan.baidu.com/share/wxlist?channel=weixin&version=2.2.2&clienttype=25&web=1';
        const b = 'pwd=' + encodeURIComponent(pwd) + '&shorturl=' + surl + '&root=1';
        const r = await fetch(u, {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'netdisk'}, body: b});
        return await r.json();
    }""", {'surl': surl, 'pwd': pwd})
    uk = (uk_info.get('data') or {}).get('uk') or ''
    print('uk:', uk)
    # 2) share/list 直调
    dir_path = '/sharelink' + str(uk) + '-' + fs_id
    print('dir_path:', dir_path)
    r2 = page.evaluate("""async ({surl, dir}) => {
        const u = 'https://pan.baidu.com/share/list?web=5&app_id=250528&desc=1&showempty=0&page=1&num=100&order=time&shorturl=' + surl + '&dir=' + encodeURIComponent(dir) + '&view_mode=1&channel=chunlei&web=1&bdstoken=&clienttype=0&logid=' + Date.now();
        const r = await fetch(u, {headers: {'Referer': 'https://pan.baidu.com/s/1' + surl}});
        const t = await r.text();
        return t;
    }""", {'surl': surl, 'dir': dir_path})
    print('share/list 原始:', str(r2)[:400])
    b.close()
