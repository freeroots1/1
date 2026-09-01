const { baiduRequest, BAIDU_API } = require('/home/ubuntu/app/coolink/server/lib/http.js');
(async () => {
  // 直接调百度 wxlist（无 cookie）看返回结构
  const surl = '1Tm_DbZhEAFsxuCWpCyz-6Q';
  const pwd = '2580';
  try {
    const info = await baiduRequest('POST',
      `${BAIDU_API}/share/wxlist?channel=weixin&version=2.2.2&clienttype=25&web=1`,
      `pwd=${encodeURIComponent(pwd)}&shorturl=${surl}&root=1`, '');
    console.log('wxlist ok:', info.ok !== false, '| errno:', info.errno, '| msg:', info.err_msg || info.message || '');
    if (info.data) {
      console.log('data keys:', Object.keys(info.data).join(','));
      console.log('uk:', info.data.uk, '| shareid:', info.data.shareid, '| seckey:', String(info.data.seckey || '').slice(0, 20));
      const list = info.data.list || [];
      console.log('list 数:', list.length);
      list.slice(0, 3).forEach(f => console.log('  -', f.server_filename, '| size:', f.size, '| isdir:', f.isdir));
    }
  } catch (e) {
    console.log('ERR:', e.message);
  }
})().catch(e => console.log('ERR:', e.message));
