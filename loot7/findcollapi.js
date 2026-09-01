const https = require("https");
const APPID = "wx9659b8401a6505ed";
const APPSECRET = "844eefffacfef0d5629f45ad71d9c257";
const ENV = "cloud1-d4g2at0je9153becc";

async function getToken() {
  return new Promise(r => {
    https.get("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid="+APPID+"&secret="+APPSECRET, res => {
      let d=""; res.on("data",c=>d+=c); res.on("end",()=>r(JSON.parse(d).access_token));
    });
  });
}

async function api(path, data) {
  const token = await getToken();
  const json = JSON.stringify(data);
  return new Promise(r => {
    const req = https.request({
      hostname:"api.weixin.qq.com", path: path + "?access_token=" + token, method:"POST",
      headers:{"Content-Type":"application/json","Content-Length":Buffer.byteLength(json)}
    }, res => { let d=""; res.on("data",c=>d+=c); res.on("end",()=>r(JSON.parse(d))); });
    req.write(json); req.end();
  });
}

async function main() {
  // Try all possible collection creation API paths
  const paths = [
    // Try the WeChat-specific ones
    "/tcb/dbcollectioncreate",
    "/tcb/addcollection",
    "/tcb/createcollection",
    "/tcb/mkcollection",
    "/tcb/collectionadd",
    "/tcb/newcollection",
    // With underscore variations
    "/tcb/db_createcollection",
    "/tcb/db_create_collection",
    // Without tcb prefix
    "/tcb/collection/create",
    "/tcb/database/create",
    // TCB API v2 paths
    "/tcb/v2/createcollection",
    "/tcb/v1/createcollection",
  ];
  
  for (const p of paths) {
    const r = await api(p, {env: ENV, collection_name: "test", name: "test"});
    if (r.errcode !== 40066) {
      console.log("✅ " + p + ": [" + r.errcode + "] " + (r.errmsg||"OK").substring(0, 60));
    }
  }

  // Also try the db.runCommand approach through databaseadd
  console.log("\n--- Trying db.runCommand ---");
  const r = await api("/tcb/databaseadd", {
    env: ENV,
    query: JSON.stringify({create: "test_col1"})
  });
  console.log("raw JSON:", JSON.stringify(r).substring(0, 150));
  
  // Try Mongo wire protocol commands
  const r2 = await api("/tcb/databaseadd", {
    env: ENV, 
    query: 'db.runCommand({create: "test_col2"})'
  });
  console.log("runCommand:", JSON.stringify(r2).substring(0, 150));
}
main().catch(e => console.error(e));
