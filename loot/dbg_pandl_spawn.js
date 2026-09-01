const { execFile } = require('child_process');
// 模拟 pandl 服务环境：不设 cwd（默认继承）
const py = '/home/ubuntu/pwand-playwright/venv/bin/python';
const script = '/home/ubuntu/pwand-playwright/xunlei_download.py';
console.log('cwd =', process.cwd());
execFile(py, [script, 'VOzZsgPqtVS_wJej8qWRv9P9A1', 'c233'], { timeout: 90000, maxBuffer: 4*1024*1024 }, (err, stdout, stderr) => {
  console.log('err:', err ? JSON.stringify({code: err.code, msg: String(err.message).slice(0,120), killed: err.killed, signal: err.signal}) : 'null');
  console.log('stdout:', String(stdout).slice(0,150));
  console.log('stderr:', String(stderr).slice(0,150));
});
