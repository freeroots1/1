const { xunleiResolve } = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
(async () => {
  for (let i = 1; i <= 5; i++) {
    try {
      const r = await xunleiResolve('https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1', '', { pass_code: 'c233', listOnly: true });
      console.log(i + ': OK tree=' + r.tree.length + ' files=' + r.files.length + ' ' + (r.tree[0]?r.tree[0].name:''));
    } catch (e) { console.log(i + ': ERR ' + e.message); }
    await new Promise(res=>setTimeout(res,1500));
  }
})();
