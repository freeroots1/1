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
  // 1. 先查所有商品（分批）
  const r = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(100).orderBy("sortOrder","asc").get()'});
  if(!r.data){console.log('查失败:',JSON.stringify(r).substring(0,100));return;}
  const all = r.data.map(s=>JSON.parse(s));
  console.log('共查得:', all.length);
  
  // 2. 标热销：前30个（不包含价格0的临时商品）
  let hotCount = 0, flashCount = 0;
  for(let i=0; i<Math.min(30, all.length); i++){
    const p = all[i];
    if(p.selling_price <= 0) continue; // 跳过临时商品
    // 更新isHot
    const r1 = await ap('/tcb/databaseupdate',{env:ENV,query:'db.collection("products").doc("'+p._id+'").update({data:{isHot:true}})'});
    if(r1.updated && r1.updated > 0) { hotCount++; process.stdout.write('.'); }
  }
  
  // 3. 标秒杀：前6个（不同类）
  for(let i=0; i<6; i++){
    const p = all[i];
    if(!p || p.selling_price <= 0) continue;
    const r2 = await ap('/tcb/databaseupdate',{env:ENV,query:'db.collection("products").doc("'+p._id+'").update({data:{isFlash:true,flash_price:Math.round(p.selling_price*0.85*10)/10}})'});
    if(r2.updated && r2.updated > 0) { flashCount++; process.stdout.write('*'); }
  }
  
  console.log('\n热销标记:', hotCount);
  console.log('秒杀标记:', flashCount);
  
  // 4. Banner补图片占位
  const banners = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("banners").limit(10).get()'});
  if(banners.data){
    const bs = banners.data.map(s=>JSON.parse(s));
    for(const b of bs){
      await ap('/tcb/databaseupdate',{env:ENV,query:'db.collection("banners").doc("'+b._id+'").update({data:{_banner:true,image_placeholder:true,image_color:"#C41E1E"}})'});
    }
  }
  
  // 5. 校验
  const r3 = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(100).get()'});
  let hc=0, fc=0;
  if(r3.data){
    const list = r3.data.map(s=>JSON.parse(s));
    hc = list.filter(p=>p.isHot===true).length;
    fc = list.filter(p=>p.isFlash===true).length;
  }
  console.log('最终校验 - 热销:', hc, '秒杀:', fc);
  console.log('✅ 修复完成！');
}
main().catch(e=>console.error(e.message));
