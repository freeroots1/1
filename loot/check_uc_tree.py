#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    pg = b.new_context(viewport={"width": 1440, "height": 1000}).new_page()
    pg.goto("http://115.159.226.161", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(3000)
    pg.get_by_text("UC", exact=False).first.click()
    pg.wait_for_timeout(500)
    pg.fill("input[placeholder*=粘贴]", "https://drive.uc.cn/s/e483ce6ce30e4?public=1")
    pg.get_by_role("button", name="获取文件列表").first.click()
    pg.wait_for_timeout(9000)
    try:
        pg.locator(".n-modal-mask").first.click(timeout=800); pg.wait_for_timeout(200)
    except Exception:
        pass
    st = pg.evaluate("() => { const t = window.__pandlTree; return {has: !!t, len: t ? t.length : 0, first: t && t[0] ? {name: t[0].name, children: t[0].children ? t[0].children.length : 0} : null}; }")
    print("__pandlTree:", json.dumps(st, ensure_ascii=False))
    fr = pg.evaluate("""async () => {
        const r = await fetch('/api/uc/list', {method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({url: 'https://drive.uc.cn/s/e483ce6ce30e4?public=1'})});
        const j = await r.json();
        return {full_tree: !!j.full_tree, ft_len: j.full_tree ? j.full_tree.length : 0, ok: j.ok};
    }""")
    print("uc/list full_tree:", json.dumps(fr, ensure_ascii=False))
    b.close()
