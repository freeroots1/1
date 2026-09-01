"""强制不缓存测百度进文件夹"""
from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-gpu","--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width":1440,"height":1000})
    # 禁用缓存
    ctx.set_extra_http_headers({"Cache-Control":"no-cache"})
    pg = ctx.new_page()
    pg.route("**/index-main.v3.js*", lambda route: route.continue_())
    pg.goto("http://115.159.226.161?nocache=" + str(__import__("time").time()), wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(2000)
    # 强制刷新
    pg.evaluate("location.reload(true)")
    pg.wait_for_timeout(4000)
    pg.fill("input[placeholder*=粘贴]", "https://pan.baidu.com/s/1iZvGy3WB2uZKY1l61BmLJw")
    pg.fill("input[placeholder*=码]", "yvih")
    pg.get_by_role("button", name="获取文件列表").first.click()
    pg.wait_for_timeout(10000)
    try: pg.locator(".n-modal-mask").first.click(timeout=600); pg.wait_for_timeout(200)
    except: pass
    pg.get_by_role("button", name="进入文件夹").first.click()
    pg.wait_for_timeout(15000)
    try: pg.locator(".n-modal-mask").first.click(timeout=600); pg.wait_for_timeout(200)
    except: pass
    rows = pg.locator("tr").all_inner_texts()
    print(f"=== {len(rows)} 行 ===")
    for r in rows[:8]: print(" 行:", r.replace("\n"," | ")[:120])
    body = pg.locator("body").inner_text()
    # 看是否含 1.jpg
    print("\n包含 1.jpg:", "1.jpg" in body)
    print("body 长度:", len(body))
    b.close()
