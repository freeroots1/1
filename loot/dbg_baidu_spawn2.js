const { execFile } = require('child_process');
const py = '/home/ubuntu/pwand-playwright/venv/bin/python';
const script = '/home/ubuntu/pwand-playwright/baidu_page.py';
// 复刻 resolve-other.js 的调用（surl=1FDBzHv-...）
execFile(py, [script, '1FDBzHv-IkPUpqM6IzqdlHA', '85rt'], { timeout: 60000, maxBuffer: 4*1024*1024 }, (err, stdout, stderr) => {
  console.log('err:', err ? String(err.message).slice(0,200) : 'null');
  console.log('stdout:', String(stdout).slice(0,250));
  console.log('stderr:', String(stderr).slice(0,300));
});
