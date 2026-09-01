// 六网盘 Cookie 全量验证（手册 §9.3）
const crypto = require('crypto'), fs = require('fs');
const key = crypto.scryptSync(process.env.ADMIN_PASSWORD || 'AeLnUxLVwcTVBDU5', Buffer.from('pandel-settings-v1', 'utf8'), 32, { N: 16384, r: 8, p: 1 });
const sv = JSON.parse(fs.readFileSync('data/settings.json', 'utf8'));
let st;
try {
  const b = Buffer.from(sv.data, 'base64');
  const d = crypto.createDecipheriv('aes-256-gcm', key, b.subarray(0, 12));
  d.setAuthTag(b.subarray(12, 28));
  st = JSON.parse(Buffer.concat([d.update(b.subarray(28)), d.final()]).toString('utf8'));
} catch (e) {
  // v2 回退
  const salt = fs.readFileSync('data/settings.salt', 'utf8').trim();
  const key2 = crypto.scryptSync(process.env.ADMIN_PASSWORD || 'AeLnUxLVwcTVBDU5', Buffer.from(salt, 'utf8'), 32, { N: 65536, r: 8, p: 1, maxmem: 128 * 1024 * 1024 });
  const b = Buffer.from(sv.data, 'base64');
  const d = crypto.createDecipheriv('aes-256-gcm', key2, b.subarray(0, 12));
  d.setAuthTag(b.subarray(12, 28));
  st = JSON.parse(Buffer.concat([d.update(b.subarray(28)), d.final()]).toString('utf8'));
}
console.log('=== settings.json 解密 OK ===');
console.log('cookies 字段:', Object.keys(st.cookies || {}).join(', '));
console.log('promo 字段:', Object.keys(st.promo || {}).join(', '));
console.log('pan123Account:', st.pan123Account ? '已配置(' + st.pan123Account.length + '字符)' : '未配置');
console.log('xunleiToken:', st.xunleiAccessToken ? '有' : '无', '| xunleiRefreshToken:', st.xunleiRefreshToken ? '有' : '无', '| xunleiDeviceId:', st.xunleiDeviceId ? '有' : '无');
console.log('限额: sizeCapGB=' + st.sizeCapGB, 'smallDailyLimitMB=' + st.smallDailyLimitMB, 'smallRewardMB=' + st.smallRewardMB, 'largeDailyLimit=' + st.largeDailyLimit);
// 各 cookie 摘要
for (const p of ['quark', 'uc', 'baidu', 'xunlei', 'pan123', 'mcloud']) {
  const c = (st.cookies || {})[p] || '';
  console.log(`cookie[${p}]: ${c ? c.slice(0, 30) + '... (' + c.length + '字符)' : '❌ 空'}`);
}
// 写一份供 cookie-check 用的明文（临时）
fs.writeFileSync('/tmp/settings.plain.json', JSON.stringify(st));
console.log('已导出 /tmp/settings.plain.json');