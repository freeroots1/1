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
  // 1. Get categories
  const r = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("categories").limit(10).get()'});
  const cats = r.data.map(s=>JSON.parse(s));
  const nameToId = {};
  cats.forEach(c => { nameToId[c.name] = c._id; });
  console.log('当前分类:', Object.entries(nameToId).map(([k,v])=>k+'->'+v.slice(0,12)).join('\n  '));
  
  // 2. Seed data old id mapping
  const seed = JSON.parse(fs.readFileSync('/root/.openclaw/workspace/祥和超市小程序/seed-data.json','utf8'));
  const oldIdToName = {};
  seed.categories.forEach(c => { oldIdToName[c.id] = c.name; });
  
  // 3. Get products in batches
  let updated = 0;
  for(let skip=0; skip<253; skip+=100){
    const q = 'db.collection("products").skip('+skip+').limit(100).get()';
    const res = await ap('/tcb/databasequery',{env:ENV,query:q});
    if(!res.data) break;
    const list = res.data.map(s=>JSON.parse(s));
    for(const p of list){
      const catName = oldIdToName[p.category_id];
      if(!catName) continue;
      const newCid = nameToId[catName];
      if(!newCid || p.category_id === newCid) continue;
      await ap('/tcb/databaseupdate',{env:ENV,query:'db.collection("products").doc("'+p._id+'").update({data:{category_id:"'+newCid+'"}})'});
      updated++;
    }
  }
  console.log('✅ 更新了', updated, '条');
  
  // 4. Verify
  for(const [name, id] of Object.entries(nameToId)){
    const ch = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").where({category_id:"'+id+'",status:"up"}).limit(1).get()'});
    console.log('  '+name+':', ch.pager?.Total||0, '件');
  }
}
main().catch(e=>console.error(e.message));
