from playwright.sync_api import sync_playwright

SHARE = "VOzZsgPqtVS_wJej8qWRv9P9A1"
PARENT = "VOKHHl8Dkr_6vqdSaHV2AdyWA1"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page()
    # 先打开分享页（非 API），让迅雷前端自己初始化 captcha_token 到 localStorage
    pg.goto(f"https://pan.xunlei.com/s/{SHARE}?pwd=c233", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(8000)
    
    js = """
    async (args) => {
        let captcha = '';
        for (const k of Object.keys(localStorage)) {
            if (k.includes('captcha_')) {
                try { const v = JSON.parse(localStorage.getItem(k)); captcha = v.token || ''; } catch(e) {}
            }
        }
        if (!captcha) return JSON.stringify({err: 'localStorage 无 captcha_token'});
        const did = localStorage.getItem('deviceid') || '';
        const u1 = 'https://api-pan.xunlei.com/drive/v1/share?share_id=' + args.share +
                   '&pass_code=' + args.pwd + '&limit=1&pass_code_token=&page_token=&scene=NORMAL';
        const r1 = await fetch(u1, { headers: {
            'x-device-id': did, 'x-client-id': 'Xqp0kJBXWhwaTpB6', 'x-captcha-token': captcha
        }});
        const j1 = await r1.json();
        const pct = j1.pass_code_token || '';
        if (!pct) return JSON.stringify({err: 'pct 空', s1: j1.share_status});
        const u2 = 'https://api-pan.xunlei.com/drive/v1/share/detail?share_id=' + args.share +
                   '&parent_id=' + args.parent + '&pass_code_token=' + encodeURIComponent(pct) + '&limit=100';
        const r2 = await fetch(u2, { headers: {
            'x-device-id': did, 'x-client-id': 'Xqp0kJBXWhwaTpB6', 'x-captcha-token': captcha
        }});
        const j2 = await r2.json();
        const fl = j2.file_list || j2.files || [];
        return JSON.stringify({ok: true, files: fl.length, first: (fl[0]||{}).name || ''});
    }
    """
    res = pg.evaluate(js, {"share": SHARE, "pwd": "c233", "parent": PARENT})
    print(res)
    b.close()
