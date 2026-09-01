#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    pg = b.new_context(viewport={"width": 1440, "height": 1000}).new_page()
    pg.goto("http://115.159.226.161", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(3000)
    pg.fill("input[placeholder*=粘贴]", "https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1?pwd=c233")
    pg.fill("input[placeholder*=码]", "c233")
    pg.get_by_role("button", name="获取文件列表").first.click()
    pg.wait_for_timeout(9000)
    try:
        pg.locator(".n-modal-mask").first.click(timeout=800); pg.wait_for_timeout(200)
    except Exception:
        pass
    pg.get_by_role("button", name="进入文件夹").first.click()
    pg.wait_for_timeout(6000)
    try:
        pg.locator(".n-modal-mask").first.click(timeout=800); pg.wait_for_timeout(200)
    except Exception:
        pass
    pg.locator(".parse-file-action-btn:has-text(\"下载\")").first.click()
    pg.wait_for_timeout(5000)
    info = pg.evaluate("""() => {
        const modals = document.querySelectorAll('.n-modal');
        const dialogs = document.querySelectorAll('.n-card-modal');
        return {
            nModals: modals.length,
            nDialogs: dialogs.length,
            modalTexts: Array.from(modals).map(m => m.innerText.slice(0, 200)),
            dialogTexts: Array.from(dialogs).map(m => m.innerText.slice(0, 200))
        };
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    b.close()
