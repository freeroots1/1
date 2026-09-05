import socket, threading, time, sys

targets = [
    "185.143.145.146", "193.26.209.18", "193.26.209.17", "193.26.209.16",
    "193.27.80.140", "195.24.131.163", "91.224.84.79", "195.211.84.128",
    "31.43.60.67", "185.177.242.240", "193.169.80.196", "139.28.39.162",
    "93.171.129.194", "46.63.21.212", "193.107.73.198", "178.93.54.13",
    "91.240.98.105", "82.207.46.61", "194.44.109.106", "79.143.42.210",
]

ports = {
    3389: "RDP", 3390: "RDP", 3393: "RDP", 3990: "RDP", 3994: "RDP",
    49389: "RDP", 50005: "RDP", 50500: "RDP", 56391: "RDP", 65333: "RDP",
    5900: "VNC", 5901: "VNC", 5902: "VNC", 5903: "VNC", 5487: "VNC", 5488: "VNC",
    59001: "VNC", 59002: "VNC", 59003: "VNC", 59005: "VNC", 59056: "VNC", 59075: "VNC",
    22: "SSH", 2222: "SSH", 35022: "SSH", 36022: "SSH", 55476: "SSH", 65222: "SSH",
}

open_ports = []
lock = threading.Lock()

def scan(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            with lock:
                open_ports.append(f"{ip}:{port} ({ports.get(port, 'UNK')})")
    except:
        pass

threads = []
for ip in targets:
    for port in ports:
        t = threading.Thread(target=scan, args=(ip, port))
        t.start()
        threads.append(t)
        if len(threads) > 200:
            for t in threads: t.join(timeout=5)
            threads = []
        time.sleep(0.01)

for t in threads: t.join(timeout=10)

print(f"\n=== OPEN PORTS ({len(open_ports)}) ===")
for p in sorted(open_ports):
    print(p)
