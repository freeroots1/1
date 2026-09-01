// 解密 settings.json 并打印各网盘 cookie 状态（脱敏）
const fs = require('fs');
const crypto = require('crypto');
const pwd = process.env.ADMIN_PASSWORD || 'AeLnUxLVwcTVBDU5';
const salt = Buffer.from('pandel-settings-v1', 'utf8');
const key = crypto.scryptSync(pwd, salt, 32, { N: 16384, r: 8, p: 1 });
const raw = JSON.parse(fs.readFileSync('/home/ubuntu/app/coolink/data/settings.json', 'utf8'));
if (raw.enc === true) {
  const buf = Buffer.from(raw.data, 'base64');
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, buf.subarray(0, 12));
  decipher.setAuthTag(buf.subarray(12, 28));
  const s = JSON.parse(Buffer.concat([decipher.update(buf.subarray(28)), decipher.final()]).toString('utf8'));
  const c = s.cookies || {};
  for (const k of Object.keys(c)) {
    const v = c[k] || '';
    console.log(`cookies.${k}: ${v.length > 0 ? 'len=' + v.length + ' head=' + v.slice(0, 40).replace(/\n/g, ' ') : 'EMPTY'}`);
  }
  console.log('pan123Account:', s.pan123Account ? 'set(len=' + String(s.pan123Account).length + ')' : 'EMPTY');
  console.log('xunleiAccessToken:', s.xunleiAccessToken ? 'set(len=' + String(s.xunleiAccessToken).length + ')' : 'EMPTY');
} else {
  console.log('settings.json 是明文格式，enc 标记缺失');
  console.log('cookies:', JSON.stringify(raw.cookies ? Object.keys(raw.cookies) : 'none'));
}
