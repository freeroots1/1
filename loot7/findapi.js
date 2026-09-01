const https = require("https");
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
  // Find which API path works for creating a function
  const endpoints = [
    "/tcb/createfunction",
    "/tcb/createFunction",
    "/tcb/CreateFunction",
    "/tcb/addfunction",
    "/tcb/addFunction",
    "/tcb/functioncreate",
    "/tcb/functionCreate",
  ];
  
  const body = {env: ENV, function_name: "seedData", handler: "index.main", runtime: "Nodejs18.16"};
  for (const ep of endpoints) {
    const r = await api(ep, body);
    if (r.errcode !== 40066) {
      console.log("WORKING: " + ep + " => [" + r.errcode + "] " + (r.errmsg||"").substring(0,60));
    }
  }
  
  // Also get cloudbase token
  const r = await api("/tcb/cloudbaseaccesstoken", {env: ENV});
  console.log("\ncloudbase token: " + JSON.stringify(r).substring(0, 200));
}
main().catch(e => console.error("ERR:", e.message));
