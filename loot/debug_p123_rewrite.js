const fs = require('fs'), crypto = require('crypto');
const salt = Buffer.from('pandel-settings-v1', 'utf8');
const key = crypto.scryptSync(process.env.ADMIN_PASSWORD || 'pandel-default-key', salt, 32, { N: 16384, r: 8, p: 1 });
const raw = JSON.parse(fs.readFileSync('/home/ubuntu/app/coolink/data/settings.json', 'utf8'));
const buf = Buffer.from(raw.data, 'base64');
const dec = crypto.createDecipheriv('aes-256-gcm', key, buf.subarray(0, 12));
dec.setAuthTag(buf.subarray(12, 28));
const s = JSON.parse(Buffer.concat([dec.update(buf.subarray(28)), dec.final()]).toString('utf8'));
const { pan123Resolve } = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
const { extractToken } = require('/home/ubuntu/app/coolink/server/providers/login-123.js');
(async () => {
  const tk = extractToken(s.cookies.pan123 || '');
  const cookie = 'token=' + tk;
  // 模拟前端重写 URL + pass_code
  const url = 'https://www.123pan.cn/s/nbicMh-c27Xh';
  console.log('传 cookie:', cookie ? 'token=***' : '无', '| pass_code: oRch');
  try {
    const r = await pan123Resolve(url, cookie, { pass_code: 'oRch' });
    console.log('✅ 成功! files:', r.files.length);
  } catch (e) {
    console.log('❌ 失败:', e.message);
  }
})().catch(e => { console.log('ERR:', e.message); process.exit(1); });
