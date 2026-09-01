const { execFile } = require('child_process');
const py = '/home/ubuntu/pwand-playwright/venv/bin/python';
const script = '/home/ubuntu/pwand-playwright/xunlei_download.py';
execFile(py, [script, 'VOzZsgPqtVS_wJej8qWRv9P9A1', 'c233'], { timeout: 90000, maxBuffer: 4*1024*1024 }, (err, stdout, stderr) => {
  console.log('err:', err ? String(err).slice(0,200) : 'null');
  console.log('stdout:', String(stdout).slice(0,300));
  console.log('stderr:', String(stderr).slice(0,200));
});
