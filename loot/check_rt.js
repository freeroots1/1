const fs = require('fs');
const crypto = require('crypto');

// 解密最新磁盘 settings.json
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'AeLnUxLVwcTVBDU5';
function settingsKeyV2() {
  const salt = fs.readFileSync('/home/ubuntu/app/coolink/data/settings.salt', 'utf8').trim();
  return crypto.scryptSync(ADMIN_PASSWORD, Buffer.from(salt, 'utf8'), 32, { N: 65536, r: 8, p: 1, maxmem: 128 * 1024 * 1024 });
}
function settingsKeyV1() {
  return crypto.scryptSync(ADMIN_PASSWORD, Buffer.from('pandel-settings-v1', 'utf8'), 32, { N: 16384, r: 8, p: 1 });
}
function decryptSettings(raw) {
  const saved = JSON.parse(raw);
  if (saved && saved.enc === true && typeof saved.data === 'string') {
    const buf = Buffer.from(saved.data, 'base64');
    if (saved.v === 2) {
      try { return decryptWith(settingsKeyV2(), buf); } catch { return decryptWith(settingsKeyV1(), buf); }
    }
    return decryptWith(settingsKeyV1(), buf);
  }
  return saved;
}
function decryptWith(key, buf) {
  const d = crypto.createDecipheriv('aes-256-gcm', key, buf.subarray(0, 12));
  d.setAuthTag(buf.subarray(12, 28));
  return JSON.parse(Buffer.concat([d.update(buf.subarray(28)), d.final()]).toString('utf8'));
}

const st = decryptSettings(fs.readFileSync('/home/ubuntu/app/coolink/data/settings.json', 'utf8'));
console.log('=== 磁盘 settings.json（最新）===');
console.log('xunleiAccessToken:', String(st.xunleiAccessToken || '').slice(0, 30), '| len:', String(st.xunleiAccessToken || '').length);
console.log('xunleiRefreshToken:', String(st.xunleiRefreshToken || '').slice(0, 30), '| len:', String(st.xunleiRefreshToken || '').length);
console.log('xunleiCreditKey:', String(st.xunleiCreditKey || '').slice(0, 25), '| len:', String(st.xunleiCreditKey || '').length);
console.log('xunleiDeviceId:', String(st.xunleiDeviceId || '').slice(0, 15));

// 磁盘文件修改时间
const stat = fs.statSync('/home/ubuntu/app/coolink/data/settings.json');
console.log('\nsettings.json mtime:', stat.mtime.toISOString());
console.log('plain.bak mtime:', fs.statSync('/home/ubuntu/app/coolink/data/settings.json.plain.bak').mtime.toISOString());

// 对比 jwt 缓存
try {
  const c = JSON.parse(fs.readFileSync('/home/ubuntu/pwand-playwright/xunlei_jwt_cache.json', 'utf8'));
  console.log('\nxunlei_jwt_cache.json jq:', String(c.jwt || '').slice(0, 25), 'ts:', c.ts, new Date(c.ts * 1000).toISOString());
} catch (e) { console.log('jwt_cache:', e.message); }
// 其他 token 文件
for (const f of ['xunlei_api_token.json', 'xunlei_auth_token.json', 'xunlei_token.json']) {
  try {
    const c = JSON.parse(fs.readFileSync('/home/ubuntu/pwand-playwright/' + f, 'utf8'));
    const t = c.token || c.access_token || '';
    console.log(f, ':', String(t).slice(0, 20), '... len:', String(t).length);
  } catch (e) { console.log(f, ':', e.message); }
}