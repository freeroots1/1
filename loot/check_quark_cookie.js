const fs=require('fs'),crypto=require('crypto');
function decrypt(p){const j=JSON.parse(fs.readFileSync(p,'utf8'));
 const key=crypto.scryptSync('AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});
 const b=Buffer.from(j.data,'base64');const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
 return JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));}
for(const p of process.argv.slice(2)){
  try{
    const o=decrypt(p);
    const c=o.cookies||{};
    console.log(p);
    for(const k of Object.keys(c)){
      const v=c[k]||'';
      const bad = v.startsWith('TEST_') ? ' ⚠️已被测试值覆盖!' : '';
      console.log('  '+k+' => '+(v?('OK '+v.length+'字 '+(v.startsWith('TEST_')?'[TEST!!]':'[真实]')):'(EMPTY)')+bad);
    }
  }catch(e){console.log(p,'ERR',e.message);}
}
