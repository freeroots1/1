const https = require('https');
const fs = require('fs');
const APPID = 'wx9659b8401a6505ed';
const ENV = 'cloud1-d4g2at0je9153becc';
const APPSECRET = '844eefffacfef0d5629f45ad71d9c257';
const seed = JSON.parse(fs.readFileSync('/root/.openclaw/workspace/祥和超市小程序/seed-data.json','utf8'));

// Get fresh token
function getToken(){return new Promise(r=>{https.get('https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid='+APPID+'&secret='+APPSECRET,res=>{let b='';res.on('data',c=>b+=c);res.on('end',()=>r(JSON.parse(b).access_token));});});}
async function ap(p,d){const t=await getToken();const j=JSON.stringify(d);return new Promise(r=>{const req=https.request({hostname:'api.weixin.qq.com',path:p+'?access_token='+t,method:'POST',headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(j)}},res=>{let b='';res.on('data',c=>b+=c);res.on('end',()=>r(JSON.parse(b)));});req.write(j);req.end();});}

async function main(){
  // Get fresh category IDs
  const r = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("categories").limit(10).get()'});
  const cats = r.data.map(s=>JSON.parse(s));
  const nameToId = {};
  cats.forEach(c => { nameToId[c.name] = c._id; });
  console.log('分类:');
  for(const [k,v] of Object.entries(nameToId)) console.log('  '+k+' -> '+v);
  
  const oldIdToName = {};
  seed.categories.forEach(c => { oldIdToName[c.id] = c.name; });
  
  const prods = seed.products;
  console.log('\n插入'+prods.length+'条...');
  let ok = 0;
  for(let i=0; i<prods.length; i+=50){
    const batch = prods.slice(i, i+50);
    const dataArray = batch.map((p,idx) => {
      const catName = oldIdToName[p.category_id] || '日用百货';
      const catId = nameToId[catName] || Object.values(nameToId)[0];
      const isHot = i+idx < 60 ? true : Math.random() < 0.2; // first 60 are hot
      const isFlash = Math.random() < 0.06;
      return {
        name: p.name, category_id: catId,
        selling_price: p.selling_price||0, original_price: p.original_price||0,
        stock: p.stock||99, unit: p.unit||'份', status: 'up',
        isHot, isFlash,
        flash_price: isFlash ? Math.round((p.selling_price||0)*0.85*10)/10 : 0,
        sold: Math.floor(Math.random()*100), sortOrder: ok+idx,
        description: p.name, main_image: '', barcode: '', min_stock: 10,
        cost_price: Math.round((p.selling_price||0)*0.7)
      };
    });
    const query = 'db.collection("products").add({data: ' + JSON.stringify(dataArray) + '})';
    const res = await ap('/tcb/databaseadd',{env:ENV,query:query});
    if(res.errcode === 0){ ok+=batch.length; process.stdout.write('.'); }
    else { console.log('\nFAIL:',JSON.stringify(res).substring(0,100)); return; }
  }
  console.log('\n插入完成:', ok);
  
  // Verify
  const r2 = await ap('/tcb/databasequery',{env:ENV,query:'db.collection("products").limit(253).get()'});
  const all = r2.data.map(s=>JSON.parse(s));
  console.log('\n=== 最终 ===');
  console.log('总计:', all.length);
  for(const [name, id] of Object.entries(nameToId)){
    const cnt = all.filter(p=>p.category_id===id).length;
    const h = all.filter(p=>p.category_id===id&&p.isHot).length;
    const f = all.filter(p=>p.category_id===id&&p.isFlash).length;
    console.log(`  ${name}: ${cnt}件 (热${h} 闪${f})`);
  }
  console.log('全部热销:', all.filter(p=>p.isHot).length, '秒杀:', all.filter(p=>p.isFlash).length);
}
main().catch(e=>console.error(e.message));
