import json, subprocess, os
js = r'''const fs=require("fs"),crypto=require("crypto");
const p='/home/ubuntu/app/coolink/data/settings.json';
const salt=fs.readFileSync('/home/ubuntu/app/coolink/data/settings.salt','utf8').trim();
const j=JSON.parse(fs.readFileSync(p,'utf8'));
const key=crypto.scryptSync(process.env.ADMIN_PASSWORD||'AeLnUxLVwcTVBDU5',Buffer.from(salt,'utf8'),32,{N:65536,r:8,p:1,maxmem:128*1024*1024});
const b=Buffer.from(j.data,'base64');
const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
const o=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));
process.stdout.write(JSON.stringify({acct:!!o.xunleiAccount, ck:!!o.xunleiCreditKey, jwt:(o.xunleiAccessToken||'').length, rt:(o.xunleiRefreshToken||'').length, did:(o.xunleiDeviceId||'').length}));'''
env=dict(os.environ); env['ADMIN_PASSWORD']='AeLnUxLVwcTVBDU5'
r = subprocess.run(['/usr/bin/node','-e',js],capture_output=True,text=True,timeout=20,env=env)
print('stdout:', r.stdout.strip() or '(empty)')
print('stderr:', r.stderr.strip()[:200] or '(none)')
