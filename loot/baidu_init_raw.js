const https = require('https'), fs = require('fs'), crypto = require('crypto');
function decrypt(p){const j=JSON.parse(fs.readFileSync(p,'utf8'));
  const key=crypto.scryptSync('AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});
  const b=Buffer.from(j.data,'base64');const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
  return JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));}
const CK = decrypt('/home/ubuntu/app/coolink/data/settings.json').cookies.baidu || '';
https.get('https://pan.baidu.com/share/init?surl=FDBzHv-IkPUpqM6IzqdlHA&pwd=85rt', {headers:{'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36','Cookie':CK}}, (x) => {
  let b=''; x.on('data',c=>b+=c); x.on('end',()=>{
    console.log('len:', b.length);
    // 找 sekey / BDCLND / yunData
    for (const kw of ['sekey','BDCLND','yunData','share_verify','sekey_data','window.yunData']) {
      const i = b.indexOf(kw);
      console.log(kw, 'at', i);
      if (i > 0) console.log('   ctx:', b.slice(i-100, i+200).replace(/\n/g,' '));
    }
    // 找 BDCLND cookie 赋值
    const m = b.match(/BDCLND[^;]{0,120}/);
    if (m) console.log('BDCLND match:', m[0].slice(0,120));
    const m2 = b.match(/sekey["':= ]+([^"'&<]{10,100})/);
    if (m2) console.log('sekey value:', m2[1].slice(0,80));
  });
}).on('error', e => console.log('ERR', e.message));
