const https = require('https');
const fs = require('fs');
const APPID = 'wx9659b8401a6505ed';
const ENV = 'cloud1-d4g2at0je9153becc';
const creds = fs.readFileSync('/root/.openclaw/workspace/projects/祥和超市/小程序/credentials.md','utf8');

// Try multiple regex patterns for AppSecret
let APPSECRET = '';
let match = creds.match(/844eefffacfef0d5629f45ad71d9c257/);
if(match) APPSECRET = '844eefffacfef0d5629f45ad71d9c257';
console.log('secret found:', APPSECRET ? APPSECRET.slice(0,6)+'...' : 'NOT FOUND');

function getToken(){
  return new Promise(r=>{
    https.get('https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid='+APPID+'&secret='+APPSECRET,res=>{
      let b='';res.on('data',c=>b+=c);res.on('end',()=>{const d=JSON.parse(b);console.log('token err:', d.errcode||'none');r(d.access_token);});
    });
  });
}

async function ap(p,d){
  const t = await getToken();
  const j = JSON.stringify(d);
  return new Promise(r=>{
    const req=https.request({hostname:'api.weixin.qq.com',path:p+'?access_token='+t,method:'POST',headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(j)}},res=>{
      let b='';res.on('data',c=>b+=c);res.on('end',()=>r(JSON.parse(b)));
    });req.write(j);req.end();
  });
}

async function main(){
  const r = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(2).get()'});
  console.log('query result:', JSON.stringify(r).substring(0,500));
  if(r.data && r.data.length>0){
    const d = JSON.parse(r.data)[0];
    console.log('首个商品字段:', Object.keys(d).join(', '));
    console.log('name:', d.name);
    console.log('price fields:', JSON.stringify({price:d.price, selling_price:d.selling_price, original_price:d.original_price, stock:d.stock}));
    console.log('status:', d.status);
  }
}
main().catch(e=>console.error(e.message));
