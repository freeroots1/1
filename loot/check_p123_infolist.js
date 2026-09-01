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
  const qs = 'shareKey=' + encodeURIComponent('nbicMh-Z27Xh') + '&sharePwd=' + encodeURIComponent('9Aut') + '&ParentFileId=0&Page=1&limit=100&orderBy=fileId&orderDirection=asc&next=0';
  const r = await fetch('https://api.123pan.cn/api/share/get?' + qs, { headers: H });
  const j = await r.json().catch(() => ({}));
  const info = (j.data && j.data.InfoList) || [];
  console.log('InfoList 数:', info.length);
  if (info.length) {
    console.log('InfoList[0] 全部字段:', Object.keys(info[0]).join(', '));
    console.log('InfoList[0] 值:', JSON.stringify(info[0]).slice(0, 400));
  }
  // 直接用 InfoList 里的字段构造 download/info 请求
  if (info.length) {
    const f = info[0];
    console.log('\n=== 用 InfoList 字段试 download/info ===');
    const body = { ShareKey: 'nbicMh-Z27Xh', FileId: f.FileId || f.fileId, SharePwd: '9Aut', S3KeyFlag: f.S3KeyFlag || '', Size: f.Size || f.size || 0, Etag: f.Etag || '' };
    console.log('body:', JSON.stringify(body));
    const r2 = await fetch('https://api.123pan.cn/api/v2/share/download/info', { method: 'POST', headers: { ...H, 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j2 = await r2.json().catch(() => ({}));
    console.log('download/info → HTTP', r2.status, '| code:', j2.code, '|', j2.message || '');
    if (j2.code === 0 && j2.data) {
      console.log('✅ 直链:', JSON.stringify(j2.data).slice(0, 200));
    }
  }
})().catch(e => console.log('ERR:', e.message));
