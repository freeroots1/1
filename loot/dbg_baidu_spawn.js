const { execFile } = require('child_process');
const py = '/home/ubuntu/pwand-playwright/venv/bin/python';
const script = '/home/ubuntu/pwand-playwright/baidu_page.py';
execFile(py, [script, 'FDBzHv-IkPUpqM6IzqdlHA', '85rt'], { timeout: 60000, maxBuffer: 4*1024*1024, cwd: '/home/ubuntu/app/coolink/server' }, (err, stdout, stderr) => {
  console.log('err:', err ? String(err.message).slice(0,150) : 'null');
  console.log('stdout:', String(stdout).slice(0,150));
  console.log('stderr:', String(stderr).slice(0,300));
});
