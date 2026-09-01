#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baidu_page.py — 百度网盘分享解析（Playwright 真实点击 + 捕获响应）
服务器版。支持两种模式：
  - 列文件：进入文件夹 → 捕获 share/list 响应
  - --download <文件名>：点击文件「下载」→ 捕获 sharedownload 响应 → 返回直链

用法:
  python baidu_page.py <surl> [pwd] [--dir <子目录 fs_id>]
  python baidu_page.py <surl> [pwd] --download <文件名> [--dir <子目录 fs_id>]
输出 JSON: {ok, files:[...]} 或 {ok, url}

2026-08-20 13:05 修改（对话丢失后按 12:49 思考方案落地）：
  子目录不再页面 fetch share/list（errno 140 风控拒绝），改为：
  wxlist root=1 查 fs_id → server_filename 映射 → 真实点击文件夹名 → 捕获 share/list 响应
"""
import json, sys, time, subprocess
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

def main():
    surl = sys.argv[1] if len(sys.argv) > 1 else ''
    pwd = sys.argv[2] if len(sys.argv) > 2 else ''
    subdir = ''
    dl_name = ''
    rest = sys.argv[3:]
    i = 0
    while i < len(rest):
        if rest[i] == '--dir' and i + 1 < len(rest): subdir = rest[i + 1]; i += 2
        elif rest[i] == '--download' and i + 1 < len(rest): dl_name = rest[i + 1]; i += 2
        else: i += 1
    if not surl:
        print(json.dumps({'ok': False, 'error': '缺少 surl'}, ensure_ascii=False)); return 1
    CK = get_baidu_cookie()
    cookies = []
    for part in CK.split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            cookies.append({'name': k.strip(), 'value': v.strip(), 'domain': '.baidu.com', 'path': '/'})
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'])
            ctx = b.new_context(viewport={'width': 1440, 'height': 1000},
                                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
            page = ctx.new_page()
            share_list = []
            sharedl = []
            def on_resp(r):
                try:
                    if 'share/list' in r.url:
                        j = json.loads(r.text())
                        if j.get('errno') == 0:
                            share_list.append(j)
                    elif 'sharedownload' in r.url:
                        j = json.loads(r.text())
                        if j.get('errno') == 0:
                            sharedl.append(j)
                except Exception:
                    pass
            page.on('response', on_resp)
            ctx.add_cookies(cookies)
            full_surl = surl if surl.startswith('1') else '1' + surl
            page.goto(f'https://pan.baidu.com/s/{full_surl}?pwd={pwd}', wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(7000)

            # ---- 子目录：wxlist 根层查 fs_id → server_filename → 真实点击文件夹名 ----
            if subdir:
                fs_id = str(subdir).replace('/', '').strip()
                try:
                    root_info = page.evaluate("""async ({surl, pwd}) => {
                        const u = 'https://pan.baidu.com/share/wxlist?channel=weixin&version=2.2.2&clienttype=25&web=1';
                        const b = 'pwd=' + encodeURIComponent(pwd) + '&shorturl=' + surl + '&root=1';
                        const r = await fetch(u, {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'netdisk'}, body: b});
                        return await r.json();
                    }""", {'surl': surl, 'pwd': pwd})
                    target_name = ''
                    for it in (root_info.get('list') or []):
                        if str(it.get('fs_id')) == fs_id:
                            target_name = it.get('server_filename') or it.get('filename') or ''
                            break
                    if target_name:
                        # 真实点击文件夹名，让页面自己发 share/list（带 dir 参数）→ on_resp 捕获
                        page.get_by_text(target_name, exact=True).first.click(timeout=6000)
                        page.wait_for_timeout(6000)
                    else:
                        # fs_id 未命中：尝试按文本点击（兼容直接传文件夹名的老用法）
                        try:
                            page.get_by_text(subdir, exact=False).first.click(timeout=5000)
                            page.wait_for_timeout(6000)
                        except Exception:
                            pass
                except Exception:
                    pass

            # ---- 下载模式：点击文件 → 弹窗「下载」 ----
            if dl_name:
                try:
                    page.get_by_text(dl_name, exact=False).first.click(timeout=5000)
                    page.wait_for_timeout(1500)
                    page.evaluate("""() => {
                        const all = document.querySelectorAll('a,button,span,div');
                        for (const e of all) {
                            const t = (e.innerText||'').trim();
                            if (t === '下载' && e.children.length < 3) {
                                const r = e.getBoundingClientRect();
                                if (r.width > 0 && r.height > 0) { e.click(); return; }
                            }
                        }
                    }""")
                    page.wait_for_timeout(6000)
                except Exception:
                    pass
            else:
                # 列文件模式：若页面没自动发 root=1，点击触发
                try:
                    page.mouse.click(320, 180)
                    page.wait_for_timeout(4000)
                except Exception:
                    pass
            # fallback：列文件 root=1
            if not share_list and not dl_name:
                try:
                    all_cookie = '; '.join(f"{c['name']}={c['value']}" for c in ctx.cookies() if 'baidu.com' in c['domain'])
                    r2 = page.evaluate("""async ({surl, ck}) => {
                        const h = {'Referer': 'https://pan.baidu.com/s/1' + surl, 'Cookie': ck};
                        const u = 'https://pan.baidu.com/share/list?web=5&app_id=250528&desc=1&showempty=0&page=1&num=100&order=time&shorturl=' + surl + '&root=1&view_mode=1&channel=chunlei&web=1&bdstoken=&clienttype=0&logid=' + Date.now();
                        const r = await fetch(u, {headers: h});
                        return await r.json();
                    }""", {'surl': surl, 'ck': all_cookie})
                    if r2.get('errno') == 0:
                        share_list.append(r2)
                except Exception:
                    pass
            b.close()
        # 下载模式返回直链
        if dl_name:
            if sharedl:
                j = sharedl[-1]
                lst = j.get('list')
                url = ''
                if isinstance(lst, list):
                    for item in lst:
                        if isinstance(item, dict) and item.get('dlink'):
                            url = item['dlink']
                            break
                if not url and isinstance(lst, str):
                    url = lst
                if url:
                    print(json.dumps({'ok': True, 'url': url}, ensure_ascii=False)); return 0
                print(json.dumps({'ok': False, 'error': 'sharedownload 未返回直链', 'raw': str(lst)[:200]}, ensure_ascii=False)); return 1
            print(json.dumps({'ok': False, 'error': '未捕获到下载响应'}, ensure_ascii=False)); return 1
        # 列文件模式
        files = []
        for j in share_list:
            files = [(f.get('server_filename') or f.get('filename'), f.get('size') or 0, f.get('isdir') in (1, '1', True), f.get('fs_id')) for f in (j.get('list') or [])]
        if not files:
            print(json.dumps({'ok': False, 'error': '未捕获到文件列表'}, ensure_ascii=False)); return 1
        out = [{'name': f[0], 'size': f[1], 'is_dir': f[2], 'fs_id': f[3]} for f in files]
        print(json.dumps({'ok': True, 'files': out}, ensure_ascii=False)); return 0
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)[:200]}, ensure_ascii=False)); return 1

if __name__ == '__main__':
    sys.exit(main())
