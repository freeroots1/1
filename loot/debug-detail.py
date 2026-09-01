from playwright.sync_api import sync_playwright
import json

SHARE = "VOzZsgPqtVS_wJej8qWRv9P9A1"
PARENT = "VOKHHl8Dkr_6vqdSaHV2AdyWA1"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page()
    pg.goto("https://pan.xunlei.com/", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(5000)
    
    js = """
    async (args) => {
        // 拿 captcha token（页面 localStorage）
        let captcha = '';
        for (const k of Object.keys(localStorage)) {
            if (k.includes('captcha_')) {
                try { const v = JSON.parse(localStorage.getItem(k)); captcha = v.token || ''; } catch(e) {}
            }
        }
        const did = localStorage.getItem('deviceid') || '';
        
        // Step1: share?limit=1 拿 pass_code_token
        const u1 = 'https://api-pan.xunlei.com/drive/v1/share?share_id=' + args.share +
                   '&pass_code=' + args.pwd + '&limit=1&keyword=&pass_code_token=&page_token=&scene=NORMAL&order_by=';
        const r1 = await fetch(u1, { headers: {
            'x-device-id': did, 'x-client-id': 'Xqp0kJBXWhwaTpB6',
            'x-captcha-token': captcha, 'Referer': 'https://pan.xunlei.com/'
        }});
        const j1 = await r1.json();
        const pct = j1.pass_code_token || '';
        
        // Step2: detail
        const u2 = 'https://api-pan.xunlei.com/drive/v1/share/detail?share_id=' + args.share +
                   '&parent_id=' + args.parent + '&pass_code_token=' + encodeURIComponent(pct) +
                   '&limit=100&keyword=&scene=NORMAL&order_by=';
        const r2 = await fetch(u2, { headers: {
            'x-device-id': did, 'x-client-id': 'Xqp0kJBXWhwaTpB6',
            'x-captcha-token': captcha, 'Referer': 'https://pan.xunlei.com/'
        }});
        const j2 = await r2.json();
        return JSON.stringify({
            step1_status: j1.share_status,
            step1_error: j1.error_description || '',
            pct_len: pct.length,
            step2_status: r2.status,
            step2_body: JSON.stringify(j2).slice(0, 400),
        });
    }
    """
    res = pg.evaluate(js, {"share": SHARE, "pwd": "c233", "parent": PARENT})
    print(res)
    b.close()
