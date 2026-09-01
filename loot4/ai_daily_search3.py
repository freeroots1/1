#!/usr/bin/env python3
"""Quick fetch of 36kr and Zhihu AI news."""
import json
import urllib.request
import time

# 1. 36kr hot list
print("=== 36KR HOT ===")
data36kr = json.dumps({"partner_id":"wap","param":{"siteId":1,"platformId":2}}).encode()
req36 = urllib.request.Request(
    "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot",
    data=data36kr,
    headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req36, timeout=10) as resp:
        result = json.loads(resp.read().decode())
        hot_list = result.get("data", {}).get("hotRankList", [])
        ai_kw = ["AI", "人工智能", "大模型", "GPT", "Claude", "模型", "算法", "智能", "OpenAI", "DeepSeek", "芯片", "算力", "机器人", "Anthropic", "谷歌", "Google", "英伟达", "NVIDIA", "苹果", "Apple", "特斯拉", "Tesla", "自动驾驶", "量子", "具身", "Copilot", "Gemini", "Llama", "Meta"]
        for item in hot_list[:40]:
            title = item.get("templateMaterial", {}).get("widgetTitle", "N/A")
            item_id = item.get("templateMaterial", {}).get("itemId", "")
            url = f"https://36kr.com/p/{item_id}" if item_id else ""
            is_ai = any(kw in title for kw in ai_kw)
            if is_ai:
                print(f"[AI] {title} | {url}")
except Exception as e:
    print(f"36kr error: {e}")

# 2. Zhihu hot
print("\n=== ZHIHU HOT ===")
try:
    zh_req = urllib.request.Request("https://api.zhihu.com/topstory/hot-lists/total?limit=50", 
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(zh_req, timeout=10) as resp:
        zhihu_data = json.loads(resp.read().decode())
        ai_kw_zh = ["AI", "人工智能", "大模型", "GPT", "Claude", "模型", "算法", "智能", "OpenAI", "DeepSeek", "芯片", "算力", "机器人", "深度学习", "Anthropic", "谷歌", "Google", "英伟达", "NVIDIA", "苹果", "特斯拉", "自动驾驶", "量子", "具身", "Copilot", "Gemini", "Llama", "Meta"]
        for item in zhihu_data.get("data", []):
            title = item.get("target", {}).get("title", "")
            if any(kw in title for kw in ai_kw_zh):
                qid = item.get("target", {}).get("id", "")
                url = f"https://www.zhihu.com/question/{qid}" if qid else ""
                heat = item.get("detail_text", "")
                print(f"{title} | {heat} | {url}")
except Exception as e:
    print(f"Zhihu error: {e}")

# 3. Hacker News (just top 30, filter for AI)
print("\n=== HACKER NEWS ===")
try:
    hn_req = urllib.request.Request("https://hacker-news.firebaseio.com/v0/topstories.json",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(hn_req, timeout=10) as resp:
        hn_top = json.loads(resp.read().decode())
    
    ai_kw_en = ["ai ", "ai-", "llm", "gpt", "claude", "openai", "deepseek", "machine learning", 
                 "neural", "transformer", "agent", "model", "inference", "anthropic", "gemini", 
                 "copilot", "reasoning", "benchmark", "deep learning", "diffusion", "embedding"]
    count = 0
    for sid in hn_top[:40]:
        if count >= 8:
            break
        try:
            story_req = urllib.request.Request(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(story_req, timeout=5) as resp:
                story = json.loads(resp.read().decode())
            title = story.get("title", "")
            url = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
            score = story.get("score", 0)
            if any(kw.lower() in title.lower() for kw in ai_kw_en):
                print(f"{title} | score:{score} | {url}")
                count += 1
        except:
            pass
        time.sleep(0.2)
except Exception as e:
    print(f"HN error: {e}")

# 4. Product Hunt
print("\n=== PRODUCT HUNT ===")
try:
    ph_req = urllib.request.Request("https://www.producthunt.com/feed", headers={
        "User-Agent": "Mozilla/5.0"
    })
    with urllib.request.urlopen(ph_req, timeout=10) as resp:
        rss = resp.read().decode('utf-8', errors='replace')
        import re
        items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>', rss, re.DOTALL)
        for title, link in items[:10]:
            print(f"{title} | {link}")
except Exception as e:
    print(f"ProductHunt error: {e}")

print("\n=== DONE ===")
