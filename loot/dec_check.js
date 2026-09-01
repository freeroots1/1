const fs=require("fs"),crypto=require("crypto");
const kdf=crypto.scryptSync(process.env.ADMIN,"pandel-settings-v1",32,{N:16384,r:8,p:1});
const j=JSON.parse(fs.readFileSync("/home/ubuntu/app/coolink/data/settings.json","utf8"));
const raw=Buffer.from(j.data,"base64");
try {
  const dec=crypto.createDecipheriv("aes-256-gcm",kdf,raw.subarray(0,12));
  dec.setAuthTag(raw.subarray(12,28));
  const s=JSON.parse(Buffer.concat([dec.update(raw.subarray(28)),dec.final()]).toString("utf8"));
  console.log("解密 OK，顶层键:", Object.keys(s));
  console.log("cookies 键:", Object.keys(s.cookies||{}));
} catch(e) {
  console.log("解密失败:", e.message);
  console.log("raw 长度:", raw.length, "iv:", raw.subarray(0,12).toString("hex").slice(0,24));
}
