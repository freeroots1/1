import json, subprocess, os, base64, time
js = r'''const fs=require("fs"),crypto=require("crypto");
const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
const salt=fs.readFileSync('/home/ubuntu/app/coolink/data/settings.salt','utf8').trim();
const key=crypto.scryptSync(process.env.ADMIN_PASSWORD||'AeLnUxLVwcTVBDU5',Buffer.from(salt,'utf8'),32,{N:65536,r:8,p:1,maxmem:128*1024*1024});
const b=Buffer.from(j.data,'base64');
const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
const o=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));
const at=o.xunleiAccessToken||'';
let exp=0; try { exp=JSON.parse(Buffer.from(at.split('.')[1],'base64url').toString()).exp*1000; } catch{}
process.stdout.write(JSON.stringify({kind:o.xunleiTokenKind, at_len:at.length, rt_len:(o.xunleiRefreshToken||'').length, at_exp: exp? new Date(exp).toISOString():'none'}));'''
env=dict(os.environ); env['ADMIN_PASSWORD']='AeLnUxLVwcTVBDU5'
r = subprocess.run(['/usr/bin/node','-e',js,'/home/ubuntu/app/coolink/data/settings.json'],capture_output=True,text=True,timeout=20,env=env)
print('settings:', r.stdout.strip())
