import json, subprocess, os
js = r'''const fs=require("fs"),crypto=require("crypto");
const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
const salt=fs.readFileSync('/home/ubuntu/app/coolink/data/settings.salt','utf8').trim();
const key=crypto.scryptSync(process.env.ADMIN_PASSWORD||'AeLnUxLVwcTVBDU5',Buffer.from(salt,'utf8'),32,{N:65536,r:8,p:1,maxmem:128*1024*1024});
const b=Buffer.from(j.data,'base64');
const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
const o=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));
const ck=o.cookies&&o.cookies.baidu||'';
const parts=ck.split(';').map(s=>s.trim()).filter(s=>s);
process.stdout.write(JSON.stringify({len:ck.length, fields:parts.map(p=>p.split('=')[0]).slice(0,14), hasBDUSS:parts.some(p=>p.startsWith('BDUSS='))}));'''
env=dict(os.environ); env['ADMIN_PASSWORD']='AeLnUxLVwcTVBDU5'
r = subprocess.run(['/usr/bin/node','-e',js,'/home/ubuntu/app/coolink/data/settings.json'],capture_output=True,text=True,timeout=20,env=env)
print('stdout:', repr(r.stdout[:200]))
print('stderr:', repr(r.stderr[:100]))
