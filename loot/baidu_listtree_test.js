const { baiduListTree } = require('/home/ubuntu/app/coolink/server/providers/list-trees.js');
const { baiduRequest, BAIDU_API } = require('/home/ubuntu/app/coolink/server/lib/http.js');
(async () => {
  const surl = '1Tm_DbZhEAFsxuCWpCyz-6Q';
  const pwd = '2580';
  // ① baiduListTree 用 baiduRequest 带 cookie=''
  try {
    const r = await baiduRequest('POST',
      `${BAIDU_API}/share/wxlist?channel=weixin&version=2.2.2&clienttype=25&web=1`,
      `dir=&num=1000&order=time&page=1&pwd=${encodeURIComponent(pwd)}&root=1&shorturl=${surl}`, '');
    console.log('① wxlist dir= 带 num=1000 → ok:', r.ok !== false, '| errno:', r.errno, '| list:', (r.data && r.data.list || []).length);
  } catch (e) { console.log('① ERR:', e.message); }
  // ② baiduListTree 直接调
  try {
    const tree = await baiduListTree(surl, pwd, '', '', [], true);
    console.log('② baiduListTree → 节点:', tree.length);
    tree.slice(0, 3).forEach(n => console.log('  -', n.name, '| dir:', n.type === 'folder'));
  } catch (e) { console.log('② ERR:', e.message); }
})().catch(e => console.log('ERR:', e.message));
