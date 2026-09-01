"""深挖百度进文件夹后I.value实际内容"""
from playwright.sync_api import sync_playwright
import json, sys
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-gpu","--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width":1440,"height":1000})
    pg = ctx.new_page()
    api_reqs, api_resps = [], []
    pg.on("request", lambda r: api_reqs.append((r.method, r.url, r.post_data[:200] if r.method=="POST" else "")) if "/api/baidu/" in r.url else None)
    pg.on("response", lambda r: api_resps.append((r.status, r.url, r.text()[:300])) if "/api/baidu/" in r.url else None)

    pg.goto("http://115.159.226.161", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(3000)
    pg.fill("input[placeholder*=粘贴]", "https://pan.baidu.com/s/1iZvGy3WB2uZKY1l61BmLJw")
    pg.fill("input[placeholder*=码]", "yvih")
    pg.get_by_role("button", name="获取文件列表").first.click()
    pg.wait_for_timeout(12000)
    try: pg.locator(".n-modal-mask").first.click(timeout=600); pg.wait_for_timeout(200)
    except: pass

    # 在点击"进入文件夹"前，找到前端的响应式 ref
    # 关键：抓 pathStack 和 I.value（需要在 .value 暴露点）
    print("=== 解析后 1 秒 ===")
    # 通过 window 的 hack 找 ref - 尝试 getCurrentInstance
    state = pg.evaluate("""() => {
        // 抓可能的全局 ref
        const ks = Object.keys(window).filter(k => /parse|file|stack|share/i.test(k));
        return {keys: ks, pathStack: window.M ? Object.keys(window.M) : null};
    }""")
    print(json.dumps(state, ensure_ascii=False)[:500])

    print("\n=== API 请求+响应（解析阶段）===")
    for m,u,pd in api_reqs[-3:]:
        print(f" REQ {m} {u[-80:]}")
        if pd: print(f"   body: {pd[:200]}")
    for s,u,t in api_resps[-3:]:
        print(f" RESP {s} {u[-80:]}")
        if s>=200 and s<300: print(f"   body[:200]: {t[:200]}")

    api_reqs.clear(); api_resps.clear()
    enter = pg.get_by_role("button", name="进入文件夹").first
    print("\n=== 点击进入文件夹 ===")
    if enter.count():
        enter.click()
        pg.wait_for_timeout(15000)
        try: pg.locator(".n-modal-mask").first.click(timeout=600); pg.wait_for_timeout(200)
        except: pass

    print("\n=== 进文件夹后 API 请求+响应 ===")
    for m,u,pd in api_reqs:
        print(f" REQ {m} {u[-80:]}")
        if pd: print(f"   body: {pd[:300]}")
    for s,u,t in api_resps:
        print(f" RESP {s} {u[-80:]}")
        if s>=200 and s<300: print(f"   body[:400]: {t[:400]}")
        else: print(f"   ERR body: {t[:200]}")

    # 抓表格
    print("\n=== 表格内容 ===")
    rows = pg.locator("tr").all_inner_texts()
    print(f"  {len(rows)} 行")
    for r in rows[1:6]: print(" 行:", r.replace("\n"," | ")[:150])

    # body 截取
    body = pg.locator("body").inner_text()
    print("\n=== body 200-800 ===")
    print(body[200:800].replace("\n"," | "))
    b.close()
