import urllib.request

files = {
    "driver.go": "https://raw.githubusercontent.com/AlistGo/alist/main/drivers/thunder/driver.go",
    "util.go": "https://raw.githubusercontent.com/AlistGo/alist/main/drivers/thunder/util.go",
    "meta.go": "https://raw.githubusercontent.com/AlistGo/alist/main/drivers/thunder/meta.go",
}
for name, url in files.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, timeout=20).read().decode()
        open(f'/tmp/alist_{name}', 'w').write(content)
        print(f"=== {name} ({len(content)} chars) ===")
    except Exception as e:
        print(name, "ERR:", e)