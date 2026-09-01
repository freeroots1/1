#!/usr/bin/env python3
"""Fetch more AI news and learning resources."""
import json
import urllib.request
import time
import re

def fetch_url(url, headers=None, timeout=8):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"ERROR: {e}"

# 1. More TechCrunch articles
print("=== More TechCrunch ===", flush=True)
try:
    content = fetch_url("https://techcrunch.com/category/artificial-intelligence/feed/?paged=2")
    if not content.startswith("ERROR"):
        items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?</item>', content, re.DOTALL)
        for title, link in items[:6]:
            title = re.sub(r'&#8217;', "'", title).strip()
            print(f"  {title}", flush=True)
            print(f"    {link.strip()}", flush=True)
except Exception as e:
    print(f"  Error: {e}", flush=True)

# 2. The Verge AI (different feed URL)
print("\n=== The Verge AI ===", flush=True)
try:
    content = fetch_url("https://www.theverge.com/rss/index.xml")
    if not content.startswith("ERROR"):
        items = re.findall(r'<entry>.*?<title>(.*?)</title>.*?<link[^>]*href="([^"]+)".*?</entry>', content, re.DOTALL)
        ai_keywords = ["AI", "GPT", "Claude", "OpenAI", "Anthropic", "Google", "Gemini", "model", "agent", "robot"]
        ai_items = [(t, l) for t, l in items if any(kw in t for kw in ai_keywords)]
        print(f"Found {len(ai_items)} AI items", flush=True)
        for title, link in ai_items[:6]:
            print(f"  {title.strip()}", flush=True)
            print(f"    {link.strip()}", flush=True)
except Exception as e:
    print(f"  Error: {e}", flush=True)

# 3. Zhihu AI learning resources
print("\n=== Zhihu AI Learning ===", flush=True)
try:
    # Search Zhihu for AI learning resources
    url = "https://api.zhihu.com/search_v3?q=AI%E5%AD%A6%E4%B9%A0%E8%B5%84%E6%BA%90&t=general&correction=1&offset=0&limit=10"
    content = fetch_url(url)
    if not content.startswith("ERROR"):
        data = json.loads(content)
        items = data.get("data", [])
        print(f"Found {len(items)} items", flush=True)
        for item in items[:5]:
            obj = item.get("object", {})
            title = obj.get("title", "")
            url = obj.get("url", "")
            print(f"  {title}", flush=True)
            print(f"    {url}", flush=True)
    else:
        print(f"  Error: {content}", flush=True)
except Exception as e:
    print(f"  Error: {e}", flush=True)

# 4. Zhihu hot topics - more AI related
print("\n=== Zhihu Hot Topics ===", flush=True)
try:
    url = "https://api.zhihu.com/topstory/hot-lists/total?limit=50"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        ai_keywords = ["AI", "人工智能", "大模型", "GPT", "Claude", "Kimi", "深度学习", "机器学习", "智能", "OpenAI", "谷歌", "Gemini", "芯片", "GPU", "英伟达", "算法", "机器人", "自动驾驶", "AGI", "LLM", "模型", "算力"]
        ai_topics = []
        for item in data.get("data", []):
            title = item["target"]["title"]
            if any(kw in title for kw in ai_keywords):
                ai_topics.append({
                    "title": title,
                    "heat": item.get("detail_text", ""),
                    "excerpt": item["target"].get("excerpt", "")[:80]
                })
        print(f"Found {len(ai_topics)} AI topics", flush=True)
        for t in ai_topics[:10]:
            print(f"  [{t['heat']}] {t['title']}", flush=True)
            print(f"    {t['excerpt']}", flush=True)
except Exception as e:
    print(f"  Error: {e}", flush=True)

# 5. Search for Bilibili videos via search.bilibili.com
print("\n=== Bilibili via search ===", flush=True)
try:
    # Try the mobile API
    url = "https://app.bilibili.com/x/v2/search/type?keyword=AI%E6%95%99%E7%A8%8B&type=video&pn=1&ps=10"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
        "Referer": "https://www.bilibili.com"
    }
    content = fetch_url(url, headers)
    if not content.startswith("ERROR"):
        data = json.loads(content)
        items = data.get("data", {}).get("item", [])
        print(f"Found {len(items)} items", flush=True)
        for item in items[:5]:
            title = item.get("title", "")
            bvid = item.get("bvid", "")
            print(f"  {title}", flush=True)
            print(f"    https://www.bilibili.com/video/{bvid}", flush=True)
    else:
        print(f"  Error: {content}", flush=True)
except Exception as e:
    print(f"  Error: {e}", flush=True)

print("\n=== DONE ===", flush=True)
