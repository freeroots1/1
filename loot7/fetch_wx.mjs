import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';

const BASE = 'https://developers.weixin.qq.com';
const URL_FILE = '/tmp/wx_all_urls.txt';
const OUTPUT_DIR = '/root/.openclaw/workspace/参考资料/微信小程序开发文档/文本版';

mkdirSync(OUTPUT_DIR, { recursive: true });

const urls = readFileSync(URL_FILE, 'utf-8')
  .split('\n').map(l => l.trim()).filter(l => l && l.startsWith('/miniprogram/dev/'));

let done = 0, failed = 0;
const total = urls.length;
let progress = [];

// 恢复进度
const PROGRESS = '/tmp/wx_progress.json';
if (existsSync(PROGRESS)) {
  progress = JSON.parse(readFileSync(PROGRESS, 'utf-8'));
  console.log(`已有进度: ${progress.length}/${total}`);
}

const seen = new Set(progress);

async function fetchAndExtract(url, retries = 2) {
  const fullUrl = `${BASE}${url}`;
  try {
    const resp = await fetch(fullUrl, {
      headers: { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36' },
      signal: AbortSignal.timeout(15000)
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const html = await resp.text();
    
    // 提取正文：找到 #docContent .content 或 main 内的文字
    let text = '';
    
    // 方法1: 提取 <div class="content"> 内的文字（去掉HTML标签）
    const contentMatch = html.match(/<div[^>]*class="[^"]*\bcontent\b[^"]*"[^>]*>([\s\S]*?)<\/div>\s*<\/div>\s*<\/main>/);
    if (contentMatch) {
      text = contentMatch[1]
        .replace(/<script[\s\S]*?<\/script>/gi, '')
        .replace(/<style[\s\S]*?<\/style>/gi, '')
        .replace(/<[^>]+>/g, ' ')
        .replace(/&nbsp;/g, ' ')
        .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
        .replace(/\s+/g, ' ')
        .replace(/\n\s*\n/g, '\n')
        .trim();
    }
    
    // 方法2: 尝试从 <div id="docContent"> 提取
    if (!text || text.length < 50) {
      const docMatch = html.match(/<div[^>]*id="docContent"[^>]*>([\s\S]*?)<\/div>\s*<\/main>/);
      if (docMatch) {
        const raw = docMatch[1]
          .replace(/<script[\s\S]*?<\/script>/gi, '')
          .replace(/<style[\s\S]*?<\/style>/gi, '');
        text = extractText(raw);
      }
    }
    
    // 方法3: 从 <main> 标签提取
    if (!text || text.length < 50) {
      const mainMatch = html.match(/<main[^>]*>([\s\S]*?)<\/main>/);
      if (mainMatch) {
        const raw = mainMatch[1]
          .replace(/<script[\s\S]*?<\/script>/gi, '')
          .replace(/<style[\s\S]*?<\/style>/gi, '')
          .replace(/<nav[\s\S]*?<\/nav>/gi, '');
        text = extractText(raw);
      }
    }
    
    // 方法4: 标题
    if (!text || text.length < 30) {
      const titleMatch = html.match(/<title>([^<]*)<\/title>/);
      text = titleMatch ? `# ${titleMatch[1]}\n\n(内容由Vue动态渲染，未抓取到SSR文本)` : '';
    }
    
    return text;
  } catch (err) {
    if (retries > 0) {
      await new Promise(r => setTimeout(r, 2000));
      return fetchAndExtract(url, retries - 1);
    }
    throw err;
  }
}

function extractText(html) {
  // 去掉所有标签
  let text = html
    .replace(/<pre[^>]*>([\s\S]*?)<\/pre>/gi, (_, code) => {
      // 保留代码块内容，但还原格式
      return '\n```\n' + code.replace(/<[^>]+>/g, '') + '\n```\n';
    })
    .replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (_, tbl) => {
      return '\n\n[TABLE]\n' + tbl.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ') + '\n[/TABLE]\n\n';
    })
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<li[^>]*>/gi, '\n- ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
    .replace(/\n\s+/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{4,}/g, '\n\n')
    .trim();
  
  // 过滤掉导航文字/版权等噪音
  const noisePatterns = [
    /微信开放文档[\s\S]{0,100}?社区学堂/,
    /Copyright © 2012-2026 Tencent/,
    /京ICP备\d+/,
    /返回首页/,
    /页面不存在/,
  ];
  for (const pat of noisePatterns) {
    text = text.replace(pat, '');
  }
  
  return text;
}

async function run() {
  const batchSize = 20;
  
  for (let i = 0; i < total; i += batchSize) {
    const batch = urls.slice(i, Math.min(i + batchSize, total));
    const promises = batch.map(async (url) => {
      if (seen.has(url)) return;
      
      const relativePath = url.replace('/miniprogram/dev/', '');
      const fileName = relativePath.replace(/\//g, '_').replace(/\.html?$/, '') || 'index';
      const outPath = `${OUTPUT_DIR}/${fileName}.md`;
      
      if (existsSync(outPath)) {
        seen.add(url);
        return;
      }
      
      try {
        const text = await fetchAndExtract(url);
        writeFileSync(outPath, text, 'utf-8');
        seen.add(url);
        done++;
        if (done % 50 === 0) console.log(`[${done}/${total}] ${fileName}`);
      } catch (err) {
        failed++;
        console.error(`✗ ${fileName}: ${err.message}`);
        seen.add(url);
      }
    });
    
    await Promise.allSettled(promises);
    
    // 每轮保存进度
    writeFileSync(PROGRESS, JSON.stringify([...seen]));
  }
  
  console.log(`\n完成! 成功: ${done}, 失败: ${failed}/${total}`);
}

run().catch(console.error);
