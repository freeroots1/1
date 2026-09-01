import urllib.request

url = "https://raw.githubusercontent.com/alist-org/alist/main/drivers/thunder_browser/util.go"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
content = urllib.request.urlopen(req, timeout=20).read().decode()
# 找 RefreshToken 完整实现
lines = content.split('\n')
printing = False
for i, line in enumerate(lines):
    if 'func (xc *XunLeiBrowserCommon) RefreshToken' in line:
        printing = True
        print(f"--- RefreshToken 实现 (L{i}) ---")
    if printing:
        print(f"{i:4d}| {line}")
    if printing and i > 0 and lines[i-1].strip().endswith('}') and '}' == line.strip():
        break