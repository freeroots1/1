#!/usr/bin/env python3
"""Fetch AI news from RSS feeds and specific APIs."""
import json
import urllib.request
import time

def fetch_url(url, headers=None, timeout=15):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"ERROR: {e}"

# 1. 36kr RSS
print("=== 36kr RSS ===", flush=True)
try:
    content = fetch_url("https://36kr.com/feed")
    if not content.startswith("ERROR"):
        import re
        items = re.findall(r'<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>.*?<link>(.*?)</link>.*?</item>', content, re.DOTALL)
        ai_keywords = ["AI", "人工智能", "大模型", "智能", "OpenAI", "芯片", "GPU", "机器人", "LLM", "Agent", "Claude", "GPT", "Gemini", "DeepSeek", "Kimi", "模型", "算法"]
        ai_news = []
        for title, link in items:
            if any(kw in title for kw in ai_keywords):
                ai_news.append({"title": title.strip(), "url": link.strip()})
        print(f"Found {len(ai_news)} AI news items", flush=True)
        for n in ai_news[:10]:
            print(f"  {n['title']}", flush=True)
            print(f"    {n['url']}", flush=True)
    else:
        print(f"  Error: {content}", flush=True)
except Exception as e:
    print(f"  36kr error: {e}", flush=True)

# 2. Hacker News top stories (JSON API)
print("\n=== Hacker News Top Stories ===", flush=True)
try:
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        story_ids = json.loads(resp.read().decode())[:20]
    
    ai_keywords_hn = ["ai", "llm", "gpt", "claude", "gemini", "openai", "anthropic", "model", "machine learning", "neural", "transformer", "agent", "copilot", "cursor", "coding"]
    ai_stories = []
    for sid in story_ids:
        try:
            url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            with urllib.request.urlopen(url, timeout=5) as resp:
                story = json.loads(resp.read().decode())
                if story and story.get("title"):
                    title_lower = story["title"].lower()
                    if any(kw in title_lower for kw in ai_keywords_hn):
                        ai_stories.append({
                            "title": story["title"],
                            "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                            "score": story.get("score", 0)
                        })
        except:
            pass
        time.sleep(0.2)
    
    print(f"Found {len(ai_stories)} AI-related stories", flush=True)
    for s in sorted(ai_stories, key=lambda x: x["score"], reverse=True)[:8]:
        print(f"  [{s['score']}pts] {s['title']}", flush=True)
        print(f"    {s['url']}", flush=True)
except Exception as e:
    print(f"  HN error: {e}", flush=True)

# 3. Search for specific AI news with DuckDuckGo (text search)
print("\n=== DuckDuckGo AI News ===", flush=True)
try:
    url = "https://html.duckduckgo.com/html/?q=AI+news+August+2026"
    content = fetch_url(url)
    if not content.startswith("ERROR"):
        import re
        # Extract results from DDG HTML
        results = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', content)
        print(f"Found {len(results)} results", flush=True)
        for href, title in results[:10]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            print(f"  {title}", flush=True)
            print(f"    {href}", flush=True)
    else:
        print(f"  DDG: {content}", flush=True)
except Exception as e:
    print(f"  DDG error: {e}", flush=True)

# 4. TechCrunch AI RSS
print("\n=== TechCrunch AI ===", flush=True)
try:
    content = fetch_url("https://techcrunch.com/category/artificial-intelligence/feed/")
    if not content.startswith("ERROR"):
        import re
        items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?</item>', content, re.DOTALL)
        print(f"Found {len(items)} items", flush=True)
        for title, link in items[:8]:
            print(f"  {title.strip()}", flush=True)
            print(f"    {link.strip()}", flush=True)
    else:
        print(f"  TechCrunch: {content}", flush=True)
except Exception as e:
    print(f"  TechCrunch error: {e}", flush=True)

# 5. VentureBeat AI RSS
print("\n=== VentureBeat AI ===", flush=True)
try:
    content = fetch_url("https://venturebeat.com/category/ai/feed/")
    if not content.startswith("ERROR"):
        import re
        items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?</item>', content, re.DOTALL)
        print(f"Found {len(items)} items", flush=True)
        for title, link in items[:8]:
            print(f"  {title.strip()}", flush=True)
            print(f"    {link.strip()}", flush=True)
    else:
        print(f"  VentureBeat: {content}", flush=True)
except Exception as e:
    print(f"  VentureBeat error: {e}", flush=True)

print("\n=== DONE ===", flush=True)
