const mod = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
const crypto = require('crypto'), fs = require('fs');
function decrypt(p){const j=JSON.parse(fs.readFileSync(p,'utf8'));
  const key=crypto.scryptSync('AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});
  const b=Buffer.from(j.data,'base64');const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
  return JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));}
const CK = decrypt('/home/ubuntu/app/coolink/data/settings.json').cookies.mcloud || '';
(async () => {
  try {
    const r = await mod.mcloudResolve('https://yun.139.com/shareweb/#/w/i/2qiemnTF83eac', CK, { allowSave: true });
    console.log('OK files=', r.files.length, 'urls:', r.files.slice(0,3).map(f=>f.url.slice(0,50)));
  } catch (e) { console.log('ERR:', e.message); }
})();
