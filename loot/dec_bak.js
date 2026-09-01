const fs=require("fs"),crypto=require("crypto");
const kdf=crypto.scryptSync(process.env.ADMIN,"pandel-settings-v1",32,{N:16384,r:8,p:1});
const j=JSON.parse(fs.readFileSync("/home/ubuntu/app/coolink/data/settings.json.plain.bak","utf8"));
console.log("plain.bak 顶层键:", Object.keys(j));
const b64 = j.data;
console.log("data base64 长度:", String(b64).length);
const raw=Buffer.from(String(b64),"base64");
console.log("raw 长度:", raw.length);
try {
  const dec=crypto.createDecipheriv("aes-256-gcm",kdf,raw.subarray(0,12));
  dec.setAuthTag(raw.subarray(12,28));
  const s=JSON.parse(Buffer.concat([dec.update(raw.subarray(28)),dec.final()]).toString("utf8"));
  console.log("✅ 解密成功！顶层键:", Object.keys(s));
  const c = s.cookies||{};
  console.log("cookies:", Object.fromEntries(Object.entries(c).map(([k,v])=>[k, v?String(v).length+"字符":"空"])));
  console.log("xunleiCaptchaToken len:", s.xunleiCaptchaToken ? s.xunleiCaptchaToken.length : 0);
  console.log("promo:", Object.keys(s.promo||{}));
} catch(e) {
  console.log("❌ 解密失败:", e.message);
}
