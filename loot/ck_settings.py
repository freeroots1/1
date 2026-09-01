import json, subprocess, os
js = r'''const fs=require("fs"),crypto=require("crypto");
const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
const key=crypto.scryptSync(process.env.ADMIN_PASSWORD||"AeLnUxLVwcTVBDU5",Buffer.from("pandel-settings-v1","utf8"),32,{N:16384,r:8,p:1});
const b=Buffer.from(j.data,"base64");
const d=crypto.createDecipheriv("aes-256-gcm",key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
const o=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString("utf8"));
process.stdout.write(JSON.stringify({acct:!!o.xunleiAccount, ck:!!o.xunleiCreditKey, jwt:(o.xunleiAccessToken||"").length, rt:(o.xunleiRefreshToken||"").length, did:(o.xunleiDeviceId||"").length}));'''
env=dict(os.environ); env['ADMIN_PASSWORD']='AeLnUxLVwcTVBDU5'
r = subprocess.run(['/usr/bin/node','-e',js,'/home/ubuntu/app/coolink/data/settings.json'],capture_output=True,text=True,timeout=15,env=env)
print('stdout:', repr(r.stdout))
print('stderr:', repr(r.stderr))
print('rc:', r.returncode)
