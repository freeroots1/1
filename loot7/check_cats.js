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
  // 查分类
  const r2 = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("categories").limit(10).get()'});
  const cats = r2.data.map(s=>JSON.parse(s));
  console.log('分类(_id vs 原名顺序与seed-data.json相同?):');
  cats.forEach((c,i) => console.log('  '+c._id.slice(0,8)+'.. -> '+c.name));
  
  // 查商品用的category_id
  const r = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(50).get()'});
  const prods = r.data.map(s=>JSON.parse(s));
  const usedCids = [...new Set(prods.map(p=>p.category_id))];
  const availableCids = cats.map(c=>c._id);
  
  console.log('\n商品中用到的category_id:', usedCids.map(c=>c.slice(0,8)+'..'));
  console.log('\n分类可用的_id:', availableCids.map(c=>c.slice(0,8)+'..'));
  
  // 找不匹配
  const missing = usedCids.filter(cid => !availableCids.includes(cid));
  if(missing.length > 0) {
    console.log('\n❌ 匹配不上的category_id:', missing.map(c=>c.slice(0,8)+'..'));
    
    // 查种子数据原始分类ID
    const seed = JSON.parse(fs.readFileSync('/root/.openclaw/workspace/祥和超市小程序/seed-data.json','utf8'));
    if(seed.categories){
      console.log('\n种子数据原始分类:');
      seed.categories.forEach(c => console.log('  '+c.id.slice(0,8)+'.. -> '+c.name));
    }
    
    // 需要把商品category_id更新为新的_id
    // 按名字匹配
    console.log('\n按名称匹配新旧ID:');
    const nameToNewId = {};
    cats.forEach(c => { nameToNewId[c.name] = c._id; });
    
    const seedCats = seed.categories;
    seedCats.forEach(sc => {
      const newId = nameToNewId[sc.name];
      if(newId){
        console.log('  '+sc.name+': '+sc.id.slice(0,8)+'.. -> '+newId.slice(0,8)+'..');
      } else {
        console.log('  ❌ '+sc.name+': 未找到匹配');
      }
    });
  } else {
    console.log('✅ 全部匹配！');
  }
}
main().catch(e=>console.error(e.message));
