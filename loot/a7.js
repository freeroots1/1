/* pandl-demo 管理后台前端（独立 chunk，仅访问 /admin 时加载）
 * 作为 ESM 模块导出 mountAdmin，由 admin.html 的 <script type="module"> 调用 */
import { createApp } from '/vendor/vue.esm-browser.prod.js?v=7';

export function mountAdmin() {
const PROVIDER_NAMES = { quark: '夸克网盘', baidu: '百度网盘', xunlei: '迅雷网盘', pan123: '123盘', mcloud: '移动云盘', uc: 'UC网盘' };
const PROVIDER_KEYS = Object.keys(PROVIDER_NAMES);

createApp({
  data() {
    return {
      authed: false,
      pwd: '',
      err: '',
      tab: 'overview',
      providerNames: PROVIDER_NAMES,
      providerKeys: PROVIDER_KEYS,
      overview: { parseOk: 0, parseFail: 0, activeDevices: 0, totalActions: 0, byProvider: {} },
      form: {
        cookies: { quark: '', baidu: '', xunlei: '', pan123: '', mcloud: '', uc: '' },
        cookieConfigured: {},
        cookieDirty: {},  // 记录哪些 Cookie 输入框被管理员动过（避免误清空）
        promo: {
          quark: { passcode: '', link: '', qrUrl: '' },
          baidu: { passcode: '', link: '', qrUrl: '' },
          xunlei: { passcode: '', link: '', qrUrl: '' },
          pan123: { passcode: '', link: '', qrUrl: '' },
          mcloud: { passcode: '', link: '', qrUrl: '' },
          uc: { passcode: '', link: '', qrUrl: '' },
        },
      },
      saved: false,
      logs: { admin: [], actions: [] },
      // 今日密码自动程序
      dailyPwd: null,
      pwdRunning: false,
      dailyPwdMsg: '',
      // 任务管理
      tasks: [],
      taskCategories: ['小文件', '大文件', '网盘解锁', '其它'],
    };
  },
  mounted() {
    this.checkAuth();
  },
  methods: {
    rewardTypeLabel(t) {
      const map = {
        unlock_small_file: '解锁小文件',
        unlock_large_file: '解除大小限制',
        unlock_downloader: '解锁发送下载器',
        small_file_all_providers: '追加小文件流量',
        small_file_single_provider: '追加指定网盘小文件',
        single_provider: '追加次数',
        default: '追加次数',
      };
      return map[t] || t;
    },
    async api(path, opts) {
      const r = await fetch(path, opts);
      return r.json();
    },
    async checkAuth() {
      const r = await this.api('/api/admin/auth-check');
      if (r.code === 0 && r.data && r.data.authed) {
        this.authed = true;
        this.loadOverview();
      }
    },
    async login() {
      this.err = '';
      const r = await this.api('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: this.pwd }),
      });
      if (r.code === 0) {
        this.authed = true;
        this.loadOverview();
      } else {
        this.err = r.msg || '登录失败';
      }
    },
    logout() {
      // admin_token 是 HttpOnly Cookie，document.cookie 删不掉 —— 走后端登出接口
      fetch('/api/admin/logout', { method: 'POST' }).finally(() => {
        this.authed = false;
        this.pwd = '';
      });
    },
    async loadOverview() {
      const r = await this.api('/api/admin/overview');
      if (r.code === 0) {
        this.overview = r.data;
      }
    },
    async loadAccounts() {
      this.tab = 'accounts';
      const [r1, r2] = await Promise.all([
        this.api('/api/admin/settings'),
        this.api('/api/admin/daily-password'),
      ]);
      if (r1.code === 0) {
        const s = r1.data || {};
        const promo = s.promo || {};
        const cookies = {};
        const cookieConfigured = s.cookieConfigured || {};
        const cookieDirty = {};
        for (const p of PROVIDER_KEYS) { cookies[p] = ''; cookieDirty[p] = false; }
        this.form = {
          cookies,
          cookieConfigured,
          cookieDirty,
          promo: {},
        };
        for (const p of PROVIDER_KEYS) {
          this.form.promo[p] = { passcode: '', link: '', qrUrl: '', ...(promo[p] || {}) };
        }
      }
      if (r2.code === 0) this.dailyPwd = r2.data || null;
    },
    async runDailyPassword() {
      this.pwdRunning = true;
      this.dailyPwdMsg = '';
      const r = await this.api('/api/admin/daily-password/run', { method: 'POST' });
      if (r.code === 0) {
        this.dailyPwdMsg = '已触发生成，约 10-30 秒后刷新查看结果…';
        // 轮询直到生成完成或超时
        for (let i = 0; i < 12; i++) {
          await new Promise((res) => setTimeout(res, 3000));
          const s = await this.api('/api/admin/daily-password');
          if (s.code === 0 && s.data) { this.dailyPwd = s.data; this.dailyPwdMsg = '✓ 今日密码已生成并分享'; break; }
        }
      } else {
        this.dailyPwdMsg = '触发失败：' + (r.msg || '');
      }
      this.pwdRunning = false;
    },
    async saveSettings() {
      this.saved = false;
      const body = {
        cookies: {},
        clearCookies: [],
        promo: {},
      };
      for (const p of PROVIDER_KEYS) {
        // 输入框有内容 → 更新；勾选了「清除」→ 显式清除；否则保持原值
        if (this.form.cookies[p] && this.form.cookies[p].trim()) body.cookies[p] = this.form.cookies[p].trim();
        else if (this.form.cookieDirty[p] && this.form.cookieConfigured[p]) body.clearCookies.push(p);
        body.promo[p] = {
          passcode: this.form.promo[p].passcode || '',
          link: this.form.promo[p].link || '',
          qrUrl: this.form.promo[p].qrUrl || '',
        };
      }
      const r = await this.api('/api/admin/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (r.code === 0) {
        this.saved = true;
        this.loadOverview();
      } else {
        this.err = r.msg || '保存失败';
      }
    },
    async loadLogs() {
      this.tab = 'logs';
      const r = await this.api('/api/admin/logs');
      if (r.code === 0) this.logs = r.data;
    },
    // ===== 任务管理（固定任务位：每个任务位选择网盘口令任务）=====
    async loadTasks() {
      this.tab = 'tasks';
      const r = await this.api('/api/admin/daily-tasks');
      if (r.code === 0) {
        this.tasks = ((r.data && r.data.tasks) || []).map((t) => ({ ...t, providers: Array.isArray(t.providers) ? [...t.providers] : [] }));
      }
    },
    // 保存单个任务位：勾选的网盘 = 完成方式；无勾选 = 停用（enabled=false，前端不展示）
    async saveTaskSlot(t) {
      const task = {
        id: t.id,
        type: t.providers.length ? 'password' : 'answer',
        icon: t.icon || '🎯',
        title: t.title,
        description: t.description,
        reward_type: t.reward_type || 'default',
        reward_count: Number(t.reward_count) || 0,
        reward_provider: t.reward_provider || '',
        providers: [...t.providers],
        answer: t.answer || '',
        enabled: t.providers.length > 0,
      };
      const r = await this.api('/api/admin/daily-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task }),
      });
      if (r.code === 0) {
        t._saved = true;
        t.enabled = task.enabled;
        setTimeout(() => { t._saved = false; }, 1500);
      } else this.err = r.msg || '保存失败';
    },
    async deleteTask(id) {
      if (!confirm('确认删除任务 ' + id + '？')) return;
      const r = await this.api(`/api/admin/daily-tasks/${encodeURIComponent(id)}/delete`, { method: 'POST' });
      if (r.code === 0) this.loadTasks();
      else this.err = r.msg || '删除失败';
    },
  },
}).mount('#app');
}
