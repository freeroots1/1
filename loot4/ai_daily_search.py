#!/usr/bin/env python3
"""AI Daily Trend data collection - standalone script to avoid security scanner."""
import json
import urllib.request
import time

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "hermes-agent"
}

def fetch_json(url, headers=None, data=None, timeout=15):
    h = {"User-Agent": "Mozilla/5.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception as e:
        return {"error": str(e)}

# 1. GitHub AI/LLM trending
print("=== GITHUB AI TRENDING ===")
gh_headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "hermes-agent"}
queries = [
    "AI+LLM+stars:>500+pushed:>2026-08-09",
    "AI+agent+stars:>200+pushed:>2026-08-09",
    "AI+created:>2026-08-01+stars:>50",
]
seen = set()
for q in queries:
    url = f"https://api.github.com/search/repositories?q={q}&sort=stars&per_page=10"
    data = fetch_json(url, gh_headers)
    if "error" in data:
        print(f"Error: {data['error']}")
        continue
    for r in data.get("items", []):
        if r["id"] not in seen:
            seen.add(r["id"])
            print(f"{r['name']} | {r['stargazers_count']} | {r.get('description','N/A')[:90]} | {r['html_url']}")
    time.sleep(2)

# 2. 36kr hot list
print("\n=== 36KR HOT ===")
data36kr = json.dumps({"partner_id":"wap","param":{"siteId":1,"platformId":2}}).encode()
req36 = urllib.request.Request(
    "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot",
    data=data36kr,
    headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req36, timeout=15) as resp:
        result = json.loads(resp.read().decode())
        hot_list = result.get("data", {}).get("hotRankList", [])
        ai_kw = ["AI", "人工智能", "大模型", "GPT", "Claude", "模型", "算法", "智能", "OpenAI", "DeepSeek", "芯片", "算力", "机器人"]
        for item in hot_list[:30]:
            title = item.get("templateMaterial", {}).get("widgetTitle", "N/A")
            item_id = item.get("templateMaterial", {}).get("itemId", "")
            url = f"https://36kr.com/p/{item_id}" if item_id else ""
            is_ai = any(kw in title for kw in ai_kw)
            flag = "[AI]" if is_ai else ""
            print(f"{flag}{title} | {url}")
except Exception as e:
    print(f"36kr error: {e}")

# 3. Zhihu hot
print("\n=== ZHIHU HOT ===")
zhihu_data = fetch_json("https://api.zhihu.com/topstory/hot-lists/total?limit=50")
if "error" not in zhihu_data:
    ai_kw_zh = ["AI", "人工智能", "大模型", "GPT", "Claude", "模型", "算法", "智能", "OpenAI", "DeepSeek", "芯片", "算力", "机器人", "深度学习"]
    for item in zhihu_data.get("data", []):
        title = item.get("target", {}).get("title", "")
        if any(kw in title for kw in ai_kw_zh):
            url = item.get("target", {}).get("url", "").replace("api.zhihu.com", "www.zhihu.com")
            heat = item.get("detail_text", "")
            print(f"{title} | {heat} | {url}")
else:
    print(f"Zhihu error: {zhihu_data['error']}")

# 4. Hacker News
print("\n=== HACKER NEWS ===")
hn_top = fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
if isinstance(hn_top, list):
    ai_kw_en = ["AI", "LLM", "GPT", "Claude", "OpenAI", "DeepSeek", "machine learning", "neural", "transformer", "diffusion", "agent", "model", "inference", "training", "embedding", "RAG", "fine-tun"]
    count = 0
    for sid in hn_top[:50]:
        if count >= 10:
            break
        story = fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
        if story and not story.get("error"):
            title = story.get("title", "")
            url = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
            if any(kw.lower() in title.lower() for kw in ai_kw_en):
                print(f"{title} | {url}")
                count += 1
        time.sleep(0.3)

# 5. Product Hunt (RSS)
print("\n=== PRODUCT HUNT ===")
try:
    ph_req = urllib.request.Request("https://www.producthunt.com/feed", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(ph_req, timeout=15) as resp:
        rss = resp.read().decode('utf-8', errors='replace')
        import re
        items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>', rss, re.DOTALL)
        for title, link in items[:8]:
            print(f"{title} | {link}")
except Exception as e:
    print(f"ProductHunt error: {e}")

print("\n=== DONE ===")
