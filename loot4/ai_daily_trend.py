#!/usr/bin/env python3
"""
AI Daily Trend Report - 2026-08-14
Gather data from GitHub API, Zhihu API, 36kr API, HN API.
Compile markdown report and upload to IMA knowledge base.
"""
import json
import subprocess
import os
import sys
import time
import datetime
import tempfile
import urllib.request
import urllib.parse

TODAY = datetime.date.today().strftime("%Y-%m-%d")
WEEK_AGO = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
MONTH_AGO = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
HEADERS_GH = {"Accept": "application/vnd.github.v3+json", "User-Agent": "hermes-agent"}

def fetch_json(url, headers=None, data=None, timeout=15):
    """Fetch JSON from URL with error handling."""
    if headers is None:
        headers = {"User-Agent": UA}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw, strict=False)
    except Exception as e:
        return {"error": str(e)}

# ── Source 1: GitHub API ──
def gather_github():
    results = []
    queries = [
        f"AI+OR+LLM+OR+agent+language:python+stars:>200+pushed:>{WEEK_AGO}",
        f"AI+tool+created:>{MONTH_AGO}+stars:>50",
        "MCP+model+context+protocol+stars:>20",
        f"deepseek+OR+kimi+OR+qwen+stars:>100+pushed:>{WEEK_AGO}",
    ]
    for q in queries:
        url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=8"
        data = fetch_json(url, headers=HEADERS_GH)
        if "items" in data:
            for r in data["items"]:
                results.append({
                    "name": r["full_name"],
                    "desc": (r.get("description") or "N/A")[:120],
                    "stars": r["stargazers_count"],
                    "url": r["html_url"],
                    "pushed": r.get("pushed_at", "")[:10],
                    "created": r.get("created_at", "")[:10],
                    "lang": r.get("language", ""),
                })
        time.sleep(1.5)
    # Deduplicate by name
    seen = set()
    deduped = []
    for r in results:
        if r["name"] not in seen:
            seen.add(r["name"])
            deduped.append(r)
    return deduped

# ── Source 2: Zhihu Hot ──
def gather_zhihu():
    url = "https://api.zhihu.com/topstory/hot-lists/total?limit=50"
    data = fetch_json(url)
    ai_keywords = ["AI", "人工智能", "大模型", "GPT", "Claude", "Gemini", "DeepSeek",
                   "Kimi", "智谱", "算力", "智能", "机器人", "OpenAI", "Anthropic",
                   "Llama", "LLM", "豆包", "通义", "文心", "Model", "Agent"]
    results = []
    for item in data.get("data", []):
        title = item.get("target", {}).get("title", "")
        if any(kw.lower() in title.lower() for kw in ai_keywords):
            results.append({
                "title": title,
                "heat": item.get("detail_text", ""),
                "url": item.get("target", {}).get("url", ""),
                "excerpt": (item.get("target", {}).get("excerpt") or "")[:100],
            })
    return results

# ── Source 3: 36kr Hot ──
def gather_36kr():
    url = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
    body = json.dumps({"partner_id": "wap", "param": {"siteId": 1, "platformId": 2}}).encode()
    data = fetch_json(url, data=body, headers={"User-Agent": UA, "Content-Type": "application/json"})
    ai_keywords = ["AI", "人工智能", "大模型", "GPT", "Claude", "DeepSeek", "Kimi",
                   "智谱", "算力", "智能", "机器人", "OpenAI", "Anthropic", "Google",
                   "英伟达", "芯片", "Llama", "LLM", "Agent", "豆包", "通义"]
    results = []
    for item in data.get("data", {}).get("hotRankList", []):
        mat = item.get("templateMaterial", {})
        title = mat.get("widgetTitle", "")
        if any(kw.lower() in title.lower() for kw in ai_keywords):
            item_id = mat.get("itemId", "")
            results.append({
                "title": title,
                "url": f"https://36kr.com/p/{item_id}" if item_id else "",
                "heat": item.get("templateMaterial", {}).get("statRead", ""),
            })
    return results

# ── Source 4: Hacker News ──
def gather_hn():
    ai_keywords = ["ai", "llm", "gpt", "claude", "gemini", "machine learning",
                   "deep learning", "neural", "transformer", "agent", "openai",
                   "anthropic", "model", "inference", "training", "mcp"]
    try:
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        data = fetch_json(url)
        if isinstance(data, list):
            ids = data[:30]
        else:
            return []
    except:
        return []
    
    results = []
    for sid in ids:
        item_data = fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
        title = item_data.get("title", "")
        if any(kw in title.lower() for kw in ai_keywords):
            results.append({
                "title": title,
                "url": f"https://news.ycombinator.com/item?id={sid}",
                "score": item_data.get("score", 0),
                "comments": item_data.get("descendants", 0),
            })
        time.sleep(0.3)
    return results

