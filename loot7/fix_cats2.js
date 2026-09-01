const https = require('https');
const fs = require('fs');
const APPID = 'wx9659b8401a6505ed';
const ENV = 'cloud1-d4g2at0je9153becc';
const APPSECRET = '844eefffacfef0d5629f45ad71d9c257';
const seed = JSON.parse(fs.readFileSync('/root/.openclaw/workspace/祥和超市小程序/seed-data.json','utf8'));

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
  // 映射新ID
  const r = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("categories").limit(10).get()'});
  const cats = r.data.map(s=>JSON.parse(s));
  const nameToId = {};
  cats.forEach(c => { nameToId[c.name] = c._id; });
  
  const oldIdToName = {};
  seed.categories.forEach(c => { oldIdToName[c.id] = c.name; });
  
  // 获取全部253商品（一次）
  const res = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(253).get()'});
  const all = res.data.map(s=>JSON.parse(s));
  console.log('共', all.length, '条商品');
  
  let updated = 0, skipped = 0;
  for(const p of all){
    const catName = oldIdToName[p.category_id];
    if(!catName) { console.log('  ❌ 未知旧ID:', p.category_id.slice(0,12), p.name); skipped++; continue; }
    const newCid = nameToId[catName];
    if(!newCid) { skipped++; continue; }
    if(p.category_id === newCid) { skipped++; continue; }
    
    const up = await ap('/tcb/databaseupdate',{env:ENV,query:'db.collection("products").doc("'+p._id+'").update({data:{category_id:"'+newCid+'"}})'});
    if(up.errcode === 0 || up.updated > 0) { updated++; process.stdout.write('.'); }
    else console.log('\n❌ 更新失败:', p.name, JSON.stringify(up));
  }
  
  console.log('\n\n✅ 更新:', updated, '条, 跳过:', skipped);
  
  // 最终校验
  for(const [name, id] of Object.entries(nameToId)){
    const ch = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").where({category_id:"'+id+'",status:"up"}).limit(1).get()'});
    console.log('  '+name+':', ch.pager?.Total||0, '件');
  }
}
main().catch(e=>console.error(e.message));
