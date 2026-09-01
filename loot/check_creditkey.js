// 检查迅雷 creditkey（长期信任凭证）状态 + 实测登录态
const fs = require('fs'), crypto = require('crypto');

const sv = JSON.parse(fs.readFileSync('/home/ubuntu/app/coolink/data/settings.json', 'utf8'));
const salt = fs.readFileSync('/home/ubuntu/app/coolink/data/settings.salt', 'utf8').trim();
const key = crypto.scryptSync('AeLnUxLVwcTVBDU5', Buffer.from(salt, 'utf8'), 32, { N: 65536, r: 8, p: 1, maxmem: 128 * 1024 * 1024 });
const b = Buffer.from(sv.data, 'base64');
const d = crypto.createDecipheriv('aes-256-gcm', key, b.subarray(0, 12));
d.setAuthTag(b.subarray(12, 28));
const st = JSON.parse(Buffer.concat([d.update(b.subarray(28)), d.final()]).toString('utf8'));

console.log('=== creditkey 状态 ===');
console.log('存在:', !!st.xunleiCreditKey);
console.log('长度:', String(st.xunleiCreditKey || '').length);
console.log('前缀:', String(st.xunleiCreditKey || '').slice(0, 30));
console.log('');

console.log('=== 其他凭证 ===');
console.log('xunleiAccount.username:', st.xunleiAccount ? st.xunleiAccount.username : '无');
console.log('xunleiDeviceId:', String(st.xunleiDeviceId || '').slice(0, 16), 'len:', String(st.xunleiDeviceId || '').length);
console.log('AT len:', String(st.xunleiAccessToken || '').length);

// 解 AT 的 exp
try {
  const p = String(st.xunleiAccessToken).split('.')[1];
  const j = JSON.parse(Buffer.from(p, 'base64url').toString('utf8'));
  console.log('AT 剩余:', Math.round((j.exp * 1000 - Date.now()) / 60000), '分钟');
} catch (e) { console.log('exp 解析失败'); }