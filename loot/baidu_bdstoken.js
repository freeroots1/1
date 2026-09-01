const https = require('https'), fs = require('fs'), crypto = require('crypto');
function decrypt(p){const j=JSON.parse(fs.readFileSync(p,'utf8'));
  const key=crypto.scryptSync('AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});
  const b=Buffer.from(j.data,'base64');const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
  return JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));}
const CK = decrypt('/home/ubuntu/app/coolink/data/settings.json').cookies.baidu || '';
function get(url) {
  return new Promise((res) => {
    https.get(url, {headers:{'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36','Referer':'https://pan.baidu.com/','Cookie':CK}}, (x) => {
      let b=''; x.on('data',c=>b+=c); x.on('end',()=>{ try{res(JSON.parse(b));}catch(e){res({raw:b.slice(0,150)});} });
    }).on('error', e => res({err:e.message}));
  });
}
(async () => {
  // 带 bdstoken + 完整 init 会话
  const bdstoken = 'adc3703f4d7fb4ae5435a8c8ecdea66b';
  const u1 = 'https://pan.baidu.com/share/list?web=5&app_id=250528&desc=1&showempty=0&page=1&num=20&order=time&shorturl=FDBzHv-IkPUpqM6IzqdlHA&root=1&view_mode=1&channel=chunlei&web=1&bdstoken=' + bdstoken + '&clienttype=0&logid=' + Date.now();
  const r1 = await get(u1);
  console.log('root=1 带bdstoken errno:', r1.errno, 'list:', (r1.list||[]).length);
  if (r1.errno === 0) {
    console.log('uk:', r1.uk, 'shareid:', r1.share_id, 'sekey:', (r1.sekey||'').slice(0,30));
    const sekey = r1.sekey || '';
    const dir = encodeURIComponent('/sharelink' + r1.uk + '-' + r1.share_id + '/魔兽争霸1.28至2.0版本下载');
    const u2 = 'https://pan.baidu.com/share/list?is_from_web=true&sekey=' + encodeURIComponent(sekey) + '&uk=' + r1.uk + '&shareid=' + r1.share_id + '&order=name&desc=0&showempty=0&view_mode=1&web=1&page=1&num=100&dir=' + dir + '&clienttype=0&logid=' + Date.now();
    const r2 = await get(u2);
    console.log('子目录 errno:', r2.errno, 'list:', (r2.list||[]).length, '文件:', (r2.list||[]).slice(0,3).map(f=>f.server_filename).join('|'));
  }
})();
