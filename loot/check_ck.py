import json
d = json.load(open("/tmp/settings.json"))
data = d.get("data", {})
cc = data.get("cookieConfigured", {})
print("=== six providers cookie status ===")
for p in ["quark","baidu","xunlei","pan123","mcloud","uc"]:
    status = "CONFIGURED" if cc.get(p) else "NOT-CONFIGURED"
    print(f"  {p}: {status}")
