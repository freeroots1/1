# 调试：点击文件夹捕获 share/list（真实点击路线）
import json, subprocess, time
from playwright.sync_api import sync_playwright
SETTINGS='/home/ubuntu/app/coolink/data/settings.json'; NODE='/usr/bin/node'
def get_baidu_cookie():
    js="""const fs=require('fs'),crypto=require('crypto');const j=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));const key=crypto.scryptSync(process.env.ADMIN_PASSWORD||'AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});const b=Buffer.from(j.data,'base64');const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));const o=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));process.stdout.write(o.cookies.baidu||'');"""
    return subprocess.run([NODE,'-e',js,SETTINGS],capture_output=True,text=True,timeout=15).stdout
CK=get_baidu_cookie(); cookies=[]
for part in CK.split(';'):
    part=part.strip()
    if '=' in part:
        k,v=part.split('=',1); cookies.append({'name':k.strip(),'value':v.strip(),'domain':'.baidu.com','path':'/'})
surl='1t2OS-TdqY1ZVDes3ODrGpQ'; pwd='xja8'; fs_id='1019263049549248'
share_list=[]
def on_resp(r):
    try:
        if 'share/list' in r.url:
            j=json.loads(r.text())
            if j.get('errno')==0: share_list.append(j)
    except: pass
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'])
    ctx=b.new_context(viewport={'width':1440,'height':1000},user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122 Safari/537.36')
    page=ctx.new_page()
    page.on('response', on_resp)
    ctx.add_cookies(cookies)
    page.goto(f'https://pan.baidu.com/s/{surl}?pwd={pwd}',wait_until='domcontentloaded',timeout=45000)
    page.wait_for_timeout(9000)
    print('初始 share/list 捕获:', len(share_list))
    # 找页面上的文件夹文本（"0"）
    # 尝试点击
    try:
        page.get_by_text('0', exact=True).first.click(timeout=5000)
        print('点击 0 成功')
    except Exception as e:
        print('点击失败:', str(e)[:80])
    page.wait_for_timeout(6000)
    print('点击后 share/list 捕获:', len(share_list))
    if share_list:
        lst=share_list[-1].get('list') or []
        print('捕获 list 数量:', len(lst))
        for f in lst[:5]:
            print(' ', f.get('server_filename'), f.get('isdir'), f.get('fs_id'))
    b.close()
