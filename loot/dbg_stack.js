const { xunleiResolve } = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
(async () => {
  try {
    const r = await xunleiResolve('https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1', '', { pass_code: 'c233', listOnly: true });
    console.log('OK files=', r.files.length);
  } catch (e) {
    console.log('MESSAGE:', e.message);
    console.log('STACK:', e.stack);
  }
})();
