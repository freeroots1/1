/* 百度新 API 完整链路验证：share/init 拿 BDCLND → share/list root=1 → 子目录 */
const https = require('https'), fs = require('fs'), crypto = require('crypto');
function decrypt(p){const j=JSON.parse(fs.readFileSync(p,'utf8'));
  const key=crypto.scryptSync('AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});
  const b=Buffer.from(j.data,'base64');const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
  return JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));}
const CK = decrypt(process.argv[2]).cookies.baidu || '';

function req(method, url, cookie, extraHeaders = {}) {
  return new Promise((res) => {
    const h = Object.assign({'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36','Referer':'https://pan.baidu.com/'}, extraHeaders);
    if (cookie) h.Cookie = cookie;
    const r = (method === 'GET') ? https.get(url, {headers:h}, cb) : null;
    function cb(x) {
      let b = '';
      x.on('data', c => b += c);
      x.on('end', () => {
        let sc = [];
        try { sc = (x.headers['set-cookie'] || []).map(c => c.split(';')[0]); } catch {}
        try { res({status:x.statusCode, body:JSON.parse(b), setCookie:sc}); }
        catch { res({status:x.statusCode, raw:b.slice(0,300), setCookie:sc}); }
      });
    }
    if (method === 'GET') r.on('error', e => res({err:e.message}));
  });
}
(async () => {
  const surl = 'FDBzHv-IkPUpqM6IzqdlHA', pwd = '85rt';
  // 1) share/init 拿会话 cookie（BDCLND）
  const init = await req('GET', `https://pan.baidu.com/share/init?surl=${surl}&pwd=${pwd}`, CK);
  console.log('init status:', init.status, 'set-cookie 数:', (init.setCookie||[]).length);
  const bdclnd = (init.setCookie||[]).find(c => c.startsWith('BDCLND=')) || '';
  console.log('BDCLND:', bdclnd.slice(0, 40));
  const sessCookie = CK + '; ' + (init.setCookie||[]).join('; ');
  // 2) share/list root=1
  const u1 = `https://pan.baidu.com/share/list?web=5&app_id=250528&desc=1&showempty=0&page=1&num=20&order=time&shorturl=${surl}&root=1&view_mode=1&channel=chunlei&web=1&bdstoken=&clienttype=0&logid=${Date.now()}`;
  const r1 = await req('GET', u1, sessCookie);
  console.log('\nroot=1 errno:', r1.body && r1.body.errno);
  if (r1.body && r1.body.errno === 0) {
    const uk = r1.body.uk, shareid = r1.body.share_id;
    console.log('uk:', uk, 'shareid:', shareid, '顶层:', (r1.body.list||[]).length, '首个:', ((r1.body.list||[])[0]||{}).server_filename);
    // 3) 子目录
    const dir = encodeURIComponent('/sharelink' + uk + '-' + shareid + '/魔兽争霸1.28至2.0版本下载');
    const u2 = `https://pan.baidu.com/share/list?is_from_web=true&sekey=${encodeURIComponent(bdclnd.replace('BDCLND=',''))}&uk=${uk}&shareid=${shareid}&order=name&desc=0&showempty=0&view_mode=1&web=1&page=1&num=100&dir=${dir}&clienttype=0&logid=${Date.now()}`;
    const r2 = await req('GET', u2, sessCookie);
    console.log('子目录 errno:', r2.body && r2.body.errno, 'list:', (r2.body.list||[]).length);
    console.log('子目录文件:', (r2.body.list||[]).slice(0,4).map(f => f.server_filename).join(' | '));
  } else {
    console.log('errno:', r1.body && r1.body.errno, r1.raw || '');
  }
})();
