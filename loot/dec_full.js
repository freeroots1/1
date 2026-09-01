const fs=require("fs"),crypto=require("crypto");
const kdf=crypto.scryptSync(process.env.ADMIN,"pandel-settings-v1",32,{N:16384,r:8,p:1});
const j=JSON.parse(fs.readFileSync("/home/ubuntu/app/coolink/data/settings.json","utf8"));
const raw=Buffer.from(j.data,"base64");
const dec=crypto.createDecipheriv("aes-256-gcm",kdf,raw.subarray(0,12)); dec.setAuthTag(raw.subarray(12,28));
const s=JSON.parse(Buffer.concat([dec.update(raw.subarray(28)),dec.final()]).toString("utf8"));
console.log("cookies:", JSON.stringify(s.cookies).slice(0,300));
console.log("pan123Account:", JSON.stringify(s.pan123Account).slice(0,150));
console.log("xunleiCaptchaToken len:", s.xunleiCaptchaToken ? s.xunleiCaptchaToken.length : 0);
