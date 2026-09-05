import requests, urllib3, re, sys, threading, queue, time
urllib3.disable_warnings()

targets = [
    ("194.44.109.106", 32980),
    ("193.26.209.18", 7575),
    ("193.26.209.17", 4563),
    ("91.224.84.79", 880),
    ("139.28.39.162", 4406),
    ("185.237.106.167", 8081),
    ("185.143.145.146", 5901),
    ("193.169.80.196", 54333),
    ("31.43.60.67", 2096),
    ("193.27.80.140", 80),
    ("193.26.209.16", 80),
    ("185.177.242.240", 443),
    ("195.211.84.128", 1331),
    ("185.237.106.167", 8088),
    ("31.43.60.67", 28006),
    ("93.171.129.194", 82),
    ("46.63.21.212", 80),
    ("193.107.73.198", 7575),
    ("178.93.54.13", 43267),
    ("91.240.98.105", 7575),
]

patterns = [
    r'\.rdp', r'\.vnc', r'vncpass', r'connections\.xml', r'servers\.xml',
    r'krdc', r'remmina', r'mRemoteNG', r'RoyalTS', r'freerdp', r'xfreerdp',
    r'mstsc', r'vncviewer', r'-passwd', r'id_rsa', r'id_ed25519', r'id_ecdsa',
    r'\.pem', r'\.key', r'private_key', r'authorized_keys', r'\.bash_history',
    r'\.ssh/', r'known_hosts', r'config', r'credentials', r'password',
    r'passwd', r'secret', r'token', r'api_key', r'apikey',
]

found = []
lock = threading.Lock()

def scan_target(ip, port):
    try:
        url = f"http://{ip}:{port}/"
        r = requests.get(url, timeout=8, verify=False)
        if r.status_code == 200:
            content = r.text
            # Find all href links
            links = re.findall(r'href="([^"]*)"', content)
            for link in links:
                link_lower = link.lower()
                for pat in patterns:
                    if re.search(pat, link_lower):
                        with lock:
                            found.append(f"{ip}:{port} -> {link} (matched: {pat})")
                        break
    except Exception as e:
        pass

threads = []
for ip, port in targets:
    t = threading.Thread(target=scan_target, args=(ip, port))
    t.start()
    threads.append(t)
    time.sleep(0.1)

for t in threads:
    t.join(timeout=15)

for f in found:
    print(f)
