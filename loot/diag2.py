import json, time
from playwright.sync_api import sync_playwright
SITE = "http://115.159.226.161"
INIT = "localStorage.setItem(\x27pandl_downloader_settings\x27, JSON.stringify({downloader_type:\x27gopeed\x27,add_url:\x27http://127.0.0.1:9999/api/v1\x27,rpc_secret:\x27\x27,rpc_transport:\x27http\x27,download_path:\x27\x27}))"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-gpu","--disable-dev-shm-usage"])
    pg = b.new_context(viewport={"width":1440,"height":1000}).new_page()
    JS = []
    pg.on("console", lambda m: JS.append(m.text) if m.type in ("error","warning") else None)
    pg.goto(SITE, wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(3000)
    pg.evaluate(INIT)
    pg.reload(wait_until="domcontentloaded")
    pg.wait_for_timeout(2000)
    # UC 解析
    pg.get_by_text("UC", exact=False).first.click()
    pg.wait_for_timeout(500)
    pg.fill("input[placeholder*=粘贴]", "https://drive.uc.cn/s/e483ce6ce30e4?public=1")
    pg.get_by_role("button", name="获取文件列表").first.click()
    pg.wait_for_timeout(9000)
    try: pg.locator(".n-modal-mask").first.click(timeout=800); pg.wait_for_timeout(200)
    except Exception: pass
    # 检查 __pandlTree
    state = pg.evaluate("""() => {
        const t = window.__pandlTree;
        return {has: !!t, len: t ? t.length : 0, first: t && t[0] ? {name: t[0].name, children: t[0].children ? t[0].children.length : 0} : null};
    }""")
    print("[PANDL-TREE]", json.dumps(state, ensure_ascii=False))
    # 进文件夹
    pg.get_by_role("button", name="进入文件夹").first.click()
    pg.wait_for_timeout(4000)
    try: pg.locator(".n-modal-mask").first.click(timeout=800); pg.wait_for_timeout(200)
    except Exception: pass
    # 点 184.jpg 下载
    api = []
    pg.on("request", lambda r: api.append(r.url.split("/api/")[-1][:50]) if "/api/" in r.url else None)
    api.clear()
    row = pg.locator("tr:has-text(\"184.jpg\")").first
    dl = row.locator("button:has-text(\"下载\")").first
    print("[下载按钮]", dl.count())
    if dl.count():
        dl.click()
        pg.wait_for_timeout(8000)
    else:
        # 找所有按钮
        btns = pg.evaluate("() => Array.from(document.querySelectorAll(\x27button\x27)).map(x => x.innerText.trim()).filter(Boolean).slice(0,20)")
        print("[按钮]", btns)
    print("[API]", api[-3:])
    pg.screenshot(path="/tmp/diag2_uc.png")
    print("[JS]", JS[-3:])
    b.close()
