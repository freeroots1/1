const { runXunleiPage } = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
(async () => {
  // 1) 直接调 runXunleiPage（xunleiResolve 内部同一函数）
  const r = await runXunleiPage('VOzZsgPqtVS_wJej8qWRv9P9A1', 'c233');
  console.log('runXunleiPage: ok=', r.ok, 'status=', r.share_status, 'files=', (r.files||[]).length);
  console.log('raw files head:', JSON.stringify(r.files||[]).slice(0,200));
})();
