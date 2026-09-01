const https = require('https');
const fs = require('fs');
const APPID = 'wx9659b8401a6505ed';
const ENV = 'cloud1-d4g2at0je9153becc';
const APPSECRET = '844eefffacfef0d5629f45ad71d9c257';

function getToken(){
  return new Promise(r=>{
    https.get('https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid='+APPID+'&secret='+APPSECRET,res=>{
      let b='';res.on('data',c=>b+=c);res.on('end',()=>r(JSON.parse(b).access_token));
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
  // 先确认热销
  const r0 = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(100).get()'});
  const list = r0.data.map(s=>JSON.parse(s));
  console.log('总商品:', list.length, '热销:', list.filter(p=>p.isHot===true).length);
  
  // 标秒杀（选不同分类的前几个商品）
  const cats = [...new Set(list.map(p=>p.category_id))];
  console.log('分类IDs:', cats);
  
  for(const cid of cats){
    const catProducts = list.filter(p=>p.category_id===cid && p.selling_price>0 && p.isHot===true);
    if(catProducts.length>0){
      const p = catProducts[0];
      const flashP = Math.round(p.selling_price * 0.85 * 10) / 10;
      const r = await ap('/tcb/databaseupdate',{env:ENV,query:'db.collection("products").doc("'+p._id+'").update({data:{isFlash:true,flash_price:'+flashP+'}})'});
      console.log(`  ${p.name} -> 秒杀¥${flashP}:`, r.updated ? '+1' : 'no');
    }
  }
  
  // 最终校验
  const r3 = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(100).get()'});
  if(r3.data){
    const all = r3.data.map(s=>JSON.parse(s));
    console.log('\n✅ 最终: 热销', all.filter(p=>p.isHot===true).length, '条, 秒杀', all.filter(p=>p.isFlash===true).length, '条');
  }
}
main().catch(e=>console.error(e.message));
