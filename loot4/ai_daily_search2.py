#!/usr/bin/env python3
"""Collect 36kr, Zhihu, HN, Product Hunt data for AI daily report."""
import json
import urllib.request
import time
import re

def fetch_json(url, headers=None, data=None, timeout=15):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            try:
                return json.loads(raw)
            except:
                return {"raw": raw[:500]}
    except Exception as e:
        return {"error": str(e)}

# 1. 36kr hot list
print("=== 36KR HOT ===")
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
        ai_kw = ["AI", "人工智能", "大模型", "GPT", "Claude", "模型", "算法", "智能", "OpenAI", "DeepSeek", "芯片", "算力", "机器人", "Anthropic", "谷歌", "Google", "英伟达", "NVIDIA", "苹果", "Apple", "特斯拉", "Tesla", "自动驾驶", "量子", "具身"]
        for item in hot_list[:40]:
            title = item.get("templateMaterial", {}).get("widgetTitle", "N/A")
            item_id = item.get("templateMaterial", {}).get("itemId", "")
            url = f"https://36kr.com/p/{item_id}" if item_id else ""
            is_ai = any(kw in title for kw in ai_kw)
            flag = "[AI]" if is_ai else ""
            print(f"{flag}{title} | {url}")
except Exception as e:
    print(f"36kr error: {e}")

# 2. Zhihu hot
print("\n=== ZHIHU HOT ===")
zhihu_data = fetch_json("https://api.zhihu.com/topstory/hot-lists/total?limit=50")
if "error" not in zhihu_data:
    ai_kw_zh = ["AI", "人工智能", "大模型", "GPT", "Claude", "模型", "算法", "智能", "OpenAI", "DeepSeek", "芯片", "算力", "机器人", "深度学习", "Anthropic", "谷歌", "Google", "英伟达", "NVIDIA", "苹果", "特斯拉", "自动驾驶", "量子", "具身", "Copilot", "Gemini"]
    for item in zhihu_data.get("data", []):
        title = item.get("target", {}).get("title", "")
        if any(kw in title for kw in ai_kw_zh):
            qid = item.get("target", {}).get("id", "")
            url = f"https://www.zhihu.com/question/{qid}" if qid else ""
            heat = item.get("detail_text", "")
            print(f"{title} | {heat} | {url}")
else:
    print(f"Zhihu error: {zhihu_data.get('error','unknown')}")

# 3. Hacker News
print("\n=== HACKER NEWS ===")
hn_top = fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
if isinstance(hn_top, list):
    ai_kw_en = ["AI", "LLM", "GPT", "Claude", "OpenAI", "DeepSeek", "machine learning", "neural", "transformer", "diffusion", "agent", "model", "inference", "training", "embedding", "RAG", "fine-tun", "Anthropic", "Gemini", "Copilot", "reasoning", "benchmark"]
    count = 0
    for sid in hn_top[:50]:
        if count >= 10:
            break
        story = fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
        if story and not story.get("error"):
            title = story.get("title", "")
            url = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
            score = story.get("score", 0)
            if any(kw.lower() in title.lower() for kw in ai_kw_en):
                print(f"{title} | score:{score} | {url}")
                count += 1
        time.sleep(0.3)
else:
    print(f"HN error: {hn_top.get('error','unknown')}")

# 4. Product Hunt RSS
print("\n=== PRODUCT HUNT ===")
try:
    ph_req = urllib.request.Request("https://www.producthunt.com/feed", headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(ph_req, timeout=15) as resp:
        rss = resp.read().decode('utf-8', errors='replace')
        items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>', rss, re.DOTALL)
        for title, link in items[:10]:
            print(f"{title} | {link}")
except Exception as e:
    print(f"ProductHunt error: {e}")

print("\n=== DONE ===")
