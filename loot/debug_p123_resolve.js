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
  const url = 'https://4001733858.share.123pan.cn/123pan/nbicMh-c27Xh?pwd=oRch';
  console.log('调用 pan123Resolve...');
  const r = await pan123Resolve(url, cookie, {});
  console.log('返回 files 数:', r.files.length);
  r.files.slice(0, 5).forEach(f => console.log('  -', f.name, '| url:', f.url ? '✅ ' + f.url.slice(0, 60) : '❌ 空'));
  console.log('tree 结构:');
  function show(nodes, d) {
    for (const n of nodes) {
      console.log('  '.repeat(d) + (n.type || n.dir ? '📁 ' : '📄 ') + (n.name || n.file_name), '| children:', (n.children || []).length);
      if (n.children && n.children.length) show(n.children, d + 1);
    }
  }
  show(r.tree, 0);
})().catch(e => { console.log('ERR:', e.message); process.exit(1); });
