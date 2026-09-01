const { xunleiResolve } = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
(async () => {
  try {
    const r = await xunleiResolve('https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1', '', { allowSave: true, pass_code: 'c233', listOnly: false });
    console.log('OK transfer=', JSON.stringify(r.transfer));
  } catch (e) {
    console.log('ERR:', e.message);
  }
})();
