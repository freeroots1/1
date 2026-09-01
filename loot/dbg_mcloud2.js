const crypto = require('crypto'), https = require('https'), fs = require('fs');
const KEY2 = Buffer.from('PVGDwmcvfs1uV3d1', 'utf8');
function yunEncrypt(obj){const json=JSON.stringify(obj);const iv=crypto.randomBytes(16);const c=crypto.createCipheriv('aes-128-cbc',KEY2,iv);const ct=Buffer.concat([c.update(Buffer.from(json,'utf8')),c.final()]);return Buffer.concat([iv,ct]).toString('base64');}
function yunDecrypt(b64){try{const raw=Buffer.from(String(b64).replace(/\s+/g,''),'base64');const iv=raw.subarray(0,16),ct=raw.subarray(16);const dc=crypto.createDecipheriv('aes-128-cbc',KEY2,iv);let out=Buffer.concat([dc.update(ct),dc.final()]);if(out.length>2&&out[0]===0x1f&&out[1]===0x8b){try{out=require('zlib').gunzipSync(out);}catch(e){}}const pad=out[out.length-1];if(pad>0&&pad<=16)out=out.subarray(0,out.length-pad);return out.toString('utf8');}catch(e){return '';}}
function decrypt(p){const j=JSON.parse(fs.readFileSync(p,'utf8'));
  const key=crypto.scryptSync('AeLnUxLVwcTVBDU5',Buffer.from('pandel-settings-v1','utf8'),32,{N:16384,r:8,p:1});
  const b=Buffer.from(j.data,'base64');const d=crypto.createDecipheriv('aes-256-gcm',key,b.subarray(0,12));d.setAuthTag(b.subarray(12,28));
  return JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]).toString('utf8'));}
const o = decrypt('/home/ubuntu/app/coolink/data/settings.json');
const ck = o.cookies.mcloud || '';
const get = (k) => (ck.match(new RegExp('(?:^;\\s*)'+k+'=([^;]*)'))||[])[1]||'';
const account = Buffer.from(get('ORCHES-I-ACCOUNT-ENCRYPT'), 'base64').toString('utf8');
const auth = 'Basic ' + Buffer.from('pc:'+account+':'+get('auth_token'),'utf8').toString('base64');
console.log('account:', account, 'auth head:', auth.slice(0,40));
const host = 'https://share-kd-njs.yun.139.com/yun-share/richlifeApp/devapp/IOutLink';
const code = '2qiemnTF83eac';
function post(url, headers, body){return new Promise((res,rej)=>{const r=https.request(new URL(url),{method:'POST',headers:{'Content-Length':Buffer.byteLength(body),...headers}},(x)=>{let b='';x.on('data',c=>b+=c);x.on('end',()=>res({status:x.statusCode,body:b}));});r.on('error',rej);r.write(body);r.end();});}
(async()=>{
  // 列表拿 coID
  const lb = JSON.stringify({getOutLinkInfoReq:{account:'',linkID:code,pCaID:'root'}});
  const lr = await post(host+'/getOutLinkInfoV6',{'User-Agent':'Mozilla/5.0','Content-Type':'application/json;charset=UTF-8'},lb);
  const lj = JSON.parse(lr.body);
  const folder = (lj.data.caLst||[])[0];
  console.log('根文件夹:', folder && folder.caName, folder && folder.caID);
  // 下钻找文件
  const lb2 = JSON.stringify({getOutLinkInfoReq:{account:'',linkID:code,pCaID:folder.caID}});
  const lr2 = await post(host+'/getOutLinkInfoV6',{'User-Agent':'Mozilla/5.0','Content-Type':'application/json;charset=UTF-8'},lb2);
  const lj2 = JSON.parse(lr2.body);
  const f = (lj2.data.coLst||[])[0];
  console.log('文件:', f.coName, f.coID, f.coType);
  // 加密下载请求
  const req = {getContentInfoFromOutLinkReq:{contentId:f.coID, linkID:code, account}};
  const enc = yunEncrypt(req);
  const r = await post(host+'/getContentInfoFromOutLink',{
    'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
    'Accept':'application/json, text/plain, */*','Content-Type':'application/json;charset=UTF-8','Authorization':auth,
    'X-Deviceinfo':'||9|12.27.0|firefox|140.0|12b780037221ab547c682223327dc9cd||linux unknow|1920X526|zh-CN|||',
    'hcy-cool-flag':'1','CMS-DEVICE':'default','x-m4c-caller':'PC','X-Yun-Api-Version':'v1',
    'Origin':'https://yun.139.com','Referer':'https://yun.139.com/',
  }, enc);
  console.log('status:', r.status, 'body前200:', r.body.slice(0,200));
  const dec = yunDecrypt(r.body);
  console.log('解密:', dec.slice(0,300));
  try {
    const dl = JSON.parse(dec);
    const ci = (dl.data && dl.data.contentInfo) || dl.contentInfo || {};
    console.log('URL字段:', JSON.stringify(Object.fromEntries(Object.entries(ci).filter(([k,v])=>typeof v==='string'&&/url|link|http/i.test(k)))));
  } catch(e){ console.log('parse err', e.message); }
})().catch(e=>console.log('ERR',e.message));
