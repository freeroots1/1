const { baiduListTree } = require('/home/ubuntu/app/coolink/server/providers/list-trees.js');
const { baiduRequest, BAIDU_API } = require('/home/ubuntu/app/coolink/server/lib/http.js');
(async () => {
  const surl = '1Tm_DbZhEAFsxuCWpCyz-6Q';
  const pwd = '2580';
  // 直接看 wxlist 返回的 isdir 类型
  const r = await baiduRequest('POST', `${BAIDU_API}/share/wxlist?channel=weixin&version=2.2.2&clienttype=25&web=1`,
    `shorturl=${surl}&dir=%2F&root=1&pwd=${pwd}&page=1&num=1000&order=time`, '');
  const list = r.data.list || [];
  console.log('wxlist list 数:', list.length);
  list.forEach(f => console.log('  -', f.server_filename, '| isdir:', JSON.stringify(f.isdir), '| type:', typeof f.isdir));
  // baiduListTree 返回
  const tree = await baiduListTree(surl, pwd, '', '', [], false);
  console.log('baiduListTree 节点:');
  tree.forEach(n => console.log('  -', n.name, '| type:', n.type));
})().catch(e => console.log('ERR:', e.message));
