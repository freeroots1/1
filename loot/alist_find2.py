import urllib.request, json

# 找 AList thunder 驱动里 RefreshToken 函数的实现文件
for path in ["drivers/thunder", "drivers/thunder/other", "drivers/xunlei"]:
    url = f"https://api.github.com/repos/alist-org/alist/contents/{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        items = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
        print(f"=== {path} ===")
        for it in items:
            print(" ", it["name"])
    except Exception as e:
        print(path, "ERR:", e)

# 也搜一下 common 里的 xunlei 相关
for path in ["drivers/thunder"]:
    url = f"https://api.github.com/repos/alist-org/alist/git/trees/main?recursive=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        tree = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        for item in tree["tree"]:
            p = item["path"]
            if "thunder" in p.lower() and p.endswith(".go") and "test" not in p:
                print("GO:", p)
    except Exception as e:
        print("TREE ERR:", e)