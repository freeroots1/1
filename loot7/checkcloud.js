const https = require("https");
const fs = require("fs");
const path = require("path");
const APPID = "wx9659b8401a6505ed";
const APPSECRET = "844eefffacfef0d5629f45ad71d9c257";
const ENV = "cloud1-d4g2at0je9153becc";

async function post(path, data) {
  const token = await new Promise((r) => {
    https.get("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid="+APPID+"&secret="+APPSECRET, (res) => {
      let d=""; res.on("data",c=>d+=c); res.on("end",()=>r(JSON.parse(d).access_token));
    });
  });
  const json = JSON.stringify(data);
  return new Promise((r) => {
    const req = https.request({
      hostname:"api.weixin.qq.com", path: path + "?access_token=" + token, method:"POST",
      headers:{"Content-Type":"application/json","Content-Length":Buffer.byteLength(json)}
    }, (res) => { let d=""; res.on("data",c=>d+=c); res.on("end",()=>r(JSON.parse(d))); });
    req.write(json); req.end();
  });
}

async function main() {
  // 1. Try invoking cloud function
  console.log("--- 调云函数 seedData ---");
  const r1 = await post("/tcb/invokecloudfunction", {
    env: ENV,
    name: "seedData",
    query_str: JSON.stringify({force: true})
  });
  console.log(r1.errcode ? `FAIL [${r1.errcode}] ${r1.errmsg}` : JSON.stringify(r1).substring(0, 200));

  // 2. Try invoke via different API path
  console.log("\n--- 检查集合列表 ---");
  const r2 = await post("/tcb/databasecollectionget", { env: ENV, limit: 20 });
  if (r2.collections) {
    console.log("已有集合:", r2.collections.map(c => c.name).join(", "));
  } else {
    console.log(JSON.stringify(r2));
  }

  // 3. Try bulk insert into products - if it auto-creates
  console.log("\n--- 测试数据库插入 ---");
  const r3 = await post("/tcb/databaseadd", {
    env: ENV,
    query: 'db.collection("products").add({data: {name:"测试用",status:"up",selling_price:10}})'
  });
  console.log("插入结果:", JSON.stringify(r3));
}
main().catch(e => console.error(e));
