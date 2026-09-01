import json, urllib.request, subprocess, re
def get_token():
    pwd = subprocess.check_output("grep ADMIN_PASSWORD /etc/systemd/system/pandl.service | sed 's/.*=//'", shell=True).decode().strip()
    req = urllib.request.Request("http://127.0.0.1:3000/api/admin/login",
        data=json.dumps({"password": pwd}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    resp = urllib.request.urlopen(req, timeout=15)
    for k, v in resp.headers.items():
        m = re.search(r"admin_token=([a-f0-9]+)", v)
        if m: return m.group(1)
    return None
at = get_token()
req = urllib.request.Request("http://127.0.0.1:3000/api/admin/settings",
    headers={"Cookie": "admin_token=" + at})
d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
promo = d.get("data", {}).get("promo", {})
print("promo keys:", list(promo.keys()))
for k, v in promo.items():
    print(f"  {k}:", json.dumps(v, ensure_ascii=False))
