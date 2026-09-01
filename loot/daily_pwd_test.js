// 测试 quark/mcloud/xunlei 每日密码生成器（真实上传分享）
const crypto = require('crypto'), fs = require('fs');
const p = '/home/ubuntu/app/coolink/data/settings.json';
const key = crypto.scryptSync('AeLnUxLVwcTVBDU5', Buffer.from('pandel-settings-v1', 'utf8'), 32, { N: 16384, r: 8, p: 1 });
const sv = JSON.parse(fs.readFileSync(p, 'utf8'));
const buf = Buffer.from(sv.data, 'base64');
const d = crypto.createDecipheriv('aes-256-gcm', key, buf.subarray(0, 12));
d.setAuthTag(buf.subarray(12, 28));
const st = JSON.parse(Buffer.concat([d.update(buf.subarray(28)), d.final()]).toString('utf8'));
const { quarkRunDaily, mcloudRunDaily, xunleiRunDaily, saveTodayPassword } = require('/home/ubuntu/app/coolink/server/quark-auto.js');

(async () => {
  const jobs = [
    ['quark', quarkRunDaily],
    ['mcloud', mcloudRunDaily],
    ['xunlei', xunleiRunDaily],
  ];
  for (const [p, fn] of jobs) {
    const ck = st.cookies[p] || '';
    if (!ck) { console.log(`[${p}] ⏭ 未配置 Cookie`); continue; }
    const t0 = Date.now();
    try {
      const r = p === 'xunlei'
        ? await fn(ck, st.xunleiCaptchaToken || '', st.xunleiAccessToken || '')
        : await fn(ck);
      console.log(`[${p}] ✅ ${Date.now() - t0}ms code=${r.code} share_url=${r.share_url || '(空)'}`);
      if (r.code && r.share_url) {
        saveTodayPassword({ provider: p, status: 'ok', code: r.code, share_url: r.share_url });
        console.log(`[${p}] 已写入 daily_passwords.json`);
      }
    } catch (e) {
      console.log(`[${p}] ❌ ${Date.now() - t0}ms ${String(e.message || e).slice(0, 200)}`);
      saveTodayPassword({ provider: p, status: 'error', error: String(e.message || e).slice(0, 300) });
    }
  }
  // 汇总
  const { loadDailyPasswords } = require('/home/ubuntu/app/coolink/server/quark-auto.js');
  const all = loadDailyPasswords();
  console.log('=== daily_passwords.json 当前状态 ===');
  for (const p of ['quark', 'mcloud', 'xunlei']) {
    const s = all && all.state && all.state[p];
    console.log(`  ${p}: ${s ? s.status : '(无)'} ${s && s.code ? 'code=' + s.code : ''} ${s && s.share_url ? 'share=' + String(s.share_url).slice(0, 50) : ''}`);
  }
})();