# ── Compile Report ──
def compile_report(github, zhihu, kr36, hn):
    lines = []
    lines.append(f"# AI趋势日报 {TODAY}\n")
    lines.append(f"> 数据来源：GitHub API、知乎热榜、36kr 热榜、Hacker News\n")

    # Section 1: Hot topics
    lines.append("\n## 一、今日AI热点\n")
    
    # Pick top items from each source
    hot_items = []
    # HN top items by score
    for h in sorted(hn, key=lambda x: x.get("score", 0), reverse=True)[:3]:
        hot_items.append(f"- **[{h['title']}]({h['url']})** — Hacker News {h['score']} points, {h['comments']} comments")
    # 36kr top items
    for k in kr36[:3]:
        hot_items.append(f"- **[{k['title']}]({k['url']})** — 36kr 热榜")
    # Zhihu top items
    for z in zhihu[:2]:
        url_str = z['url'] if z['url'] else '#'
        hot_items.append(f"- **[{z['title']}]({url_str})** — 知乎热榜 {z['heat']}")
    
    if not hot_items:
        hot_items.append("- 今日暂无显著AI热点，建议关注 GitHub Trending 和行业媒体。")
    
    lines.extend(hot_items[:6])

    # Section 2: Tool recommendations
    lines.append("\n## 二、工具推荐\n")
    
    # Prefer new repos, high velocity
    new_repos = [r for r in github if r["created"] >= MONTH_AGO]
    popular_repos = [r for r in github if r["stars"] >= 500]
    
    tool_picks = []
    # Pick 2-3 interesting tools
    seen_names = set()
    for r in new_repos[:2]:
        if r["name"] not in seen_names:
            seen_names.add(r["name"])
            tool_picks.append(r)
    for r in popular_repos[:3]:
        if r["name"] not in seen_names and len(tool_picks) < 3:
            seen_names.add(r["name"])
            tool_picks.append(r)
    # Fill up if needed
    for r in github[:5]:
        if r["name"] not in seen_names and len(tool_picks) < 3:
            seen_names.add(r["name"])
            tool_picks.append(r)

    for i, r in enumerate(tool_picks[:3], 1):
        lines.append(f"### {i}. {r['name']}")
        lines.append(f"- **简介**：{r['desc']}")
        lines.append(f"- **Stars**：{r['stars']} | 语言：{r['lang']} | 最近更新：{r['pushed']}")
        lines.append(f"- **适用场景**：AI 开发、研究、工具集成")
        lines.append(f"- **链接**：{r['url']}")
        lines.append("")

    # Section 3: Learning resources
    lines.append("## 三、学习资源推荐\n")
    
    lines.append("### 1. GitHub Trending AI 项目速览")
    lines.append("- **内容**：每日精选 GitHub 上最热门的 AI/LLM 开源项目，涵盖工具、框架、应用")
    lines.append("- **适合**：开发者、AI 爱好者、技术管理者")
    lines.append(f"- **链接**：[GitHub Trending](https://github.com/trending?since=daily)")
    lines.append("")
    
    lines.append("### 2. Hacker News AI 讨论")
    lines.append("- **内容**：全球技术社区对 AI 最新进展的深度讨论和评论")
    lines.append("- **适合**：关注前沿技术趋势的开发者和研究者")
    lines.append("- **链接**：[Hacker News](https://news.ycombinator.com/)")
    lines.append("")
    
    lines.append("### 3. 36kr AI 频道")
    lines.append("- **内容**：中文 AI 产业新闻、融资动态、产品发布")
    lines.append("- **适合**：关注国内 AI 产业动态的从业者")
    lines.append("- **链接**：[36kr AI 频道](https://36kr.com/information/AI/)")
    lines.append("")

    # Section 4: Practical advice
    lines.append("## 四、实操建议\n")
    lines.append("### 这周可以学什么")
    
    # Extract trending languages/topics from GitHub
    langs = {}
    for r in github[:20]:
        l = r.get("lang", "")
        if l:
            langs[l] = langs.get(l, 0) + 1
    top_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:3]
    lang_str = "、".join([l[0] for l in top_langs]) if top_langs else "Python、TypeScript"
    
    lines.append(f"- 关注本周 GitHub 热门语言趋势：**{lang_str}**")
    if new_repos:
        lines.append(f"- 试试新工具 **{new_repos[0]['name']}**：{new_repos[0]['desc'][:60]}")
    lines.append("- 浏览 Hacker News AI 讨论，了解海外社区关注点")
    lines.append("")
    lines.append("### 怎么用到工作中")
    lines.append("- 如果你是开发者：关注 AI Agent 框架和 MCP 生态，提升自动化工作流效率")
    lines.append("- 如果你是团队负责人：评估新工具对团队生产力的影响，考虑内部试用")
    lines.append("- 如果你关注趋势：对比中英文社区讨论差异，形成自己的判断框架")
    lines.append("")

    return "\n".join(lines)

