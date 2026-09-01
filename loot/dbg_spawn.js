const { execFile } = require('child_process');
const XUNLEI_PY = '/home/ubuntu/pwand-playwright/venv/bin/python';
const XUNLEI_SCRIPT = '/home/ubuntu/pwand-playwright/xunlei_page.py';
const args = [XUNLEI_SCRIPT, 'VOzZsgPqtVS_wJej8qWRv9P9A1', 'c233'];
console.log('cwd =', process.cwd());
console.log('python exists:', require('fs').existsSync(XUNLEI_PY), 'script exists:', require('fs').existsSync(XUNLEI_SCRIPT));
execFile(XUNLEI_PY, args, { timeout: 60000, maxBuffer: 4*1024*1024 }, (err, stdout, stderr) => {
  console.log('err:', err ? String(err).slice(0,150) : null);
  console.log('stdout len:', stdout.length, 'head:', stdout.slice(0,300));
  console.log('stderr:', String(stderr).slice(0,200));
  try { const j = JSON.parse(stdout.trim()); console.log('parse OK, files=', (j.files||[]).length, 'ok=', j.ok, 'status=', j.share_status); }
  catch(e){ console.log('parse FAIL:', e.message); }
});
