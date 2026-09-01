const fs = require('fs'), crypto = require('crypto');
const salt = Buffer.from('pandel-settings-v1', 'utf8');
const key = crypto.scryptSync(process.env.ADMIN_PASSWORD || 'pandel-default-key', salt, 32, { N: 16384, r: 8, p: 1 });
const raw = JSON.parse(fs.readFileSync('/home/ubuntu/app/coolink/data/settings.json', 'utf8'));
const buf = Buffer.from(raw.data, 'base64');
const dec = crypto.createDecipheriv('aes-256-gcm', key, buf.subarray(0, 12));
dec.setAuthTag(buf.subarray(12, 28));
const s = JSON.parse(Buffer.concat([dec.update(buf.subarray(28)), dec.final()]).toString('utf8'));
const { extractToken } = require('/home/ubuntu/app/coolink/server/providers/login-123.js');
(async () => {
  const tk = extractToken(s.cookies.pan123 || '');
  const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36';
  const H = { 'User-Agent': UA, authorization: 'Bearer ' + tk, platform: 'web', 'app-version': '3', Origin: 'https://www.123pan.com', Referer: 'https://www.123pan.com/' };
  // 进入文件夹拿 62.jpg 的完整字段
  const qs = 'shareKey=' + encodeURIComponent('nbicMh-c27Xh') + '&sharePwd=' + encodeURIComponent('oRch') + '&ParentFileId=38649716&Page=1&limit=100&orderBy=fileId&orderDirection=asc&next=0';
  const r = await fetch('https://api.123pan.cn/api/share/get?' + qs, { headers: H });
  const j = await r.json().catch(() => ({}));
  const info = (j.data && j.data.InfoList) || [];
  console.log('文件夹内文件数:', info.length);
  if (info.length) {
    const f0 = info[0];
    console.log('62.jpg 完整字段:');
    console.log(JSON.stringify(f0, null, 1).slice(0, 800));
    console.log('CreateAt:', repr(f0.CreateAt), '| UpdateAt:', repr(f0.UpdateAt));
  }
  function repr(v) { return v === undefined ? 'undefined' : JSON.stringify(v); }
})().catch(e => { console.log('ERR:', e.message); process.exit(1); });