# ── IMA Upload ──
def upload_to_ima(content):
    SKILL_DIR = "/home/ubuntu/.hermes/skills/ima-skill"
    IMA_API = f"{SKILL_DIR}/ima_api.cjs"
    COS_SCRIPT = f"{SKILL_DIR}/knowledge-base/scripts/cos-upload.cjs"

    client_id = open(os.path.expanduser("~/.config/ima/client_id")).read().strip()
    api_key = open(os.path.expanduser("~/.config/ima/api_key")).read().strip()
    OPTS = json.dumps({"clientId": client_id, "apiKey": api_key})

    def call_ima(endpoint, body):
        result = subprocess.run(
            ["node", IMA_API, endpoint, body, OPTS],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {"error": result.stderr[:300]}
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": f"JSON parse failed: {result.stdout[:200]}"}

    file_name = f"AI趋势日报_{TODAY}.md"
    
    # Step 1: Find KB by name
    search = call_ima("openapi/wiki/v1/search_knowledge_base",
                      json.dumps({"query": "AI趋势", "cursor": "", "limit": 10}))
    if not search or search.get("code") != 0:
        print(f"[error] KB search failed: {search}")
        return False
    
    kb_id = None
    for kb in search.get("data", {}).get("info_list", []):
        if "AI趋势" in kb.get("kb_name", ""):
            kb_id = kb.get("kb_id")
            break
    
    if not kb_id:
        print("[error] Knowledge base 'AI趋势' not found")
        return False
    
    print(f"[info] Found KB: {kb_id}")

    # Step 2: Write content to temp file
    tmp_dir = tempfile.mkdtemp(prefix="ima_daily_")
    tmp_path = os.path.join(tmp_dir, file_name)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    file_size = len(content.encode("utf-8"))
    
    try:
        # Step 3: create_media
        resp = call_ima("openapi/wiki/v1/create_media", json.dumps({
            "knowledge_base_id": kb_id,
            "file_name": file_name,
            "file_size": file_size,
            "file_ext": "md",
            "content_type": "text/markdown"
        }))
        if resp.get("code") != 0:
            print(f"[error] create_media failed: {resp}")
            return False

        data = resp["data"]
        media_id = data["media_id"]
        cred = data["cos_credential"]
        print(f"[info] media_id: {media_id}")

        # Step 4: COS upload
        cos_result = subprocess.run([
            "node", COS_SCRIPT,
            "--file", tmp_path,
            "--secret-id", cred["secret_id"],
            "--secret-key", cred["secret_key"],
            "--token", cred["token"],
            "--bucket", cred["bucket_name"],
            "--region", cred["region"],
            "--cos-key", cred["cos_key"],
            "--content-type", "text/markdown",
            "--start-time", cred["start_time"],
            "--expired-time", cred["expired_time"],
            "--timeout", "300000"
        ], capture_output=True, text=True, timeout=60)

        if cos_result.returncode != 0:
            print(f"[error] COS upload failed: {cos_result.stderr[:200]}")
            return False
        print("[info] COS upload OK")

        # Step 5: add_knowledge
        add_resp = call_ima("openapi/wiki/v1/add_knowledge", json.dumps({
            "media_type": 7,
            "media_id": media_id,
            "title": file_name,
            "knowledge_base_id": kb_id,
            "file_info": {
                "cos_key": cred["cos_key"],
                "file_size": file_size,
                "file_name": file_name
            }
        }))
        if add_resp.get("code") != 0:
            print(f"[error] add_knowledge failed: {add_resp}")
            return False

        print(f"[success] {file_name} uploaded to IMA knowledge base")
        return True

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)


# ── Main ──
if __name__ == "__main__":
    print(f"[{TODAY}] Gathering AI trend data...")
    
    print("[1/4] GitHub API...")
    github = gather_github()
    print(f"  -> {len(github)} repos found")
    
    print("[2/4] Zhihu hot list...")
    zhihu = gather_zhihu()
    print(f"  -> {len(zhihu)} AI topics found")
    
    print("[3/4] 36kr hot list...")
    kr36 = gather_36kr()
    print(f"  -> {len(kr36)} AI topics found")
    
    print("[4/4] Hacker News...")
    hn = gather_hn()
    print(f"  -> {len(hn)} AI stories found")
    
    print("\nCompiling report...")
    report = compile_report(github, zhihu, kr36, hn)
    
    # Print report for cron delivery
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    
    # Upload to IMA
    print("\nUploading to IMA...")
    ok = upload_to_ima(report)
    if ok:
        print("Upload complete.")
    else:
        print("Upload failed — report printed above.")
