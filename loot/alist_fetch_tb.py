import urllib.request

files = {
    "tb_driver.go": "https://raw.githubusercontent.com/alist-org/alist/main/drivers/thunder_browser/driver.go",
    "tb_meta.go": "https://raw.githubusercontent.com/alist-org/alist/main/drivers/thunder_browser/meta.go",
    "tb_util.go": "https://raw.githubusercontent.com/alist-org/alist/main/drivers/thunder_browser/util.go",
}
for name, url in files.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, timeout=20).read().decode()
        open(f'/tmp/alist_{name}', 'w').write(content)
        print(f"=== {name} ({len(content)} chars) ===")
        for line in content.split('\n'):
            if any(k in line for k in ['client_id', 'ClientID', 'Xp6', 'Xqp0', 'Refresh', 'refresh', 'LocalStorage', 'localStorage', 'profile', 'Profile', 'Cookie']):
                print("  ", line.strip()[:150])
    except Exception as e:
        print(name, "ERR:", e)