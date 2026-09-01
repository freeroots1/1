#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "请用 root 执行：sudo bash deploy/test-public/install-test-on-server.sh 测试域名 证书邮箱"
  exit 1
fi

DOMAIN="${1:-}"
CERT_EMAIL="${2:-}"
if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ ]] || [[ "$DOMAIN" != *.* ]]; then
  echo "用法：sudo bash deploy/test-public/install-test-on-server.sh test.example.com admin@example.com"
  exit 1
fi
if [[ ! "$CERT_EMAIL" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
  echo "请提供用于申请 HTTPS 证书的有效邮箱。"
  exit 1
fi

for command in python3 rsync nginx certbot systemctl curl; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "缺少系统命令：$command"
    exit 1
  fi
done

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="/opt/yaocheng-test"
DATA_DIR="/srv/yaocheng-test"
SERVICE_NAME="yaocheng-test"
NGINX_CONFIG="/etc/nginx/conf.d/yaocheng-test.conf"

echo "准备公网测试版账号和隔离目录..."
if ! id yaochengtest >/dev/null 2>&1; then
  useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin yaochengtest
fi

mkdir -p "$APP_DIR" "$DATA_DIR/data" "$DATA_DIR/backups" "$DATA_DIR/exports" "$DATA_DIR/module-releases"
chown -R yaochengtest:yaochengtest "$DATA_DIR"
chmod 750 "$DATA_DIR" "$DATA_DIR/data" "$DATA_DIR/backups" "$DATA_DIR/exports" "$DATA_DIR/module-releases"

echo "同步测试版代码到 $APP_DIR ..."
rsync -a --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "$SOURCE_ROOT/" "$APP_DIR/"

chown -R root:root "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 755 {} \;
find "$APP_DIR" -type f -exec chmod 644 {} \;
chmod +x "$APP_DIR/deploy/test-public/install-test-on-server.sh"

sed "s#https://example.com#https://$DOMAIN#g" \
  "$APP_DIR/deploy/test-public/yaocheng-test.service.example" \
  > "/etc/systemd/system/$SERVICE_NAME.service"
sed "s#example.com#$DOMAIN#g" \
  "$APP_DIR/deploy/test-public/nginx.conf.example" \
  > "$NGINX_CONFIG"

python3 -m py_compile "$APP_DIR/saas_host/server.py"
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
nginx -t
systemctl reload nginx

echo "申请并启用 HTTPS 证书..."
certbot --nginx -d "$DOMAIN" --redirect --non-interactive --agree-tos --email "$CERT_EMAIL"
nginx -t
systemctl reload nginx

HEALTH="$(curl --fail --silent --show-error "https://$DOMAIN/api/health")"
if [[ "$HEALTH" != *'"deployment": "public-test"'* && "$HEALTH" != *'"deployment":"public-test"'* ]]; then
  echo "公网健康检查未返回 public-test：$HEALTH"
  exit 1
fi

cat <<EOF
曜程独立公网测试版已安装：
https://$DOMAIN

首次启用：
https://$DOMAIN/setup.html

隔离边界：
- 服务：$SERVICE_NAME
- 代码：$APP_DIR
- 数据：$DATA_DIR
- 内部端口：127.0.0.1:8777

请只为测试人员创建测试账号，不要录入正式客户或未成年人真实信息。
EOF
