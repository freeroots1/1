#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量查各网盘解析后 window.__pandlTree + full_tree 响应"""
import json
from playwright.sync_api import sync_playwright

CASES = [
    ("pan123", "123", "https://4001733858.share.123pan.cn/123pan/nbicMh-e27Xh?pwd=HSgd#", "HSgd"),
    ("baidu", "百度", "https://pan.baidu.com/s/1FDBzHv-IkPUpqM6IzqdlHA?pwd=85rt", "85rt"),
    ("mcloud", "移动", "https://yun.139.com/shareweb/#/w/i/2wFGxNHV4061i", "hsgj"),
    ("xunlei", "迅雷", "https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1?pwd=c233", "c233"),
]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    pg = b.new_context(viewport={"width": 1440, "height": 1000}).new_page()
    pg.goto("http://115.159.226.161", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(3000)
    for key, name, url, pwd in CASES:
        try:
            pg.get_by_text(name, exact=False).first.click()
            pg.wait_for_timeout(500)
            pg.fill("input[placeholder*=粘贴]", url)
            if pwd:
                try:
                    pg.fill("input[placeholder*=码]", pwd)
                except Exception:
                    pass
            pg.get_by_role("button", name="获取文件列表").first.click()
            pg.wait_for_timeout(9000)
            try:
                pg.locator(".n-modal-mask").first.click(timeout=800); pg.wait_for_timeout(200)
            except Exception:
                pass
            st = pg.evaluate("() => { const t = window.__pandlTree; return {has: !!t, len: t ? t.length : 0, first: t && t[0] ? {name: t[0].name, c: t[0].children ? t[0].children.length : 0} : null}; }")
            print("%s __pandlTree: %s" % (name, json.dumps(st, ensure_ascii=False)))
        except Exception as e:
            print("%s 异常: %s" % (name, str(e)[:100]))
        pg.goto("http://115.159.226.161", wait_until="domcontentloaded", timeout=30000)
        pg.wait_for_timeout(800)
    b.close()
