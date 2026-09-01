import urllib.request

url = "https://raw.githubusercontent.com/AlistGo/alist/main/drivers/thunder/driver.go"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
content = urllib.request.urlopen(req, timeout=20).read().decode()
open('/tmp/alist_driver_full.go', 'w').write(content)
print("saved", len(content))
# 找 Login 函数和 creditkey 相关逻辑
lines = content.split('\n')
capture = False
for i, line in enumerate(lines):
    if 'func (x *Thunder) Login' in line or 'creditkey' in line.lower() or 'CreditKey' in line or 'review' in line.lower():
        # 打印前后上下文
        start = max(0, i-2)
        end = min(len(lines), i+8)
        for j in range(start, end):
            print(f"{j:4d}| {lines[j]}")
        print("---")