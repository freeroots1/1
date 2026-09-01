# 曜程独立公网测试版

这套配置只用于邀请外部人员测试。它与本机 `8776`、本机测试端 `8777` 以及将来的正式售卖版代码和数据完全独立。

## 隔离方式

- 服务器代码：`/opt/yaocheng-test`
- 服务器数据：`/srv/yaocheng-test`
- systemd 服务：`yaocheng-test`
- 服务器内部端口：`127.0.0.1:8777`
- 健康接口：`deployment=public-test`
- 公网只开放 80/443，8777 不得直接暴露。
- 发布包不包含本机数据库、备份、导出文件或本机账号。

## 需要准备

- 一台具有公网 IP 的 64 位 Linux 云服务器。
- 一个已解析到该服务器的测试域名或子域名，例如 `test.example.com`。
- Python 3.11+、Nginx、Certbot、rsync、curl。
- 云平台安全组和服务器防火墙仅开放 SSH、80、443；SSH 应限制来源并使用密钥登录。

## 生成测试发布包

在本机项目目录执行：

```bash
bash scripts/package-yaocheng-public-test.sh
```

发布包生成在 `output/public-test-release/`，同时生成 SHA-256 校验文件。

## 首次安装

1. 将发布包上传到独立测试服务器并解压。
2. 确认测试域名已解析到服务器公网 IP。
3. 执行：

```bash
sudo bash deploy/test-public/install-test-on-server.sh test.example.com admin@example.com
```

4. 安装完成后打开 `https://测试域名/setup.html` 创建公网测试版唯一平台管理员。
5. 在管理中心创建测试单位和测试账号，只使用虚构数据。

## 验收

- `GET https://测试域名/api/health` 返回 `ok=true`、`mode=saas`、`deployment=public-test`。
- HTTP 自动跳转 HTTPS，浏览器证书有效。
- 管理中心顶部显示“公网测试环境”。
- 测试账号只能看到已授权模块，单日、多日、派车宝均可贯通。
- 浏览器控制台为 0 error / 0 warning。
- 服务器重启后服务自动恢复，测试数据仍在 `/srv/yaocheng-test`。

## 使用边界

- 这是测试环境，不是正式发布工作台已验收的售卖版。
- 测试包只带已构建完成的页面，不包含模块源码；发布工作台生成候选版本不属于公网测试范围。
- 不复制本机正式数据库，不录入正式客户资料、真实财务数据或未成年人个人信息。
- 测试结束后可单独停服或清空测试数据，不影响本机与正式环境。
