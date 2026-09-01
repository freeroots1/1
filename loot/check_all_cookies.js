// 临时诊断：检查 6 个网盘 cookie 有效性
const fs = require('fs');
const crypto = require('crypto');
const { checkAllCookies } = require('/home/ubuntu/app/coolink/server/cookie-check.js');

const SETTINGS_FILE = '/home/ubuntu/app/coolink/data/settings.json';

function settingsKey() {
  const pwd = process.env.ADMIN_PASSWORD || '';
  const salt = Buffer.from('pandel-settings-v1', 'utf8');
  return crypto.scryptSync(pwd || 'pandel-default-key', salt, 32, { N: 16384, r: 8, p: 1 });
}

async function main() {
  const raw = JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf8'));
  let s;
  if (raw.enc === true) {
    const buf = Buffer.from(raw.data, 'base64');
    const iv = buf.subarray(0, 12);
    const tag = buf.subarray(12, 28);
    const ct = buf.subarray(28);
    const decipher = crypto.createDecipheriv('aes-256-gcm', settingsKey(), iv);
    decipher.setAuthTag(tag);
    s = JSON.parse(Buffer.concat([decipher.update(ct), decipher.final()]).toString('utf8'));
  } else {
    s = raw;
  }
  const providers = ['quark', 'baidu', 'xunlei', 'pan123', 'mcloud', 'uc'];
  const results = await checkAllCookies(s, providers);
  for (const r of results) {
    console.log(`${r.provider || '?'}: status=${r.status} | ${(r.detail || '').slice(0, 90)}`);
  }
}

main().catch(e => { console.log('诊断失败:', e.message); process.exit(1); });
