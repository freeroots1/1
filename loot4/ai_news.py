#!/usr/bin/env python3
"""
AI News Aggregator - Fetches AI-related news from Chinese sources.
1) 36kr hot list (filtered for AI keywords)
2) Bing CN search: 'AI人工智能 2026年8月'
3) Bing CN search: 'AI工具 最新发布 2026'
"""

import json
import urllib.request
import urllib.parse
import re
import ssl
import sys

# Disable SSL verification for environments without proper certs
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

AI_KEYWORDS = [
    "AI", "人工智能", "GPT", "大模型", "机器学习", "深度学习",
    "LLM", "ChatGPT", "智能", "算法", "算力", "AGI", "Transformer",
    "Gemini", "Claude", "OpenAI", "百度", "文心", "通义", "智谱",
    "AIGC", "生成式", "Sora", "Midjourney", "Stable Diffusion",
    "芯片", "GPU", "NVIDIA", "英伟达", "自动驾驶", "机器人",
    "量子计算", "Mistral", "Llama", "千问", "DeepSeek", "月之暗面",
    "Kimi", "MiniMax", "零一万物", "百川", "阶跃星辰",
    "Copilot", "Agent", "智能体", "多模态", "向量",
]


def is_ai_related(text):
    text_lower = text.lower()
    for kw in AI_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def fetch_36kr_hot():
    """Fetch 36kr hot list and filter for AI-related items."""
    url = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
    payload = json.dumps({
        "partner_id": "wap",
        "param": {"siteId": 1, "platformId": 2}
    }).encode("utf-8")

    headers = {**HEADERS, "Content-Type": "application/json"}

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items = []
        hot_list = data.get("data", {}).get("hotRankList", [])
        if not hot_list:
            # Try alternative keys
            hot_list = data.get("data", {}).get("itemList", [])
        if not hot_list:
            hot_list = data.get("data", []) if isinstance(data.get("data"), list) else []

        for item in hot_list:
            title = item.get("templateMaterial", {}).get("widgetTitle", "") or item.get("title", "") or item.get("name", "")
            summary = item.get("templateMaterial", {}).get("summary", "") or item.get("summary", "")
            url_link = item.get("templateMaterial", {}).get("widgetContent", "") or item.get("url", "")
            item_id = item.get("itemId", "") or item.get("id", "")

            if not title:
                # Try to extract from nested structures
                title = str(item.get("templateMaterial", {}).get("widgetTitle", ""))

            combined = f"{title} {summary}"
            if is_ai_related(combined):
                items.append({
                    "source": "36kr",
                    "title": title,
                    "summary": summary[:200] if summary else "",
                    "url": url_link,
                    "item_id": str(item_id),
                })

        return {"status": "ok", "total_hot": len(hot_list), "ai_filtered": len(items), "items": items}
    except Exception as e:
        return {"status": "error", "message": str(e), "items": []}


def search_bing_cn(query, label):
    """Search Bing CN for a query and return parsed results."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://cn.bing.com/search?q={encoded_query}&setlang=zh-CN"

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Parse search results from HTML using regex
        results = []

        # Match Bing search result blocks
        # Pattern: <li class="b_algo"><h2><a href="URL">TITLE</a></h2>...<p>SNIPPET</p>
        pattern = r'<li\s+class="b_algo"[^>]*>.*?<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</h2>(.*?)(?=</li>)'
        matches = re.findall(pattern, html, re.DOTALL)

        for url_match, title_raw, content_raw in matches[:15]:
            # Clean HTML tags
            title = re.sub(r'<[^>]+>', '', title_raw).strip()
            # Extract snippet text
            snippet = re.sub(r'<[^>]+>', '', content_raw).strip()
            # Remove excessive whitespace
            snippet = re.sub(r'\s+', ' ', snippet)[:300]

            if title:
                results.append({
                    "source": f"Bing CN ({label})",
                    "title": title,
                    "snippet": snippet,
                    "url": url_match,
                })

        return {"status": "ok", "query": query, "count": len(results), "items": results}
    except Exception as e:
        return {"status": "error", "query": query, "message": str(e), "items": []}


def main():
    output = {
        "fetch_time": __import__("datetime").datetime.now().isoformat(),
        "sources": {}
    }

    # 1) 36kr hot list
    print("Fetching 36kr hot list...", file=sys.stderr)
    output["sources"]["36kr_hot"] = fetch_36kr_hot()

    # 2) Bing CN: AI人工智能 2026年8月
    print("Searching Bing CN for 'AI人工智能 2026年8月'...", file=sys.stderr)
    output["sources"]["bing_ai_aug2026"] = search_bing_cn("AI人工智能 2026年8月", "AI人工智能 2026年8月")

    # 3) Bing CN: AI工具 最新发布 2026
    print("Searching Bing CN for 'AI工具 最新发布 2026'...", file=sys.stderr)
    output["sources"]["bing_ai_tools"] = search_bing_cn("AI工具 最新发布 2026", "AI工具 最新发布 2026")

    # Summary
    total_items = sum(len(s.get("items", [])) for s in output["sources"].values())
    output["summary"] = {
        "total_ai_items_found": total_items,
        "sources_queried": len(output["sources"]),
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
