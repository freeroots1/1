const http=require('http');
function post(path,body){return new Promise((res,rej)=>{const d=JSON.stringify(body);const r=http.request({host:'127.0.0.1',port:3000,path,method:'POST',headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(d)}},(x)=>{let b='';x.on('data',c=>b+=c);x.on('end',()=>{try{res(JSON.parse(b));}catch(e){res({_raw:b.slice(0,300)});}});});r.on('error',rej);r.write(d);r.end();});}
(async()=>{
  const t0=Date.now();
  const sh=await post('/api/xunlei/share',{share_url:'https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1?pwd=c233',pass_code:'c233',url:'https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1?pwd=c233'});
  console.log('耗时', ((Date.now()-t0)/1000).toFixed(1)+'s ok=', sh.ok);
  console.log('顶层 keys:', Object.keys(sh));
  const ft = sh.full_tree || [];
  console.log('full_tree 长度:', ft.length);
  if(ft[0]){
    console.log('根节点:', ft[0].name, 'type=', ft[0].type, 'dir=', ft[0].dir);
    console.log('children 数:', (ft[0].children||[]).length);
    const c0=(ft[0].children||[])[0];
    if(c0) console.log('首子:', c0.name, 'size=', c0.size);
  }
  // result.files[0] 是否内嵌 children
  const rf=(sh.result&&sh.result.files||[])[0];
  console.log('result.files[0].children:', rf ? (rf.children||[]).length : 'n/a');
})();
