const { runXunleiPage, collectFileNodes } = (() => {
  const mod = require('/home/ubuntu/app/coolink/server/providers/resolve-other.js');
  return { runXunleiPage: mod.runXunleiPage, collectFileNodes: require('/home/ubuntu/app/coolink/server/lib/utils.js').collectFileNodes };
})();
(async () => {
  const shareId = 'VOzZsgPqtVS_wJej8qWRv9P9A1';
  const pwd = 'c233';
  const r = await runXunleiPage(shareId, pwd);
  console.log('r.ok=', r.ok, 'files=', (r.files||[]).length);
  const tree = [];
  for (const f of r.files || []) {
    if (f.kind === 'drive#folder') {
      tree.push({ name: f.name, type: 'folder', fid: f.id, children: [] });
    } else {
      tree.push({ name: f.name, type: 'file', size: f.size || 0, fid: f.id, url: '' });
    }
  }
  console.log('tree=', JSON.stringify(tree));
  const fileNodes = collectFileNodes(tree);
  console.log('fileNodes=', fileNodes.length);
  if (!fileNodes.length && !tree.length) console.log('>>> 会抛「空文件夹」');
  else console.log('>>> 不会抛');
})();
