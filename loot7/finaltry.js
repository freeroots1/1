const https = require("https");
const fs = require("fs");
const APPID = "wx9659b8401a6505ed";
const APPSECRET = "844eefffacfef0d5629f45ad71d9c257";
const ENV = "cloud1-d4g2at0je9153becc";

async function getToken() {
  return new Promise((r) => {
    https.get("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid="+APPID+"&secret="+APPSECRET, (res) => {
      let d=""; res.on("data",c=>d+=c); res.on("end",()=>r(JSON.parse(d).access_token));
    });
  });
}

async function api(path, data) {
  const token = await getToken();
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
  // Try: MongoDB command via databaseadd to create collection
  // db.createCollection() doesn't work through databaseadd
  // But what about db.runCommand?
  
  const queries = [
    'db.runCommand({create: "test_a1"})',
    '{create: "test_a2"}',
    'db.createCollection("test_a3")',
  ];
  
  // Use the createfunction API with the correct SCF-compatible format
  console.log("=== Try creating function ===\n");
  
  // Read the actual function code
  const funcDir = "/root/.openclaw/workspace/祥和超市小程序/miniprogram/cloudfunctions/seedData";
  const files = {};
  for (const f of fs.readdirSync(funcDir)) {
    files[f] = fs.readFileSync(funcDir+"/"+f, "utf8");
  }
  const zipBuffer = createZip(files);
  const zipBase64 = zipBuffer.toString("base64");
  
  // Try with ZipFile in correct format
  const r1 = await api("/tcb/createfunction", {
    env: ENV,
    function_name: "seedData",
    handler: "index.main",
    runtime: "Nodejs18.16",
    code: {zip_file: zipBase64}
  });
  console.log("createfunction with zip:", JSON.stringify(r1).substring(0, 200));
  
  // Try createCollection via databasemanage
  const r2 = await api("/tcb/databasemanage", {
    env: ENV,
    query: 'db.createCollection("test_b1")'
  });
  console.log("databasemanage:", JSON.stringify(r2).substring(0, 150));
  
  // Try: use the direct DB command via the new URL format
  // The correct path might be /tcb/databasecreate or similar
  const r3 = await api("/tcb/databasecreate", {env: ENV, name:"test_c1"});
  console.log("databasecreate:", JSON.stringify(r3).substring(0, 150));
  
  console.log("\n✅ 所有API测试完成");
}

function createZip(files) {
  // Create a minimal zip file for the cloud function
  const { execSync } = require("child_process");
  const tmpDir = "/tmp/seeddata-fn";
  fs.mkdirSync(tmpDir, {recursive: true});
  for (const [name, content] of Object.entries(files)) {
    fs.writeFileSync(tmpDir+"/"+name, content);
  }
  execSync("cd " + tmpDir + " && zip -r /tmp/seeddata.zip . 2>/dev/null");
  const data = fs.readFileSync("/tmp/seeddata.zip");
  fs.rmSync(tmpDir, {recursive: true, force: true});
  return data;
}

main().catch(e => console.error("ERR:", e.message));
