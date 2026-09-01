#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    pg = b.new_context(viewport={"width": 1440, "height": 1000}).new_page()
    pg.goto("http://115.159.226.161", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(3000)
    pg.evaluate("localStorage.setItem('pandl_downloader_settings', JSON.stringify({downloader_type:'gopeed',add_url:'http://127.0.0.1:9999/api/v1',rpc_secret:'',rpc_transport:'http',download_path:''}))")
    pg.reload(wait_until="domcontentloaded")
    pg.wait_for_timeout(2500)
    pg.fill("input[placeholder*=粘贴]", "https://pan.baidu.com/s/1FDBzHv-IkPUpqM6IzqdlHA?pwd=85rt")
    pg.fill("input[placeholder*=码]", "85rt")
    pg.get_by_role("button", name="获取文件列表").first.click()
    pg.wait_for_timeout(10000)
    try: pg.locator(".n-modal-mask").first.click(timeout=800); pg.wait_for_timeout(200)
    except Exception: pass
    info = pg.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('.parse-file-action-btn')).map(b => ({text: b.innerText.trim().slice(0,40), disabled: b.disabled}));
        const tree = window.__pandlTree;
        return {btns, treeLen: tree ? tree.length : 0, firstHasChildren: tree && tree[0] ? (tree[0].children ? tree[0].children.length : 'no children key') : null};
    }""")
    print("状态:", json.dumps(info, ensure_ascii=False, indent=2))
    pg.screenshot(path="/tmp/baidu_btn.png")
    b.close()
