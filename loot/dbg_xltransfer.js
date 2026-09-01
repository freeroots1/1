const mod = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
const { execFile } = require('child_process');
// 直接调 xunleiTransfer
mod.xunleiTransfer('VOzZsgPqtVS_wJej8qWRv9P9A1', 'c233').then(r => {
  console.log('OK:', JSON.stringify(r));
}).catch(e => {
  console.log('ERR type:', typeof e, 'msg:', e.message);
  console.log('ERR full:', JSON.stringify(e));
});
