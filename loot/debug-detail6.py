from playwright.sync_api import sync_playwright

SHARE = "VOzZsgPqtVS_wJej8qWRv9P9A1"
PARENT = "VOzZrppX04OB37cAcR9aApIyA1"  # 根层返回的文件夹 ID

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page()
    pg.goto(f"https://pan.xunlei.com/s/{SHARE}?pwd=c233", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(8000)
    js = """
    async (args) => {
        let captcha = ''; let pct2 = '';
        for (const k of Object.keys(localStorage)) {
            if (k.includes('captcha_')) { try { captcha = JSON.parse(localStorage.getItem(k)).token || ''; } catch(e) {} }
        }
        const did = localStorage.getItem('deviceid') || '';
pct="";
        const u1 = 'https://api-pan.xunlei.com/drive/v1/share?share_id=' + args.share +
                   '&pass_code=' + args.pwd + '&limit=100&pass_code_token=&page_token=&scene=NORMAL';
        const r1 = await fetch(u1, { headers: {'x-device-id': did, 'x-client-id': 'Xqp0kJBXWhwaTpB6', 'x-captcha-token': captcha} });
        const j1 = await r1.json();
        pct2 = j1.pass_code_token || '';
        pct2 = j1.pass_code_token || '';
        const u2 = 'https://api-pan.xunlei.com/drive/v1/share/detail?share_id=' + args.share +
                   '&parent_id=' + args.parent + '&pass_code_token=' + encodeURIComponent(pct2) + '&limit=100';
        const r2 = await fetch(u2, { headers: {'x-device-id': did, 'x-client-id': 'Xqp0kJBXWhwaTpB6', 'x-captcha-token': captcha} });
        const j2 = await r2.json();
        return JSON.stringify({pct_len: pct2.length, s2: JSON.stringify(j2).slice(0,400)});
    }
    """
    res = pg.evaluate(js, {"share": SHARE, "pwd": "c233", "parent": PARENT})
    print(res)
    b.close()
