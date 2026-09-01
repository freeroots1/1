const mod = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
(async () => {
  // 模拟 pandlFetchHandle 的 xunlei 分支：resolveProvider(allowSave)
  try {
    const r = await mod.xunleiResolve('https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1', '', { allowSave: true, pass_code: 'c233' });
    console.log('xunleiResolve OK, transfer=', JSON.stringify(r.transfer));
  } catch (e) {
    console.log('xunleiResolve ERR:', e.message);
  }
})();
