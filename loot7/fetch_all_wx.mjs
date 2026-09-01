#!/usr/bin/env node
/**
 * 微信小程序开发文档 · 完整抓取 & Word生成
 * 
 * 流程:
 *   1) 遍历所有URL
 *   2) HTTP GET → 从SSR内容提取正文
 *   3) 分段存成Markdown
 *   4) 最终合成为单个Word文档 (.docx)
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync, appendFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ============ 配置 ============
const BASE = 'https://developers.weixin.qq.com';
const URL_FILE = '/tmp/wx_all_urls.txt';
const OUT_DIR = '/root/.openclaw/workspace/参考资料/微信小程序开发文档/文本版';
const MASTER_TXT = join(OUT_DIR, '_全部合并_WECHAT_DEV_DOCS.txt');
const PROGRESS_FILE = '/tmp/wx_dl_progress.json';
const PARALLEL = 10;          // 并发数
const TIMEOUT_MS = 20000;

// ============ 确保目录 ============
mkdirSync(OUT_DIR, { recursive: true });

// ============ 读取URL ============
const urls = readFileSync(URL_FILE, 'utf-8')
  .split('\n').map(l => l.trim())
  .filter(l => l && l.startsWith('/miniprogram/dev/'));

console.log(`📋 共 ${urls.length} 个页面`);

// ============ 加载进度 ============
let doneList = [];
if (existsSync(PROGRESS_FILE)) {
  doneList = JSON.parse(readFileSync(PROGRESS_FILE, 'utf-8'));
  console.log(`🔄 已有进度: ${doneList.length}/${urls.length}`);
}
const doneSet = new Set(doneList);
const skipped = urls.filter(u => doneSet.has(u));
const remaining = urls.filter(u => !doneSet.has(u));
console.log(`⏳ 剩余: ${remaining.length}`);

// ============ 提取正文 ============
function extractContent(html) {
  // 先找到 docContent 区域
  const docIdx = html.indexOf('docContent');
  if (docIdx === -1) return '';
  
  // 从docContent往后找，直到遇到页脚
  const footerIdx = html.indexOf('关于腾讯', docIdx);
  const endIdx = footerIdx > 0 ? footerIdx + 200 : docIdx + 15000;
  const zone = html.substring(docIdx, Math.min(endIdx, html.length));
  
  // 去掉HTML标签, 保留文字
  let text = zone
    // 保留代码块的结构
    .replace(/<pre[^>]*>/gi, '\n```\n')
    .replace(/<\/pre>/gi, '\n```\n')
    // 换行符
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<\/li>/gi, '\n')
    .replace(/<\/tr>/gi, ' | ')
    .replace(/<\/td>/gi, ' | ')
    .replace(/<\/th>/gi, ' | ')
    // 去掉标签
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    // 清理空白
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{4,}/g, '\n\n')
    .replace(/\|[ \t]*\|[ \t]*\|/g, '| | |')  // 空表格
    .trim();
  
  // 过滤导航噪音
  const noiseStart = text.indexOf('The translations are provided');
  if (noiseStart > 0) text = text.substring(0, noiseStart).trim();
  
  return text;
}

// ============ 获取单页 ============
async function fetchPage(url) {
  const fullUrl = BASE + url;
  const resp = await fetch(fullUrl, {
    headers: { 'User-Agent': 'Mozilla/5.0 (compatible; DocBot)' },
    signal: AbortSignal.timeout(TIMEOUT_MS)
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const html = await resp.text();
  const text = extractContent(html);
  if (!text || text.length < 30) throw new Error('内容太少');
  return text;
}

// ============ 处理一批 ============
async function processBatch(batch) {
  const results = await Promise.allSettled(
    batch.map(async (url) => {
      if (doneSet.has(url)) return;
      
      const relPath = url.replace('/miniprogram/dev/', '');
      const fileName = relPath.replace(/\//g, '_').replace(/\.html?$/, '') || 'index';
      const outPath = join(OUT_DIR, fileName + '.md');
      
      if (existsSync(outPath)) {
        doneSet.add(url);
        return;
      }
      
      const text = await fetchPage(url);
      // 写入单独文件
      writeFileSync(outPath, text, 'utf-8');
      doneSet.add(url);
    })
  );
  
  for (let i = 0; i < results.length; i++) {
    const r = results[i];
    if (r.status === 'rejected') {
      console.error(`✗ ${batch[i].split('/').pop()}: ${r.reason?.message || '?'}`);
      doneSet.add(batch[i]); // 失败也标记，避免死循环
    }
  }
}

// ============ 主循环 ============
async function main() {
  const startTime = Date.now();
  let idx = 0;
  
  while (idx < remaining.length) {
    const batch = remaining.slice(idx, idx + PARALLEL);
    await processBatch(batch);
    idx += PARALLEL;
    
    // 每批保存进度
    writeFileSync(PROGRESS_FILE, JSON.stringify([...doneSet]));
    
    const elapsed = Math.round((Date.now() - startTime) / 1000);
    const perSec = Math.round(doneSet.size / elapsed * 10) / 10;
    console.log(`📊 [${doneSet.size}/${urls.length}] ${elapsed}s @ ${perSec}页/秒`);
  }
  
  console.log(`\n✅ 下载完成! 共 ${doneSet.size} 页`);
  
  // ============ 生成汇总 ============
  console.log('📝 生成汇总文件...');
  const allFiles = [];
  for (const url of urls) {
    const relPath = url.replace('/miniprogram/dev/', '');
    const fileName = relPath.replace(/\//g, '_').replace(/\.html?$/, '') || 'index';
    const fpath = join(OUT_DIR, fileName + '.md');
    if (existsSync(fpath)) {
      allFiles.push({ url, file: fpath });
    }
  }
  
  // 按URL分组排序
  allFiles.sort((a, b) => a.url.localeCompare(b.url));
  
  let totalChars = 0;
  const out = writeFileSync(MASTER_TXT, '', 'utf-8');
  
  for (const { url, file } of allFiles) {
    const content = readFileSync(file, 'utf-8');
    totalChars += content.length;
    const title = content.split('\n')[0] || url.split('/').pop();
    appendFileSync(MASTER_TXT, 
      `\n\n${'='.repeat(80)}\n` +
      `# ${title}\n` +
      `原文: ${BASE}${url}\n` +
      `${'='.repeat(80)}\n\n` +
      content + '\n',
      'utf-8'
    );
  }
  
  console.log(`📄 汇总文件: ${MASTER_TXT}`);
  console.log(`📊 总字数: ${totalChars.toLocaleString()}`);
  console.log(`⏱️ 总耗时: ${Math.round((Date.now() - startTime)/1000)}秒`);
}

main().catch(err => {
  console.error('致命错误:', err);
  process.exit(1);
});
