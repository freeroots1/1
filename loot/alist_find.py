import urllib.request, json

# AList 仓库找 thunder/xunlei 驱动
for path in ["drivers/thunder", "drivers/xunlei"]:
    url = f"https://api.github.com/repos/alist-org/alist/contents/{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        items = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
        print(f"=== {path} ===")
        for it in items:
            print(" ", it["name"], it["download_url"])
    except Exception as e:
        print(path, "ERR:", e)