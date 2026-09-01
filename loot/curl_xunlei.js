const http=require('http');
const data=JSON.stringify({share_url:'https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1?pwd=c233',pass_code:'c233',url:'https://pan.xunlei.com/s/VOzZsgPqtVS_wJej8qWRv9P9A1?pwd=c233'});
const req=http.request({host:'127.0.0.1',port:3000,path:'/api/xunlei/share',method:'POST',headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(data)}},(x)=>{let b='';x.on('data',c=>b+=c);x.on('end',()=>console.log(b.slice(0,2500)))});
req.on('error',e=>console.log('ERR',e.message));req.write(data);req.end();
