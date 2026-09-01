const mod = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
const { execFile } = require('child_process');
const py = '/home/ubuntu/pwand-playwright/venv/bin/python';
const script = '/home/ubuntu/pwand-playwright/xunlei_download.py';
execFile(py, [script, 'VOzZsgPqtVS_wJej8qWRv9P9A1', 'c233'], { timeout: 90000, maxBuffer: 4*1024*1024, cwd: '/home/ubuntu/app/coolink/server' }, (err, stdout, stderr) => {
  if (err) {
    console.log('err.code:', err.code, 'killed:', err.killed, 'signal:', err.signal);
    console.log('err.msg:', String(err.message).slice(0,300));
    console.log('stderr:', String(stderr).slice(0,300));
  } else {
    console.log('OK stdout:', String(stdout).slice(0,200));
  }
});
