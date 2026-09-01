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
  const r = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(50).get()'});
  if(r.data){
    // r.data is an array of JSON strings
    const list = r.data.map(s => JSON.parse(s));
    
    const hasHot = list.filter(p => p.isHot === true);
    const hasFlash = list.filter(p => p.isFlash === true);
    const hasUp = list.filter(p => p.status === 'up');
    const hasImg = list.filter(p => p.main_image && p.main_image.length > 0);
    
    console.log('样本(50条):');
    console.log('  status=up:', hasUp.length);
    console.log('  isHot=true:', hasHot.length);
    console.log('  isFlash=true:', hasFlash.length);
    console.log('  有main_image:', hasImg.length);
    
    console.log('\n前5个:');
    list.slice(0,5).forEach(p => {
      console.log(`  ${p.name} | status:${p.status} | hot:${p.isHot}(${typeof p.isHot}) | flash:${p.isFlash}(${typeof p.isFlash}) | price:${p.selling_price}`);
    });
    
    // Check isHot values
    const hotValues = [...new Set(list.map(p => p.isHot))];
    console.log('\nisHot所有值:', hotValues.map(v => `${v}(${typeof v})`));
    
    const statusValues = [...new Set(list.map(p => p.status))];
    console.log('status所有值:', statusValues);
  }

  // 分类
  const r2 = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("categories").limit(10).get()'});
  if(r2.data){
    const list = r2.data.map(s => JSON.parse(s));
    console.log('\n分类:', list.map(c=>`${c.name} (${c._id})`).join('\n  '));
  }

  // Banner
  const r3 = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("banners").limit(10).get()'});
  if(r3.data){
    const list = r3.data.map(s => JSON.parse(s));
    console.log('\nBanner:', list.map(b=>`${b.title||'无'} img:${b.image?'有':'无'}`).join('\n  '));
  }
}
main().catch(e=>console.error(e.message));
