from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import urllib.parse
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape


PLATFORM_ROLES = {
    "platform_admin",
    "platform_customer_ops",
    "platform_finance",
    "platform_release_manager",
    "platform_auditor",
}
PLATFORM_ROLE_LABELS = {
    "platform_admin": "超级管理员",
    "platform_customer_ops": "客户开通维护",
    "platform_finance": "财务续费维护",
    "platform_release_manager": "发布管理员",
    "platform_auditor": "只读审计",
}
TENANT_ROLES = {"tenant_admin", "day1_admin", "user", "viewer"}
ROLES = PLATFORM_ROLES | TENANT_ROLES
TENANT_WRITE_ROLES = {"tenant_admin", "day1_admin", "user"}
MODULE_ACCESS_ROLES = {"manager", "editor", "viewer", "none"}
PLATFORM_ROLE_PERMISSIONS = {
    "platform_admin": {
        "platform_overview",
        "read_tenants",
        "read_signup_requests",
        "create_tenant",
        "manage_signup_requests",
        "set_tenant_status",
        "renew_tenant",
        "update_tenant_quota",
        "update_tenant_profile",
        "reset_tenant_accounts",
        "update_tenant_modules",
        "delete_tenant",
        "purge_tenant",
        "read_logs",
        "export_logs",
        "read_releases",
        "manage_releases",
        "manage_module_config",
        "manage_backups",
        "manage_platform_operators",
    },
    "platform_customer_ops": {
        "platform_overview",
        "read_tenants",
        "read_signup_requests",
        "create_tenant",
        "manage_signup_requests",
        "set_tenant_status",
        "update_tenant_profile",
        "reset_tenant_accounts",
        "update_tenant_modules",
        "read_logs",
    },
    "platform_finance": {
        "platform_overview",
        "read_tenants",
        "renew_tenant",
        "update_tenant_quota",
        "read_logs",
    },
    "platform_release_manager": {
        "platform_overview",
        "read_logs",
        "read_releases",
        "manage_releases",
        "manage_module_config",
    },
    "platform_auditor": {
        "platform_overview",
        "read_tenants",
        "read_signup_requests",
        "read_logs",
        "read_releases",
        "export_logs",
    },
}
MODULE_CATALOG = {
    "day1": {
        "name": "单日大研学",
        "description": "一日研学实践活动报价与利润核算",
        "source_entry": "private_host/public/index.html",
        "generated_entry": "saas_host/public/app.html",
        "customer_entry": "/app.html",
        "build_scripts": (
            "scripts/build-day1-private-host.mjs",
            "scripts/build-day1-saas-customer-app.mjs",
        ),
    },
    "multiday": {
        "name": "多日大研学",
        "description": "跨城多日研学逐天餐饮住宿与城际交通核算",
        "source_entry": "module_sources/yanxuebao-cloudbase.html",
        "generated_entry": "saas_host/public/multiday.html",
        "customer_entry": "/multiday.html",
        "build_scripts": ("scripts/build-multiday-saas-customer-app.mjs",),
    },
    "dispatch": {
        "name": "派车宝",
        "description": "班级导入、车辆推荐、人员分配与车长卡",
        "source_entry": "module_sources/paichebao.html",
        "generated_entry": "saas_host/public/dispatch.html",
        "customer_entry": "/dispatch.html",
        "build_scripts": ("scripts/build-dispatch-saas-customer-app.mjs",),
    },
}
MODULE_BUILD_SUPPORT_FILES = ("scripts/saas-commercial-theme.mjs",)
PREPURCHASE_ITEM_SCOPES = {"门票/场地", "门票/场地2", "场地服务全部"}
RESTORE_REQUIRED_TABLES = {
    "tenants",
    "users",
    "signup_requests",
    "customers",
    "suppliers",
    "day1_schemes",
    "day1_supplier_items",
    "prepurchase_ledgers",
    "prepurchase_adjustments",
    "platform_operation_logs",
    "module_release_records",
    "module_configs",
}
RESTORE_REQUIRED_COLUMNS = {
    "tenants": {"id", "name", "status", "expires_at"},
    "users": {"id", "tenant_id", "username", "password_hash", "role", "is_active"},
    "platform_operation_logs": {"id", "action", "details_json", "created_at"},
    "module_release_records": {"id", "module_key", "status", "acceptance_status", "created_at"},
}
BACKUP_SUMMARY_TABLES = {
    "tenants": "tenants",
    "users": "users",
    "customers": "customers",
    "suppliers": "suppliers",
    "day1_schemes": "day1_schemes",
    "module_schemes": "module_schemes",
    "operation_logs": "platform_operation_logs",
    "release_records": "module_release_records",
}
RELEASE_ACCEPTANCE_EVIDENCE_FIELDS = (
    ("customer_login", "客户登录"),
    ("save", "保存"),
    ("load", "调出"),
    ("print", "打印"),
    ("export", "导出"),
)
SAAS_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)
PLATFORM_ACTION_NAMES = {
    "create_tenant": "开通客户单位",
    "approve_signup_request": "审核通过客户申请",
    "disable_tenant": "停用客户单位",
    "enable_tenant": "启用客户单位",
    "renew_tenant": "续费/延期客户单位",
    "update_tenant_quota": "调整客户用户数",
    "update_tenant_profile": "修改客户资料",
    "delete_tenant": "删除客户单位",
    "purge_tenant": "彻底删除客户数据",
    "reset_tenant_admin_password": "重置客户管理员密码",
    "reset_tenant_user_password": "重置员工密码",
    "disable_tenant_user": "停用员工账号",
    "enable_tenant_user": "启用员工账号",
    "update_tenant_modules": "调整客户模块授权",
    "update_module_config": "更新模块配置",
    "build_module": "生成客户最新版",
    "accept_module_release": "验收模块版本",
    "create_platform_backup": "创建平台备份",
    "restore_platform_backup": "恢复平台备份",
    "change_platform_password": "修改平台管理员密码",
    "create_platform_operator": "创建平台维护人员",
    "update_platform_operator_role": "调整平台维护权限",
    "disable_platform_operator": "停用平台维护人员",
    "enable_platform_operator": "启用平台维护人员",
    "reset_platform_operator_password": "重置平台维护人员密码",
}


@dataclass
class ApiResponse:
    status: int
    body: bytes
    headers: dict[str, str]

    def json(self) -> Any:
        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), f"{salt}${expected}")


class SaaSHostApp:
    def __init__(
        self,
        root: Path | str | None = None,
        *,
        project_root: Path | str | None = None,
        bootstrap_default_admin: bool = False,
        public_url: str | None = None,
        deployment: str | None = None,
        trusted_proxy: bool | None = None,
        session_hours: int | None = None,
    ):
        self.root = Path(root or Path.cwd()).resolve()
        self.project_root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
        self.data_dir = self.root / "data"
        self.backup_dir = self.root / "backups"
        self.export_dir = self.root / "exports"
        self.public_dir = self.project_root / "saas_host" / "public"
        self.module_release_root = self.root / "module-releases"
        self.build_workspace_dir = self.data_dir / "build-workspaces"
        self.db_path = self.data_dir / "yanxuebao_saas.sqlite"
        self.public_url = str(public_url or os.environ.get("YAOCHENG_PUBLIC_URL", "")).strip().rstrip("/")
        inferred_deployment = "online-saas" if self.public_url else "local-development"
        self.deployment = str(
            deployment or os.environ.get("YAOCHENG_DEPLOYMENT", "") or inferred_deployment
        ).strip()
        if self.deployment not in {"local-development", "public-test", "online-saas"}:
            raise ValueError(f"unsupported deployment mode: {self.deployment}")
        self.trusted_proxy = (
            bool(trusted_proxy)
            if trusted_proxy is not None
            else os.environ.get("YAOCHENG_TRUST_PROXY", "").strip().lower() in {"1", "true", "yes"}
        )
        configured_session_hours = session_hours
        if configured_session_hours is None:
            try:
                configured_session_hours = int(os.environ.get("YAOCHENG_SESSION_HOURS", "12"))
            except ValueError:
                configured_session_hours = 12
        self.session_hours = min(168, max(1, int(configured_session_hours)))
        self.sessions: dict[str, dict[str, Any]] = {}
        self._login_attempts: dict[str, list[dt.datetime]] = {}
        self._login_attempts_lock = threading.Lock()
        self._module_build_locks: dict[str, threading.Lock] = {}
        self._module_build_locks_guard = threading.Lock()
        self._setup_lock = threading.Lock()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.module_release_root.mkdir(parents=True, exist_ok=True)
        self.build_workspace_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        if bootstrap_default_admin:
            self._ensure_platform_admin()

    def api_request(
        self,
        method: str,
        path: str,
        token: str | None = None,
        body: Any = None,
        client_key: str | None = None,
        trial_token: str | None = None,
    ) -> ApiResponse:
        method = method.upper()
        parsed = urllib.parse.urlparse(path)
        route = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        try:
            payload = self._decode_body(body)
            if route == "/api/health" and method == "GET":
                return self._json({
                    "ok": True,
                    "mode": "saas",
                    "deployment": self.deployment,
                })
            if route == "/api/setup/status" and method == "GET":
                return self._json({
                    "required": self._setup_required(),
                    "product_name": "曜程",
                    "admin_entry": "/admin.html",
                })
            if route == "/api/setup/initialize" and method == "POST":
                return self._json(self._initialize_setup(payload), 201)
            if route == "/api/login" and method == "POST":
                return self._json(self._login(payload, client_key=client_key))
            if route == "/api/signup-requests" and method == "POST":
                return self._json(self._create_signup_request(payload), 201)
            if route == "/api/signup-requests/current" and method == "GET":
                return self._json(self._public_trial_status(trial_token))
            if route == "/api/signup-requests/enter" and method == "POST":
                return self._json(self._enter_public_trial(trial_token))
            if route == "/api/logout" and method == "POST":
                self._require_user(token)
                self._delete_session(str(token or ""))
                return self._json({"logged_out": True})

            user = self._require_user(token)
            if route == "/api/me" and method == "GET":
                return self._json({"user": self._public_user(user)})
            if route == "/api/me/password" and method == "POST":
                return self._json(self._change_own_password(user, payload))
            if route == "/api/modules" and method == "GET":
                self._require_tenant_user(user)
                return self._json({"items": self._customer_modules(user)})
            if route == "/api/workspace/overview" and method == "GET":
                self._require_tenant_user(user)
                return self._json(self._workspace_overview(user))
            if route == "/api/workspace/schemes" and method == "GET":
                self._require_tenant_user(user)
                return self._json({"items": self._workspace_schemes(user, query)})
            if route.startswith("/api/modules/") and route.endswith("/config") and method == "GET":
                self._require_tenant_user(user)
                module_key = route[len("/api/modules/"):-len("/config")].strip("/")
                self._require_module_access(user, module_key)
                return self._json({"config": self._customer_module_config(module_key, user)})
            if route == "/api/day1/module-config" and method == "GET":
                self._require_tenant_user(user)
                self._require_module_access(user, "day1")
                return self._json({"config": self._day1_customer_module_config()})
            if route == "/api/platform/tenants":
                if method == "GET":
                    self._require_platform_permission(user, "read_tenants")
                    return self._json({"items": self._list_tenants(query)})
                if method == "POST":
                    self._require_platform_permission(user, "create_tenant")
                    return self._json(self._create_tenant(payload, user), 201)
            if route == "/api/platform/signup-requests":
                if method == "GET":
                    self._require_platform_permission(user, "read_signup_requests")
                    return self._json({"items": self._list_signup_requests()})
            if route == "/api/platform/overview" and method == "GET":
                self._require_platform_permission(user, "platform_overview")
                return self._json(self._platform_overview())
            if route == "/api/platform/releases" and method == "GET":
                self._require_platform_permission(user, "read_releases")
                return self._json(self._platform_releases())
            if route == "/api/platform/modules" and method == "GET":
                self._require_platform_permission(user, "read_releases")
                return self._json({"items": [self._module_state(key) for key in MODULE_CATALOG]})
            if route.startswith("/api/platform/modules/"):
                module_route = route[len("/api/platform/modules/"):].strip("/").split("/")
                module_key = module_route[0] if module_route else ""
                self._module_definition(module_key)
                if len(module_route) == 1 and method == "GET":
                    self._require_platform_permission(user, "read_releases")
                    return self._json(self._module_state(module_key))
                if len(module_route) == 2 and module_route[1] == "build" and method == "POST":
                    self._require_platform_permission(user, "manage_releases")
                    return self._json(self._record_catalog_module_build(module_key, user, payload))
                if len(module_route) == 2 and module_route[1] == "config" and method == "PATCH":
                    self._require_platform_permission(user, "manage_module_config")
                    return self._json({"config": self._update_module_config(module_key, payload, user)})
                if (
                    len(module_route) == 4
                    and module_route[1] == "releases"
                    and module_route[3] == "accept"
                    and method == "POST"
                ):
                    self._require_platform_permission(user, "manage_releases")
                    try:
                        release_id = int(module_route[2])
                    except ValueError as exc:
                        raise ApiError(404, "路径无效") from exc
                    return self._json(self._accept_module_release(
                        module_key=module_key,
                        release_id=release_id,
                        user=user,
                        acceptance_payload=payload,
                        online_path=self.project_root / self._module_definition(module_key)["generated_entry"],
                        module_name=self._module_definition(module_key)["name"],
                    ))
            if route == "/api/platform/modules/day1" and method == "GET":
                self._require_platform_permission(user, "read_releases")
                return self._json(self._day1_module_state())
            if route == "/api/platform/modules/day1/build" and method == "POST":
                self._require_platform_permission(user, "manage_releases")
                return self._json(self._record_day1_build(user, payload))
            if route == "/api/platform/modules/day1/config" and method == "PATCH":
                self._require_platform_permission(user, "manage_module_config")
                return self._json({"config": self._update_day1_module_config(payload, user)})
            if route.startswith("/api/platform/modules/day1/releases/") and route.endswith("/accept") and method == "POST":
                self._require_platform_permission(user, "manage_releases")
                release_id = self._route_int(route[:-len("/accept")], "/api/platform/modules/day1/releases/")
                return self._json(self._accept_day1_release(release_id, user, payload))
            if route == "/api/platform/logs" and method == "GET":
                self._require_platform_permission(user, "read_logs")
                return self._json(self._list_platform_logs(query))
            if route == "/api/platform/logs.xlsx" and method == "GET":
                self._require_platform_permission(user, "export_logs")
                data = build_platform_logs_xlsx(self._export_platform_logs(query), self._now())
                filename = f"platform-logs-{self._timestamp()}.xlsx"
                return ApiResponse(
                    200,
                    data,
                    {
                        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "Content-Disposition": f'attachment; filename="{filename}"',
                    },
                )
            if route == "/api/platform/backups":
                self._require_platform_permission(user, "manage_backups")
                if method == "GET":
                    return self._json({"items": self._list_platform_backups()})
                if method == "POST":
                    return self._json(self._create_platform_backup(user), 201)
            if route == "/api/platform/restore" and method == "POST":
                self._require_platform_permission(user, "manage_backups")
                return self._json(self._restore_platform_backup(payload, user))
            if route.startswith("/api/platform/backups/") and method == "GET":
                self._require_platform_permission(user, "manage_backups")
                filename = urllib.parse.unquote(route[len("/api/platform/backups/"):])
                backup = self._read_platform_backup(filename)
                return ApiResponse(
                    200,
                    backup["data"],
                    {
                        "Content-Type": "application/octet-stream",
                        "Content-Disposition": f'attachment; filename="{backup["filename"]}"',
                    },
                )
            if route == "/api/platform/operators":
                self._require_platform_permission(user, "manage_platform_operators")
                if method == "GET":
                    return self._json({"items": self._list_platform_operators()})
                if method == "POST":
                    return self._json(self._create_platform_operator(payload, user), 201)
            if route.startswith("/api/platform/operators/"):
                self._require_platform_permission(user, "manage_platform_operators")
                operator_route = route[len("/api/platform/operators/"):].strip("/").split("/")
                if not operator_route or not operator_route[0]:
                    raise ApiError(404, "路径无效")
                try:
                    operator_id = int(operator_route[0])
                except ValueError as exc:
                    raise ApiError(404, "路径无效") from exc
                if len(operator_route) == 1 and method == "PATCH":
                    return self._json(self._update_platform_operator(operator_id, payload, user))
                if len(operator_route) == 2 and operator_route[1] == "password" and method == "POST":
                    return self._json(self._reset_platform_operator_password(operator_id, payload, user))
                if len(operator_route) == 2 and operator_route[1] == "disable" and method == "POST":
                    return self._json(self._set_platform_operator_active(operator_id, False, user))
                if len(operator_route) == 2 and operator_route[1] == "enable" and method == "POST":
                    return self._json(self._set_platform_operator_active(operator_id, True, user))
            if route.startswith("/api/platform/signup-requests/") and route.endswith("/approve") and method == "POST":
                self._require_platform_permission(user, "manage_signup_requests")
                request_id = self._route_int(route[:-len("/approve")], "/api/platform/signup-requests/")
                return self._json(self._approve_signup_request(request_id, payload, user))
            if route.startswith("/api/platform/signup-requests/") and route.endswith("/reject") and method == "POST":
                self._require_platform_permission(user, "manage_signup_requests")
                request_id = self._route_int(route[:-len("/reject")], "/api/platform/signup-requests/")
                return self._json(self._reject_signup_request(request_id))
            if route.startswith("/api/platform/signup-requests/") and method == "DELETE":
                self._require_platform_permission(user, "manage_signup_requests")
                request_id = self._route_int(route, "/api/platform/signup-requests/")
                return self._json(self._delete_signup_request(request_id))
            if route.startswith("/api/platform/tenants/") and "/users/" in route and method == "POST":
                self._require_platform_permission(user, "reset_tenant_accounts")
                tenant_id, target_user_id, action = self._platform_tenant_user_route(route)
                if action == "password":
                    return self._json(self._reset_platform_tenant_user_password(tenant_id, target_user_id, payload, user))
                if action == "disable":
                    return self._json(self._set_platform_tenant_user_active(tenant_id, target_user_id, False, user))
                if action == "enable":
                    return self._json(self._set_platform_tenant_user_active(tenant_id, target_user_id, True, user))
            if route.startswith("/api/platform/tenants/") and route.endswith("/disable") and method == "POST":
                self._require_platform_permission(user, "set_tenant_status")
                tenant_id = self._route_int(route[:-len("/disable")], "/api/platform/tenants/")
                return self._json(self._disable_tenant(tenant_id, user))
            if route.startswith("/api/platform/tenants/") and route.endswith("/enable") and method == "POST":
                self._require_platform_permission(user, "set_tenant_status")
                tenant_id = self._route_int(route[:-len("/enable")], "/api/platform/tenants/")
                return self._json(self._enable_tenant(tenant_id, user))
            if route.startswith("/api/platform/tenants/") and route.endswith("/renew") and method == "POST":
                self._require_platform_permission(user, "renew_tenant")
                tenant_id = self._route_int(route[:-len("/renew")], "/api/platform/tenants/")
                return self._json(self._renew_tenant(tenant_id, payload, user))
            if route.startswith("/api/platform/tenants/") and route.endswith("/quota") and method == "POST":
                self._require_platform_permission(user, "update_tenant_quota")
                tenant_id = self._route_int(route[:-len("/quota")], "/api/platform/tenants/")
                return self._json(self._update_tenant_quota(tenant_id, payload, user))
            if route.startswith("/api/platform/tenants/") and route.endswith("/admin-password") and method == "POST":
                self._require_platform_permission(user, "reset_tenant_accounts")
                tenant_id = self._route_int(route[:-len("/admin-password")], "/api/platform/tenants/")
                return self._json(self._reset_tenant_admin_password(tenant_id, payload, user))
            if route.startswith("/api/platform/tenants/") and route.endswith("/purge") and method == "POST":
                self._require_platform_permission(user, "purge_tenant")
                tenant_id = self._route_int(route[:-len("/purge")], "/api/platform/tenants/")
                return self._json(self._purge_tenant(tenant_id, payload, user))
            if route.startswith("/api/platform/tenants/") and route.endswith("/modules"):
                tenant_id = self._route_int(route[:-len("/modules")], "/api/platform/tenants/")
                if method == "GET":
                    self._require_platform_permission(user, "read_tenants")
                    return self._json({"items": self._tenant_modules(tenant_id)})
                if method == "PATCH":
                    self._require_platform_permission(user, "update_tenant_modules")
                    return self._json({"items": self._update_tenant_modules(tenant_id, payload, user)})
            if route.startswith("/api/platform/tenants/") and method in {"GET", "PATCH"}:
                tenant_id = self._route_int(route, "/api/platform/tenants/")
                if method == "GET":
                    self._require_platform_permission(user, "read_tenants")
                    return self._json(self._tenant_detail(tenant_id))
                self._require_platform_permission(user, "update_tenant_profile")
                return self._json(self._update_tenant(tenant_id, payload, user))
            if route.startswith("/api/platform/tenants/") and method == "DELETE":
                self._require_platform_permission(user, "delete_tenant")
                tenant_id = self._route_int(route, "/api/platform/tenants/")
                return self._json(self._delete_tenant(tenant_id, payload, user))
            if route == "/api/users":
                self._require_tenant_admin(user)
                if method == "GET":
                    return self._json({"items": self._list_users(user)})
                if method == "POST":
                    return self._json(self._create_user(payload, user), 201)
            if route.startswith("/api/users/") and route.endswith("/password") and method == "POST":
                self._require_tenant_admin(user)
                user_id = self._route_int(route[:-len("/password")], "/api/users/")
                return self._json(self._reset_user_password(user_id, payload, user))
            if route.startswith("/api/users/") and route.endswith("/disable") and method == "POST":
                self._require_tenant_admin(user)
                user_id = self._route_int(route[:-len("/disable")], "/api/users/")
                return self._json(self._set_tenant_user_active(user_id, False, user))
            if route.startswith("/api/users/") and route.endswith("/enable") and method == "POST":
                self._require_tenant_admin(user)
                user_id = self._route_int(route[:-len("/enable")], "/api/users/")
                return self._json(self._set_tenant_user_active(user_id, True, user))
            if route.startswith("/api/users/") and route.endswith("/module-roles"):
                self._require_tenant_admin(user)
                user_id = self._route_int(route[:-len("/module-roles")], "/api/users/")
                if method == "GET":
                    return self._json({"roles": self._user_module_roles(user_id, user)})
                if method == "PATCH":
                    return self._json({"roles": self._update_user_module_roles(user_id, payload, user)})
            if route == "/api/customers":
                self._require_tenant_user(user)
                if method == "GET":
                    return self._json({"items": self._list_customers(user)})
                if method == "POST":
                    self._require_tenant_writer(user)
                    return self._json(self._create_customer(payload, user), 201)
            if route.startswith("/api/customers/"):
                self._require_tenant_user(user)
                customer_id = self._route_int(route, "/api/customers/")
                if method == "PATCH":
                    self._require_shared_library_manager(user)
                    return self._json(self._update_customer(customer_id, payload, user))
                if method == "DELETE":
                    self._require_shared_library_manager(user)
                    return self._json(self._delete_customer(customer_id, user))
            if route == "/api/suppliers":
                self._require_tenant_user(user)
                if method == "GET":
                    return self._json({"items": self._list_suppliers(user)})
                if method == "POST":
                    self._require_tenant_writer(user)
                    return self._json(self._create_supplier(payload, user), 201)
            if route.startswith("/api/suppliers/"):
                self._require_tenant_user(user)
                supplier_id = self._route_int(route, "/api/suppliers/")
                if method == "PATCH":
                    self._require_shared_library_manager(user)
                    return self._json(self._update_supplier(supplier_id, payload, user))
                if method == "DELETE":
                    self._require_shared_library_manager(user)
                    return self._json(self._delete_supplier(supplier_id, user))
            for module_key in ("multiday", "dispatch"):
                module_prefix = f"/api/{module_key}/schemes"
                if route == module_prefix:
                    self._require_module_access(user, module_key)
                    if method == "GET":
                        return self._json({"items": self._list_module_schemes(module_key, user)})
                    if method == "POST":
                        self._require_module_access(user, module_key, write=True)
                        return self._json(self._save_module_scheme(module_key, payload, user), 201)
                if route.startswith(module_prefix + "/"):
                    self._require_module_access(user, module_key)
                    scheme_id = self._route_int(route, module_prefix + "/")
                    if method == "GET":
                        return self._json(self._get_module_scheme(module_key, scheme_id, user))
                    if method == "DELETE":
                        self._require_module_access(user, module_key, manage=True)
                        return self._json(self._delete_module_scheme(module_key, scheme_id, user))
            if route == "/api/day1/schemes":
                self._require_tenant_user(user)
                self._require_module_access(user, "day1")
                if method == "GET":
                    return self._json({"items": self._list_day1_schemes(user)})
                if method == "POST":
                    self._require_module_access(user, "day1", write=True)
                    return self._json(self._save_day1_scheme(payload, user), 201)
            if route.startswith("/api/day1/schemes/"):
                self._require_tenant_user(user)
                self._require_module_access(user, "day1")
                scheme_id = self._route_int(route, "/api/day1/schemes/")
                if method == "GET":
                    return self._json(self._get_day1_scheme(scheme_id, user))
                if method == "DELETE":
                    self._require_day1_manager(user)
                    return self._json(self._delete_day1_scheme(scheme_id, user))
            if route == "/api/supplier-stats" and method == "GET":
                self._require_tenant_user(user)
                return self._json(self._supplier_stats(parsed.query, user))
            if route == "/api/supplier-stats.xlsx" and method == "GET":
                self._require_tenant_user(user)
                stats = self._supplier_stats(parsed.query, user)
                data = build_xlsx(stats["summary"], stats["details"])
                filename = f"supplier-stats-{self._timestamp()}.xlsx"
                (self.export_dir / filename).write_bytes(data)
                return ApiResponse(
                    200,
                    data,
                    {
                        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "Content-Disposition": f'attachment; filename="{filename}"',
                    },
                )
            if route == "/api/prepurchase-ledgers.xlsx" and method == "GET":
                self._require_day1_manager(user)
                ledgers = self._prepurchase_ledgers(query, user)
                data = build_prepurchase_xlsx(ledgers["summary"], ledgers["details"])
                filename = f"prepurchase-ledgers-{self._timestamp()}.xlsx"
                (self.export_dir / filename).write_bytes(data)
                return ApiResponse(
                    200,
                    data,
                    {
                        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "Content-Disposition": f'attachment; filename="{filename}"',
                    },
                )
            if route == "/api/prepurchase-ledgers" and method == "GET":
                self._require_tenant_user(user)
                self._require_module_access(user, "day1")
                return self._json(self._prepurchase_ledgers(query, user))
            if route == "/api/prepurchase-ledgers" and method == "POST":
                self._require_day1_manager(user)
                return self._json(self._create_prepurchase_ledger(payload, user), 201)
            if route.startswith("/api/prepurchase-ledgers/") and route.endswith("/adjustments"):
                self._require_day1_manager(user)
                ledger_id = self._route_int(route[:-len("/adjustments")], "/api/prepurchase-ledgers/")
                if method == "POST":
                    return self._json(self._create_prepurchase_adjustment(ledger_id, payload, user), 201)
            if route.startswith("/api/prepurchase-ledgers/"):
                self._require_day1_manager(user)
                ledger_id = self._route_int(route, "/api/prepurchase-ledgers/")
                if method == "DELETE":
                    return self._json(self._delete_prepurchase_ledger(ledger_id, user))
            raise ApiError(404, "接口不存在")
        except ApiError as exc:
            return self._json({"error": exc.message}, exc.status)
        except Exception as exc:
            return self._json({"error": str(exc)}, 500)

    def serve_static(self, request_path: str) -> ApiResponse:
        parsed = urllib.parse.urlparse(request_path)
        setup_entry_paths = {"/", "/index.html", "/admin.html", "/modules.html", "/workspace.html", "/app.html", "/multiday.html", "/dispatch.html"}
        if parsed.path in setup_entry_paths and self._setup_required():
            return ApiResponse(302, b"", {"Location": "/setup.html", "Cache-Control": "no-store"})
        if parsed.path in {"/", "/index.html"}:
            return ApiResponse(302, b"", {"Location": "/sales.html", "Cache-Control": "no-store"})
        rel = parsed.path.lstrip("/") or "index.html"
        target = (self.public_dir / rel).resolve()
        public_root = self.public_dir.resolve()
        if not str(target).startswith(str(public_root)) or not target.exists() or target.is_dir():
            return self._json({"error": "文件不存在"}, 404)
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        headers = {"Content-Type": content_type, "Cross-Origin-Resource-Policy": "same-origin"}
        if target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
            headers["Content-Type"] = content_type
            headers["Content-Security-Policy"] = SAAS_CONTENT_SECURITY_POLICY
            headers["Cache-Control"] = "no-store"
        elif rel.startswith("vendor/"):
            headers["Cache-Control"] = "public, max-age=604800"
        elif rel.startswith("assets/"):
            headers["Cache-Control"] = "public, max-age=3600"
        return ApiResponse(200, target.read_bytes(), headers)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'active',
                  max_users INTEGER NOT NULL DEFAULT 10,
                  expires_at TEXT NOT NULL DEFAULT '',
                  created_by INTEGER,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER,
                  username TEXT NOT NULL UNIQUE,
                  password_hash TEXT NOT NULL,
                  role TEXT NOT NULL,
                  is_active INTEGER NOT NULL DEFAULT 1,
                  created_by INTEGER,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
                CREATE TABLE IF NOT EXISTS web_sessions (
                  token_hash TEXT PRIMARY KEY,
                  user_id INTEGER NOT NULL,
                  created_at TEXT NOT NULL,
                  expires_at TEXT NOT NULL,
                  last_seen_at TEXT NOT NULL,
                  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_web_sessions_user
                  ON web_sessions(user_id,expires_at);
                CREATE INDEX IF NOT EXISTS idx_web_sessions_expiry
                  ON web_sessions(expires_at);
                CREATE TABLE IF NOT EXISTS signup_requests (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  admin_username TEXT NOT NULL,
                  admin_password_hash TEXT NOT NULL,
                  contact_name TEXT NOT NULL DEFAULT '',
                  contact_phone TEXT NOT NULL DEFAULT '',
                  requested_modules_json TEXT NOT NULL DEFAULT '[]',
                  estimated_users INTEGER NOT NULL DEFAULT 10,
                  notes TEXT NOT NULL DEFAULT '',
                  status TEXT NOT NULL DEFAULT 'pending',
                  approved_tenant_id INTEGER,
                  approved_user_id INTEGER,
                  trial_token_hash TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_signup_requests_status ON signup_requests(status,created_at);
                CREATE TABLE IF NOT EXISTS customers (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  contact TEXT NOT NULL DEFAULT '',
                  phone TEXT NOT NULL DEFAULT '',
                  notes TEXT NOT NULL DEFAULT '',
                  created_by INTEGER,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_customers_tenant ON customers(tenant_id, updated_at);
                CREATE TABLE IF NOT EXISTS suppliers (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  type TEXT NOT NULL DEFAULT '其他',
                  contact TEXT NOT NULL DEFAULT '',
                  phone TEXT NOT NULL DEFAULT '',
                  notes TEXT NOT NULL DEFAULT '',
                  created_by INTEGER,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_suppliers_tenant ON suppliers(tenant_id, updated_at);
                CREATE TABLE IF NOT EXISTS day1_schemes (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER NOT NULL,
                  customer_id INTEGER,
                  customer_name TEXT NOT NULL DEFAULT '',
                  scheme_name TEXT NOT NULL,
                  module_type TEXT NOT NULL DEFAULT 'day1',
                  project_date TEXT NOT NULL,
                  data_json TEXT NOT NULL,
                  supplier_bindings_json TEXT NOT NULL DEFAULT '{}',
                  version INTEGER NOT NULL DEFAULT 1,
                  is_latest INTEGER NOT NULL DEFAULT 1,
                  is_deleted INTEGER NOT NULL DEFAULT 0,
                  created_by INTEGER,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_day1_schemes_tenant_latest
                  ON day1_schemes(tenant_id,is_latest,is_deleted,customer_id,scheme_name);
                CREATE TABLE IF NOT EXISTS day1_supplier_items (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER NOT NULL,
                  scheme_id INTEGER NOT NULL,
                  cost_category TEXT NOT NULL,
                  cost_item TEXT NOT NULL,
                  item_key TEXT NOT NULL,
                  supplier_id INTEGER,
                  supplier_name_snapshot TEXT NOT NULL,
                  supplier_type TEXT NOT NULL,
                  service_target TEXT NOT NULL,
                  quantity REAL NOT NULL DEFAULT 0,
                  unit TEXT NOT NULL DEFAULT '',
                  student_person_times REAL NOT NULL DEFAULT 0,
                  adult_person_times REAL NOT NULL DEFAULT 0,
                  amount REAL NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                  FOREIGN KEY(scheme_id) REFERENCES day1_schemes(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_day1_supplier_items_tenant_scheme
                  ON day1_supplier_items(tenant_id,scheme_id);
                CREATE TABLE IF NOT EXISTS prepurchase_ledgers (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER NOT NULL,
                  year INTEGER NOT NULL,
                  supplier_id INTEGER,
                  supplier_name_snapshot TEXT NOT NULL,
                  supplier_type TEXT NOT NULL DEFAULT '场地',
                  item_scope TEXT NOT NULL DEFAULT '门票/场地',
                  purchased_amount REAL NOT NULL DEFAULT 0,
                  purchased_quantity REAL,
                  quantity_unit TEXT NOT NULL DEFAULT '张',
                  valid_from TEXT,
                  valid_to TEXT,
                  notes TEXT NOT NULL DEFAULT '',
                  is_deleted INTEGER NOT NULL DEFAULT 0,
                  created_by INTEGER,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                  FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_prepurchase_ledgers_tenant_year
                  ON prepurchase_ledgers(tenant_id,year,is_deleted,supplier_id);
                CREATE TABLE IF NOT EXISTS prepurchase_adjustments (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER NOT NULL,
                  ledger_id INTEGER NOT NULL,
                  adjustment_date TEXT NOT NULL,
                  adjustment_type TEXT NOT NULL CHECK(adjustment_type IN ('increase','decrease')),
                  amount REAL NOT NULL DEFAULT 0,
                  quantity REAL,
                  notes TEXT NOT NULL DEFAULT '',
                  created_by INTEGER,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                  FOREIGN KEY(ledger_id) REFERENCES prepurchase_ledgers(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_prepurchase_adjustments_tenant_ledger
                  ON prepurchase_adjustments(tenant_id,ledger_id,adjustment_date);
                CREATE TABLE IF NOT EXISTS platform_operation_logs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  actor_id INTEGER,
                  actor_username TEXT NOT NULL,
                  action TEXT NOT NULL,
                  target_type TEXT NOT NULL,
                  target_id INTEGER,
                  target_name TEXT NOT NULL DEFAULT '',
                  details_json TEXT NOT NULL DEFAULT '{}',
                  created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_platform_operation_logs_created
                  ON platform_operation_logs(created_at,id);
                CREATE TABLE IF NOT EXISTS module_release_records (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  module_key TEXT NOT NULL,
                  module_name TEXT NOT NULL,
                  status TEXT NOT NULL,
                  actor_id INTEGER,
                  actor_username TEXT NOT NULL,
                  build_command TEXT NOT NULL DEFAULT '',
                  generated_entry TEXT NOT NULL DEFAULT '',
                  release_notes TEXT NOT NULL DEFAULT '',
                  output TEXT NOT NULL DEFAULT '',
                  error TEXT NOT NULL DEFAULT '',
                  acceptance_status TEXT NOT NULL DEFAULT '',
                  accepted_by_id INTEGER,
                  accepted_by_username TEXT NOT NULL DEFAULT '',
                  accepted_at TEXT NOT NULL DEFAULT '',
                  candidate_path TEXT NOT NULL DEFAULT '',
                  candidate_sha256 TEXT NOT NULL DEFAULT '',
                  candidate_size INTEGER NOT NULL DEFAULT 0,
                  candidate_generated_at TEXT NOT NULL DEFAULT '',
                  acceptance_evidence_json TEXT NOT NULL DEFAULT '{}',
                  created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_module_release_records_module_created
                  ON module_release_records(module_key,created_at,id);
                CREATE TABLE IF NOT EXISTS module_configs (
                  module_key TEXT PRIMARY KEY,
                  config_json TEXT NOT NULL DEFAULT '{}',
                  updated_by INTEGER,
                  updated_by_username TEXT NOT NULL DEFAULT '',
                  updated_at TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS tenant_modules (
                  tenant_id INTEGER NOT NULL,
                  module_key TEXT NOT NULL,
                  enabled INTEGER NOT NULL DEFAULT 0,
                  updated_by INTEGER,
                  updated_at TEXT NOT NULL DEFAULT '',
                  PRIMARY KEY(tenant_id,module_key),
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_tenant_modules_key_enabled
                  ON tenant_modules(module_key,enabled,tenant_id);
                CREATE TABLE IF NOT EXISTS user_module_roles (
                  user_id INTEGER NOT NULL,
                  tenant_id INTEGER NOT NULL,
                  module_key TEXT NOT NULL,
                  access_role TEXT NOT NULL DEFAULT 'viewer',
                  updated_by INTEGER,
                  updated_at TEXT NOT NULL DEFAULT '',
                  PRIMARY KEY(user_id,module_key),
                  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_user_module_roles_tenant
                  ON user_module_roles(tenant_id,module_key,user_id);
                CREATE TABLE IF NOT EXISTS module_schemes (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER NOT NULL,
                  module_key TEXT NOT NULL,
                  customer_id INTEGER,
                  customer_name TEXT NOT NULL DEFAULT '',
                  scheme_name TEXT NOT NULL,
                  project_date TEXT NOT NULL DEFAULT '',
                  data_json TEXT NOT NULL DEFAULT '{}',
                  supplier_bindings_json TEXT NOT NULL DEFAULT '{}',
                  version INTEGER NOT NULL DEFAULT 1,
                  is_latest INTEGER NOT NULL DEFAULT 1,
                  is_deleted INTEGER NOT NULL DEFAULT 0,
                  created_by INTEGER,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                  FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_module_schemes_tenant_latest
                  ON module_schemes(tenant_id,module_key,is_latest,is_deleted,customer_id,scheme_name);
                CREATE TABLE IF NOT EXISTS module_supplier_items (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER NOT NULL,
                  module_key TEXT NOT NULL,
                  scheme_id INTEGER NOT NULL,
                  cost_category TEXT NOT NULL,
                  cost_item TEXT NOT NULL,
                  item_key TEXT NOT NULL,
                  supplier_id INTEGER,
                  supplier_name_snapshot TEXT NOT NULL,
                  supplier_type TEXT NOT NULL,
                  service_target TEXT NOT NULL,
                  quantity REAL NOT NULL DEFAULT 0,
                  unit TEXT NOT NULL DEFAULT '',
                  student_person_times REAL NOT NULL DEFAULT 0,
                  adult_person_times REAL NOT NULL DEFAULT 0,
                  amount REAL NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                  FOREIGN KEY(scheme_id) REFERENCES module_schemes(id) ON DELETE CASCADE,
                  FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_module_supplier_items_tenant_scheme
                  ON module_supplier_items(tenant_id,module_key,scheme_id);
                """
            )
            self._ensure_column(conn, "module_release_records", "acceptance_status", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "accepted_by_id", "INTEGER")
            self._ensure_column(conn, "module_release_records", "accepted_by_username", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "accepted_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "release_notes", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "candidate_path", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "candidate_sha256", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "candidate_size", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "module_release_records", "candidate_generated_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "acceptance_evidence_json", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "module_schemes", "supplier_bindings_json", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "signup_requests", "contact_name", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "signup_requests", "contact_phone", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "signup_requests", "requested_modules_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "signup_requests", "estimated_users", "INTEGER NOT NULL DEFAULT 10")
            self._ensure_column(conn, "signup_requests", "notes", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "signup_requests", "approved_user_id", "INTEGER")
            self._ensure_column(conn, "signup_requests", "trial_token_hash", "TEXT NOT NULL DEFAULT ''")
            now = self._now()
            conn.execute("DELETE FROM web_sessions WHERE expires_at<=?", (now,))
            conn.execute(
                """
                INSERT OR IGNORE INTO tenant_modules(tenant_id,module_key,enabled,updated_at)
                SELECT id,'day1',1,? FROM tenants
                """,
                (now,),
            )
            for row in conn.execute("SELECT id,expires_at FROM tenants WHERE expires_at<>''").fetchall():
                try:
                    normalized_expiry = normalize_optional_date(row["expires_at"])
                except ApiError:
                    continue
                if normalized_expiry != row["expires_at"]:
                    conn.execute(
                        "UPDATE tenants SET expires_at=?,updated_at=? WHERE id=?",
                        (normalized_expiry, now, row["id"]),
                    )

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ensure_platform_admin(self) -> None:
        now = self._now()
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM users WHERE username=?", ("admin",)).fetchone()
            if row:
                return
            conn.execute(
                """
                INSERT INTO users(tenant_id,username,password_hash,role,is_active,created_at,updated_at)
                VALUES(NULL,?,?,?,?,?,?)
                """,
                ("admin", hash_password("admin123"), "platform_admin", 1, now, now),
            )

    def _setup_required(self) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE role='platform_admin' AND is_active=1 LIMIT 1"
            ).fetchone()
        return row is None

    def _initialize_setup(self, payload: dict[str, Any]) -> dict[str, Any]:
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        if len(username) < 3 or len(username) > 40:
            raise ApiError(400, "平台管理员账号需为 3 到 40 个字符")
        if len(password) < 8:
            raise ApiError(400, "平台管理员密码至少 8 位")
        with self._setup_lock:
            if not self._setup_required():
                raise ApiError(409, "曜程已经完成首次启用")
            now = self._now()
            try:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO users(tenant_id,username,password_hash,role,is_active,created_at,updated_at)
                        VALUES(NULL,?,?,?,?,?,?)
                        """,
                        (username, hash_password(password), "platform_admin", 1, now, now),
                    )
            except sqlite3.IntegrityError as exc:
                raise ApiError(409, "该管理员账号已存在，请更换账号") from exc
        login_result = self._login({"username": username, "password": password})
        return {"initialized": True, **login_result}

    def _login(self, payload: dict[str, Any], client_key: str | None = None) -> dict[str, Any]:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        if not username or not password:
            raise ApiError(400, "请输入账号和密码")
        attempt_key = self._login_attempt_key(client_key, username)
        self._assert_login_attempt_allowed(attempt_key)
        user = self._get_user_by_username(username)
        if not user or not user["is_active"] or not verify_password(password, user["password_hash"]):
            self._record_login_failure(attempt_key)
            raise ApiError(401, "账号或密码错误")
        if user["tenant_id"] is not None:
            tenant = self._get_tenant(int(user["tenant_id"]))
            if not tenant or tenant["status"] != "active":
                self._record_login_failure(attempt_key)
                raise ApiError(403, "客户单位已停用")
            if tenant["expires_at"] and tenant["expires_at"] < self._today():
                self._record_login_failure(attempt_key)
                raise ApiError(403, "客户单位已到期")
        self._clear_login_failures(attempt_key)
        return self._create_user_session(user)

    def _create_user_session(self, user: dict[str, Any]) -> dict[str, Any]:
        token = secrets.token_urlsafe(32)
        session_user = self._session_user(user)
        self.sessions[token] = session_user
        self._persist_session(token, int(user["id"]))
        return {"token": token, "user": self._public_user(session_user)}

    def _login_attempt_key(self, client_key: str | None, username: str) -> str:
        source = str(client_key or "local").strip()[:120] or "local"
        return f"{source}:{username.casefold()}"

    def _assert_login_attempt_allowed(self, attempt_key: str) -> None:
        cutoff = dt.datetime.now() - dt.timedelta(minutes=10)
        with self._login_attempts_lock:
            attempts = [item for item in self._login_attempts.get(attempt_key, []) if item > cutoff]
            self._login_attempts[attempt_key] = attempts
            if len(attempts) >= 5:
                raise ApiError(429, "登录尝试过多，请 10 分钟后再试")

    def _record_login_failure(self, attempt_key: str) -> None:
        with self._login_attempts_lock:
            self._login_attempts.setdefault(attempt_key, []).append(dt.datetime.now())

    def _clear_login_failures(self, attempt_key: str) -> None:
        with self._login_attempts_lock:
            self._login_attempts.pop(attempt_key, None)

    def _session_token_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _persist_session(self, token: str, user_id: int) -> None:
        now = dt.datetime.now().replace(microsecond=0)
        expires_at = now + dt.timedelta(hours=self.session_hours)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO web_sessions(token_hash,user_id,created_at,expires_at,last_seen_at)
                VALUES(?,?,?,?,?)
                """,
                (
                    self._session_token_hash(token),
                    user_id,
                    now.isoformat(sep=" "),
                    expires_at.isoformat(sep=" "),
                    now.isoformat(sep=" "),
                ),
            )

    def _delete_session(self, token: str) -> None:
        self.sessions.pop(token, None)
        if not token:
            return
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM web_sessions WHERE token_hash=?",
                (self._session_token_hash(token),),
            )

    def _clear_all_sessions(self) -> None:
        self.sessions.clear()
        with self._connect() as conn:
            conn.execute("DELETE FROM web_sessions")

    def _create_tenant(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        admin_username = str(payload.get("admin_username", "")).strip()
        admin_password = str(payload.get("admin_password", ""))
        if not name:
            raise ApiError(400, "请输入客户单位名称")
        if not admin_username:
            raise ApiError(400, "请输入客户管理员账号")
        if len(admin_password) < 6:
            raise ApiError(400, "客户管理员密码至少 6 位")
        max_users = int(payload.get("max_users") or 10)
        expires_at = normalize_optional_date(payload.get("expires_at"))
        now = self._now()
        with self._connect() as conn:
            self._assert_username_available(conn, admin_username, "管理员账号已被占用，请换一个账号")
            cur = conn.execute(
                """
                INSERT INTO tenants(name,status,max_users,expires_at,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (name, "active", max_users, expires_at, user["id"], now, now),
            )
            tenant_id = cur.lastrowid
            conn.execute(
                """
                INSERT INTO users(tenant_id,username,password_hash,role,is_active,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (tenant_id, admin_username, hash_password(admin_password), "tenant_admin", 1, user["id"], now, now),
            )
            conn.execute(
                "INSERT OR IGNORE INTO tenant_modules(tenant_id,module_key,enabled,updated_by,updated_at) VALUES(?,?,?,?,?)",
                (tenant_id, "day1", 1, user["id"], now),
            )
        self._write_platform_log(
            "create_tenant",
            "tenant",
            int(tenant_id),
            name,
            user,
            {"admin_username": admin_username, "max_users": max_users, "expires_at": expires_at},
        )
        return {"id": tenant_id, "name": name, "status": "active", "max_users": max_users, "expires_at": expires_at}

    def _list_tenants(self, query: dict[str, list[str]] | None = None) -> list[dict[str, Any]]:
        query = query or {}
        search = query.get("search", [""])[0].strip()
        status = query.get("status", [""])[0].strip()
        expiry = query.get("expiry", [""])[0].strip()
        sort = query.get("sort", [""])[0].strip()
        where = []
        params: list[Any] = []
        if search:
            where.append("t.name LIKE ?")
            params.append(f"%{search}%")
        if status in {"active", "disabled"}:
            where.append("t.status=?")
            params.append(status)
        today = self._today()
        soon = (dt.date.fromisoformat(today) + dt.timedelta(days=30)).isoformat()
        if expiry == "expired":
            where.append("t.expires_at<>'' AND t.expires_at<?")
            params.append(today)
        elif expiry == "soon":
            where.append("t.expires_at<>'' AND t.expires_at>=? AND t.expires_at<=?")
            params.extend([today, soon])
        elif expiry == "none":
            where.append("t.expires_at=''")
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        order_sql = "ORDER BY t.id DESC"
        if sort == "expires_asc":
            order_sql = "ORDER BY (t.expires_at='') ASC,t.expires_at ASC,t.id DESC"
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                  t.id,t.name,t.status,t.max_users,t.expires_at,t.created_at,t.updated_at,
                  COUNT(DISTINCT u.id) AS user_count,
                  COUNT(DISTINCT c.id) AS customer_count,
                  COUNT(DISTINCT sp.id) AS supplier_count,
                  (COUNT(DISTINCT s.id)+COUNT(DISTINCT ms.id)) AS scheme_count,
                  COUNT(DISTINCT l.id) AS prepurchase_ledger_count
                FROM tenants t
                LEFT JOIN users u ON u.tenant_id=t.id AND u.is_active=1
                LEFT JOIN customers c ON c.tenant_id=t.id
                LEFT JOIN suppliers sp ON sp.tenant_id=t.id
                LEFT JOIN day1_schemes s ON s.tenant_id=t.id AND s.module_type='day1' AND s.is_latest=1 AND s.is_deleted=0
                LEFT JOIN module_schemes ms ON ms.tenant_id=t.id AND ms.is_latest=1 AND ms.is_deleted=0
                LEFT JOIN prepurchase_ledgers l ON l.tenant_id=t.id AND l.is_deleted=0
                {where_sql}
                GROUP BY t.id
                {order_sql}
                """,
                params,
            ).fetchall()
        return [self._tenant_list_item(dict(row)) for row in rows]

    def _tenant_list_item(self, item: dict[str, Any]) -> dict[str, Any]:
        expires_at = item.get("expires_at") or ""
        item["days_until_expiry"] = None
        item["expiry_state"] = "未设置"
        if expires_at:
            try:
                days = (dt.date.fromisoformat(expires_at[:10]) - dt.date.fromisoformat(self._today())).days
            except ValueError:
                days = None
            item["days_until_expiry"] = days
            if days is None:
                item["expiry_state"] = "日期异常"
            elif days < 0:
                item["expiry_state"] = "已到期"
            elif days <= 30:
                item["expiry_state"] = "即将到期"
            else:
                item["expiry_state"] = "正常"
        return item

    def _platform_overview(self) -> dict[str, Any]:
        today = self._today()
        soon = (dt.date.fromisoformat(today) + dt.timedelta(days=30)).isoformat()
        with self._connect() as conn:
            tenant_count = conn.execute("SELECT COUNT(*) AS count FROM tenants").fetchone()["count"]
            active_tenant_count = conn.execute(
                "SELECT COUNT(*) AS count FROM tenants WHERE status='active'"
            ).fetchone()["count"]
            disabled_tenant_count = conn.execute(
                "SELECT COUNT(*) AS count FROM tenants WHERE status='disabled'"
            ).fetchone()["count"]
            pending_signup_count = conn.execute(
                "SELECT COUNT(*) AS count FROM signup_requests WHERE status='pending'"
            ).fetchone()["count"]
            expired_tenant_count = conn.execute(
                "SELECT COUNT(*) AS count FROM tenants WHERE expires_at<>'' AND expires_at<?",
                (today,),
            ).fetchone()["count"]
            expiring_soon_count = conn.execute(
                "SELECT COUNT(*) AS count FROM tenants WHERE expires_at<>'' AND expires_at>=? AND expires_at<=?",
                (today, soon),
            ).fetchone()["count"]
        return {
            "tenant_count": tenant_count,
            "active_tenant_count": active_tenant_count,
            "disabled_tenant_count": disabled_tenant_count,
            "pending_signup_count": pending_signup_count,
            "expired_tenant_count": expired_tenant_count,
            "expiring_soon_count": expiring_soon_count,
        }

    def _platform_releases(self) -> dict[str, Any]:
        modules = []
        for key, definition in MODULE_CATALOG.items():
            modules.append({
                "key": key,
                "name": definition["name"],
                "status": "已接入 SaaS" if (self.project_root / definition["generated_entry"]).exists() else "待生成",
                "admin_window": "曜程管理中心 /admin.html",
                "customer_window": f"客户使用页面 {definition['customer_entry']}",
                "edit_source": definition["source_entry"],
                "build_command": " && ".join(f"node {item}" for item in definition["build_scripts"]),
                "release_method": "在发布工作台验收发布后，已获授权的客户刷新模块入口即可使用最新版。",
            })
        return {
            "delivery_model": "saas-central",
            "deployment_mode": "online-saas",
            "phase": "线上 SaaS 首发版",
            "release_window": "曜程管理中心 > 发布工作台",
            "customer_entry": "客户使用入口 /app.html",
            "module_center_entry": "客户模块中心 /modules.html",
            "current_runtime": self.public_url or "统一托管线上 Web 服务（待绑定正式域名）",
            "customer_upgrade_rule": "SaaS 客户打开客户使用入口就是最新版，不需要单独发送安装包或文件。",
            "delivery_rule": "不再以客户安装包作为主售卖方式；我方统一部署、发布、备份和运维，客户使用网址登录。",
            "private_upgrade_rule": "历史私有化流程不再作为主产品路线，仅保留为特殊项目的单独交付能力。",
            "production_boundary": "产品运行于与旧腾讯云业务库分离的独立线上运行环境；对外开放前必须完成正式域名、HTTPS、异机备份、监控和数据托管协议。",
            "handoff_checklist": [
                {"name": "线上服务", "status": "底座已具备", "note": "应用作为统一托管服务运行，不再要求客户启动本机程序。"},
                {"name": "域名与 HTTPS", "status": "待部署配置", "note": "正式域名只指向 Nginx/HTTPS，应用 8776 端口不直接暴露公网。"},
                {"name": "后台维护", "status": "已具备", "note": "平台方在 /admin.html 管理客户、账号、日志、备份和模块升级。"},
                {"name": "客户使用", "status": "已具备", "note": "客户在 /modules.html 进入已开通的三个模块，数据按客户单位隔离。"},
                {"name": "升级发布", "status": "已具备", "note": "发布工作台生成候选产物、验收后统一上线，所有客户刷新后使用新版。"},
                {"name": "备份恢复", "status": "本机备份已具备", "note": "上线时再配置每日自动备份、异机复制和定期恢复演练。"},
                {"name": "运行监控", "status": "待部署配置", "note": "上线时接入服务健康、磁盘、备份、错误日志和证书到期告警。"},
            ],
            "modules": modules,
        }

    def _module_definition(self, module_key: str) -> dict[str, Any]:
        definition = MODULE_CATALOG.get(str(module_key or "").strip())
        if not definition:
            raise ApiError(404, "模块不存在")
        return definition

    def _module_state(self, module_key: str) -> dict[str, Any]:
        definition = self._module_definition(module_key)
        records = self._list_module_release_records(module_key)
        latest_release = records[0] if records else None
        current_release = self._current_module_release(module_key)
        rel_path = Path(definition["generated_entry"])
        path = self.project_root / rel_path
        if path.exists():
            stat = path.stat()
            updated_at = dt.datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0).isoformat(sep=" ")
            file_status = {
                "exists": True,
                "path": str(rel_path),
                "updated_at": updated_at,
                "size": stat.st_size,
                "label": f"已生成，{updated_at}",
            }
        else:
            file_status = {"exists": False, "path": str(rel_path), "updated_at": "", "size": 0, "label": "客户页尚未生成"}
        return {
            "key": module_key,
            "name": definition["name"],
            "description": definition["description"],
            "status": "已接入 SaaS" if path.exists() else "待生成",
            "source_entry": definition["source_entry"],
            "generated_entry": definition["generated_entry"],
            "customer_entry": definition["customer_entry"],
            "admin_entry": "/admin.html",
            "build_command": " && ".join(f"node {item}" for item in definition["build_scripts"]),
            "restart_command": "launchctl kickstart -k gui/$(id -u)/com.day1study.saas",
            "customer_usage": f"获授权客户刷新 {definition['customer_entry']} 使用最新版",
            "maintenance_rule": "每个模块使用独立源文件、候选产物、发布记录和租户授权。",
            "file_status": file_status,
            "latest_version_label": latest_release["version_label"] if latest_release else "暂无生成记录",
            "current_version_label": current_release["version_label"] if current_release else "暂无正式版",
            "config": self._module_config(module_key),
            "latest_release": latest_release,
            "current_release": current_release,
            "release_records": records,
        }

    def _default_module_config(self, module_key: str) -> dict[str, Any]:
        definition = self._module_definition(module_key)
        config = {
            "module_title": definition["name"],
            "customer_entry_label": "客户使用入口" if module_key == "day1" else "进入模块",
        }
        if module_key == "day1":
            config.update({"supplier_stats_enabled": True, "prepurchase_enabled": True})
        return config

    def _module_config(self, module_key: str) -> dict[str, Any]:
        config = self._default_module_config(module_key)
        with self._connect() as conn:
            row = conn.execute("SELECT config_json FROM module_configs WHERE module_key=?", (module_key,)).fetchone()
        if row:
            try:
                saved = json.loads(row["config_json"] or "{}")
            except json.JSONDecodeError:
                saved = {}
            if isinstance(saved, dict):
                for key in config:
                    if key in saved:
                        config[key] = saved[key]
        for key in ("supplier_stats_enabled", "prepurchase_enabled"):
            if key in config:
                config[key] = bool(config[key])
        return config

    def _update_module_config(self, module_key: str, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        current = self._module_config(module_key)
        for key in ("module_title", "customer_entry_label"):
            if key in payload:
                value = str(payload.get(key) or "").strip()
                if not value:
                    raise ApiError(400, "模块配置名称不能为空")
                current[key] = value[:40]
        for key in ("supplier_stats_enabled", "prepurchase_enabled"):
            if key in current and key in payload:
                current[key] = bool(payload.get(key))
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO module_configs(module_key,config_json,updated_by,updated_by_username,updated_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(module_key) DO UPDATE SET
                  config_json=excluded.config_json,updated_by=excluded.updated_by,
                  updated_by_username=excluded.updated_by_username,updated_at=excluded.updated_at
                """,
                (module_key, json.dumps(current, ensure_ascii=False), user.get("id"), user.get("username", ""), now),
            )
        self._write_platform_log("update_module_config", "module", None, self._module_definition(module_key)["name"], user, {"module_key": module_key})
        return current

    def _record_catalog_module_build(self, module_key: str, user: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        definition = self._module_definition(module_key)
        release_notes = str((payload or {}).get("release_notes") or "").strip()[:500]
        if not release_notes:
            raise ApiError(400, "本次更新说明为必填项")
        return self._record_module_build(
            module_key=module_key,
            state=self._module_state(module_key),
            user=user,
            release_notes=release_notes,
            build_scripts=tuple(definition["build_scripts"]),
            generated_path=Path(definition["generated_entry"]),
        )

    def _customer_modules(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        for module_key, definition in MODULE_CATALOG.items():
            access_role = self._module_access_role(user, module_key)
            if access_role == "none":
                continue
            current = self._current_module_release(module_key)
            items.append({
                "key": module_key,
                "name": self._module_config(module_key)["module_title"],
                "description": definition["description"],
                "customer_entry": definition["customer_entry"],
                "access_role": access_role,
                "current_release": self._public_module_release(current),
            })
        return items

    def _workspace_overview(self, user: dict[str, Any]) -> dict[str, Any]:
        module_roles = {
            module_key: self._module_access_role(user, module_key)
            for module_key in MODULE_CATALOG
        }
        visible_modules = [key for key, role in module_roles.items() if role != "none"]
        with self._connect() as conn:
            customer_count = int(conn.execute(
                "SELECT COUNT(*) FROM customers WHERE tenant_id=?",
                (user["tenant_id"],),
            ).fetchone()[0])
            supplier_count = int(conn.execute(
                "SELECT COUNT(*) FROM suppliers WHERE tenant_id=?",
                (user["tenant_id"],),
            ).fetchone()[0])
            day1_count = int(conn.execute(
                """
                SELECT COUNT(*) FROM day1_schemes
                WHERE tenant_id=? AND module_type='day1' AND is_latest=1 AND is_deleted=0
                """,
                (user["tenant_id"],),
            ).fetchone()[0]) if "day1" in visible_modules else 0
            rows = conn.execute(
                """
                SELECT module_key,COUNT(*) AS count
                FROM module_schemes
                WHERE tenant_id=? AND is_latest=1 AND is_deleted=0
                GROUP BY module_key
                """,
                (user["tenant_id"],),
            ).fetchall()
        scheme_counts = {key: 0 for key in visible_modules}
        if "day1" in scheme_counts:
            scheme_counts["day1"] = day1_count
        for row in rows:
            if row["module_key"] in scheme_counts:
                scheme_counts[row["module_key"]] = int(row["count"] or 0)
        return {
            "customer_count": customer_count,
            "supplier_count": supplier_count,
            "scheme_count": sum(scheme_counts.values()),
            "module_scheme_counts": scheme_counts,
            "module_roles": {key: module_roles[key] for key in visible_modules},
            "permissions": {
                "can_create_library": user.get("role") in TENANT_WRITE_ROLES and any(
                    module_roles[key] in {"manager", "editor"} for key in visible_modules
                ),
                "can_manage_library": any(module_roles[key] == "manager" for key in visible_modules),
            },
        }

    def _workspace_schemes(
        self,
        user: dict[str, Any],
        query: dict[str, list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        query = query or {}
        keyword = str(query.get("q", [""])[0]).strip()
        module_filter = str(query.get("module_key", [""])[0]).strip()
        visible_modules = [
            key for key in MODULE_CATALOG
            if self._module_access_role(user, key) != "none"
        ]
        if module_filter:
            visible_modules = [key for key in visible_modules if key == module_filter]
        if not visible_modules:
            return []
        unions: list[str] = []
        params: list[Any] = []
        if "day1" in visible_modules:
            unions.append(
                """
                SELECT 'day1' AS module_key,s.id,s.customer_id,s.customer_name,s.scheme_name,
                       s.project_date,s.version,s.created_at,s.updated_at,u.username AS created_by_name
                FROM day1_schemes s LEFT JOIN users u ON u.id=s.created_by
                WHERE s.tenant_id=? AND s.module_type='day1' AND s.is_latest=1 AND s.is_deleted=0
                """
            )
            params.append(user["tenant_id"])
        generic_modules = [key for key in visible_modules if key != "day1"]
        if generic_modules:
            placeholders = ",".join("?" for _ in generic_modules)
            unions.append(
                f"""
                SELECT s.module_key,s.id,s.customer_id,s.customer_name,s.scheme_name,
                       s.project_date,s.version,s.created_at,s.updated_at,u.username AS created_by_name
                FROM module_schemes s LEFT JOIN users u ON u.id=s.created_by
                WHERE s.tenant_id=? AND s.module_key IN ({placeholders}) AND s.is_latest=1 AND s.is_deleted=0
                """
            )
            params.append(user["tenant_id"])
            params.extend(generic_modules)
        where = []
        if keyword:
            where.append("(customer_name LIKE ? OR scheme_name LIKE ? OR created_by_name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                WITH schemes AS ({' UNION ALL '.join(unions)})
                SELECT * FROM schemes {where_sql}
                ORDER BY project_date DESC,updated_at DESC,id DESC
                """,
                params,
            ).fetchall()
        return [
            dict(row) | {
                "module_name": MODULE_CATALOG[row["module_key"]]["name"],
                "module_entry": MODULE_CATALOG[row["module_key"]]["customer_entry"],
            }
            for row in rows
        ]

    def _customer_module_config(self, module_key: str, user: dict[str, Any]) -> dict[str, Any]:
        config = self._module_config(module_key)
        config["key"] = module_key
        config["customer_entry"] = self._module_definition(module_key)["customer_entry"]
        config["access_role"] = self._module_access_role(user, module_key)
        config["current_release"] = self._public_module_release(self._current_module_release(module_key))
        return config

    def _day1_module_state(self) -> dict[str, Any]:
        records = self._list_module_release_records("day1")
        latest_release = records[0] if records else None
        current_release = self._current_module_release("day1")
        return {
            "key": "day1",
            "name": "单日大研学",
            "status": "已接入 SaaS",
            "source_entry": "private_host/public/index.html",
            "generated_entry": "saas_host/public/app.html",
            "customer_entry": "/app.html",
            "admin_entry": "/admin.html",
            "build_command": "node scripts/build-day1-private-host.mjs && node scripts/build-day1-saas-customer-app.mjs",
            "restart_command": "launchctl kickstart -k gui/$(id -u)/com.day1study.saas",
            "customer_usage": "客户刷新 /app.html 使用最新版",
            "maintenance_rule": "业务功能先改源页面，再生成 SaaS 客户使用页。",
            "file_status": self._day1_generated_file_status(),
            "latest_version_label": latest_release["version_label"] if latest_release else "暂无生成记录",
            "current_version_label": current_release["version_label"] if current_release else "暂无正式版",
            "config": self._day1_module_config(),
            "latest_release": latest_release,
            "current_release": current_release,
            "release_records": records,
        }

    def _day1_generated_file_status(self) -> dict[str, Any]:
        rel_path = Path("saas_host/public/app.html")
        path = self.project_root / rel_path
        if not path.exists():
            return {
                "exists": False,
                "path": str(rel_path),
                "updated_at": "",
                "size": 0,
                "label": "客户页尚未生成",
            }
        stat = path.stat()
        updated_at = dt.datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0).isoformat(sep=" ")
        return {
            "exists": True,
            "path": str(rel_path),
            "updated_at": updated_at,
            "size": stat.st_size,
            "label": f"已生成，{updated_at}",
        }

    def _default_day1_module_config(self) -> dict[str, Any]:
        return {
            "module_title": "单日大研学",
            "customer_entry_label": "客户使用入口",
            "supplier_stats_enabled": True,
            "prepurchase_enabled": True,
        }

    def _day1_module_config(self) -> dict[str, Any]:
        config = self._default_day1_module_config()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT config_json FROM module_configs WHERE module_key='day1'",
            ).fetchone()
        if row:
            try:
                saved = json.loads(row["config_json"])
            except json.JSONDecodeError:
                saved = {}
            for key in config:
                if key in saved:
                    config[key] = saved[key]
        config["supplier_stats_enabled"] = bool(config["supplier_stats_enabled"])
        config["prepurchase_enabled"] = bool(config["prepurchase_enabled"])
        return config

    def _day1_customer_module_config(self) -> dict[str, Any]:
        config = self._day1_module_config()
        current = self._current_module_release("day1")
        config["current_release"] = self._public_module_release(current)
        return config

    def _public_module_release(self, record: dict[str, Any] | None) -> dict[str, Any] | None:
        if not record:
            return None
        return {
            "id": record["id"],
            "version_label": record["version_label"],
            "release_notes": record.get("release_notes", ""),
            "accepted_at": record.get("accepted_at", ""),
        }

    def _update_day1_module_config(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        current = self._day1_module_config()
        for key in ("module_title", "customer_entry_label"):
            if key in payload:
                value = str(payload.get(key) or "").strip()
                if not value:
                    raise ApiError(400, "模块配置名称不能为空")
                current[key] = value[:40]
        for key in ("supplier_stats_enabled", "prepurchase_enabled"):
            if key in payload:
                current[key] = bool(payload.get(key))
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO module_configs(module_key,config_json,updated_by,updated_by_username,updated_at)
                VALUES('day1',?,?,?,?)
                ON CONFLICT(module_key) DO UPDATE SET
                  config_json=excluded.config_json,
                  updated_by=excluded.updated_by,
                  updated_by_username=excluded.updated_by_username,
                  updated_at=excluded.updated_at
                """,
                (json.dumps(current, ensure_ascii=False), user.get("id"), user.get("username", ""), now),
            )
        self._write_platform_log("update_module_config", "module", 1, "单日大研学", user)
        return current

    def _record_day1_build(self, user: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        release_notes = str((payload or {}).get("release_notes") or "").strip()[:500]
        if not release_notes:
            raise ApiError(400, "本次更新说明为必填项")
        return self._record_module_build(
            module_key="day1",
            state=self._day1_module_state(),
            user=user,
            release_notes=release_notes,
            build_scripts=(
                "scripts/build-day1-private-host.mjs",
                "scripts/build-day1-saas-customer-app.mjs",
            ),
            generated_path=Path("saas_host/public/app.html"),
        )

    def _record_module_build(
        self,
        *,
        module_key: str,
        state: dict[str, Any],
        user: dict[str, Any],
        release_notes: str,
        build_scripts: tuple[str, ...],
        generated_path: Path,
    ) -> dict[str, Any]:
        build_lock = self._module_build_lock(module_key)
        if not build_lock.acquire(blocking=False):
            raise ApiError(409, f"{state['name']}正在构建，请稍后再试")
        try:
            return self._record_module_build_locked(
                module_key=module_key,
                state=state,
                user=user,
                release_notes=release_notes,
                build_scripts=build_scripts,
                generated_path=generated_path,
            )
        finally:
            build_lock.release()

    def _record_module_build_locked(
        self,
        *,
        module_key: str,
        state: dict[str, Any],
        user: dict[str, Any],
        release_notes: str,
        build_scripts: tuple[str, ...],
        generated_path: Path,
    ) -> dict[str, Any]:
        outputs: list[str] = []
        errors: list[str] = []
        candidate: dict[str, Any] | None = None
        try:
            with tempfile.TemporaryDirectory(prefix=f"{module_key}-build-", dir=self.build_workspace_dir) as tmp:
                workspace = Path(tmp)
                self._prepare_module_build_workspace(workspace, build_scripts, module_key)
                (workspace / generated_path).parent.mkdir(parents=True, exist_ok=True)
                for script in build_scripts:
                    result = self._run_build_command([self._node_executable(), script], cwd=workspace)
                    stdout = (result.get("stdout") or "").strip()
                    stderr = (result.get("stderr") or "").strip()
                    if stdout:
                        outputs.append(stdout)
                    if stderr:
                        errors.append(stderr)
                    if int(result.get("returncode") or 0) != 0:
                        self._raise_module_build_failure(
                            state,
                            user,
                            "\n".join(outputs),
                            "\n".join(errors),
                            release_notes,
                        )
                generated = workspace / generated_path
                if not generated.is_file():
                    raise FileNotFoundError(f"隔离构建未生成 {generated_path.as_posix()}")
                candidate = self._persist_module_candidate(module_key, generated)
        except ApiError:
            raise
        except Exception as exc:
            errors.append(str(exc))
            self._raise_module_build_failure(
                state,
                user,
                "\n".join(outputs),
                "\n".join(errors),
                release_notes,
            )

        assert candidate is not None
        output = "\n".join(outputs)
        error = "\n".join(errors)
        try:
            record = self._create_module_release_record(
                state,
                "built",
                user,
                output,
                error,
                release_notes,
                candidate,
            )
        except Exception:
            self._delete_module_candidate(module_key, candidate.get("candidate_path", ""))
            raise
        self._write_platform_log(
            "build_module",
            "module",
            1,
            state["name"],
            user,
            {
                "release_id": record.get("id"),
                "release_notes": release_notes,
                "candidate_path": candidate["candidate_path"],
                "candidate_sha256": candidate["candidate_sha256"],
            },
        )
        return {
            "module": state["key"],
            "status": "built",
            "message": "候选版本已生成，验收前不会影响在线客户页。",
            "id": record.get("id"),
            "version_label": record.get("version_label"),
            "release_notes": release_notes,
            "build_command": state["build_command"],
            "generated_entry": state["generated_entry"],
            "output": output,
            "error": error,
            "candidate_path": candidate["candidate_path"],
            "candidate_sha256": candidate["candidate_sha256"],
            "candidate_size": candidate["candidate_size"],
            "candidate_generated_at": candidate["candidate_generated_at"],
            "rollback_available": True,
        }

    def _module_build_lock(self, module_key: str) -> threading.Lock:
        with self._module_build_locks_guard:
            return self._module_build_locks.setdefault(module_key, threading.Lock())

    def _prepare_module_build_workspace(self, workspace: Path, build_scripts: tuple[str, ...], module_key: str = "day1") -> None:
        for relative in build_scripts:
            source = self.project_root / relative
            if not source.is_file():
                raise FileNotFoundError(f"构建脚本不存在：{relative}")
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for relative in MODULE_BUILD_SUPPORT_FILES:
            source = self.project_root / relative
            if not source.is_file():
                continue
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        definition = MODULE_CATALOG.get(module_key)
        if not definition:
            return
        source_relative = Path(definition["source_entry"])
        source_path = self.project_root / source_relative
        if source_path.is_file():
            target = workspace / source_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
        if module_key == "dispatch":
            vendor_source = self.project_root / "module_sources" / "vendor"
            vendor_target = workspace / "module_sources" / "vendor"
            if vendor_source.is_dir():
                shutil.copytree(vendor_source, vendor_target, dirs_exist_ok=True)

    def _persist_module_candidate(self, module_key: str, generated: Path) -> dict[str, Any]:
        module_dir = self._module_release_dir(module_key)
        module_dir.mkdir(parents=True, exist_ok=True)
        candidate_key = f"{self._timestamp()}-{secrets.token_hex(6)}"
        candidate_dir = module_dir / candidate_key
        candidate_dir.mkdir(parents=True, exist_ok=False)
        candidate_path = candidate_dir / generated.name
        temp_path = candidate_dir / f".{generated.name}-{secrets.token_hex(4)}.tmp"
        try:
            shutil.copyfile(generated, temp_path)
            os.replace(temp_path, candidate_path)
        finally:
            temp_path.unlink(missing_ok=True)
        stat = candidate_path.stat()
        return {
            "candidate_path": candidate_path.relative_to(self.root).as_posix(),
            "candidate_sha256": self._sha256_file(candidate_path),
            "candidate_size": stat.st_size,
            "candidate_generated_at": self._now(),
        }

    def _raise_module_build_failure(
        self,
        state: dict[str, Any],
        user: dict[str, Any],
        output: str,
        error: str,
        release_notes: str,
    ) -> None:
        record = self._create_module_release_record(
            state,
            "failed",
            user,
            output,
            error,
            release_notes,
        )
        self._write_platform_log(
            "build_module_failed",
            "module",
            1,
            state["name"],
            user,
            {"release_id": record.get("id"), "release_notes": release_notes},
        )
        message = error or output or "构建脚本未返回错误详情"
        raise ApiError(500, f"生成客户最新版失败：{message}")

    def _create_module_release_record(
        self,
        state: dict[str, Any],
        status: str,
        user: dict[str, Any],
        output: str,
        error: str,
        release_notes: str,
        candidate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        candidate = candidate or {}
        now = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO module_release_records(
                  module_key,module_name,status,actor_id,actor_username,build_command,
                  generated_entry,release_notes,output,error,candidate_path,candidate_sha256,
                  candidate_size,candidate_generated_at,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    state["key"],
                    state["name"],
                    status,
                    user.get("id"),
                    user.get("username", ""),
                    state["build_command"],
                    state["generated_entry"],
                    release_notes,
                    output,
                    error,
                    str(candidate.get("candidate_path") or ""),
                    str(candidate.get("candidate_sha256") or ""),
                    int(candidate.get("candidate_size") or 0),
                    str(candidate.get("candidate_generated_at") or ""),
                    now,
                ),
            )
            record_id = cur.lastrowid
        records = self._list_module_release_records(state["key"], limit=1)
        return records[0] if records else {"id": record_id}

    def _list_module_release_records(self, module_key: str, limit: int = 8) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id,module_key,module_name,status,actor_id,actor_username,build_command,
                       generated_entry,release_notes,output,error,acceptance_status,accepted_by_id,
                       accepted_by_username,accepted_at,candidate_path,candidate_sha256,
                       candidate_size,candidate_generated_at,acceptance_evidence_json,created_at
                FROM module_release_records
                WHERE module_key=?
                ORDER BY created_at DESC,id DESC
                LIMIT ?
                """,
                (module_key, limit),
            ).fetchall()
        return [self._module_release_item(row) for row in rows]

    def _current_module_release(self, module_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id,module_key,module_name,status,actor_id,actor_username,build_command,
                       generated_entry,release_notes,output,error,acceptance_status,accepted_by_id,
                       accepted_by_username,accepted_at,candidate_path,candidate_sha256,
                       candidate_size,candidate_generated_at,acceptance_evidence_json,created_at
                FROM module_release_records
                WHERE module_key=? AND acceptance_status='accepted'
                ORDER BY accepted_at DESC,id DESC
                LIMIT 1
                """,
                (module_key,),
            ).fetchone()
        return self._module_release_item(row) if row else None

    def _get_module_release(self, module_key: str, release_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id,module_key,module_name,status,actor_id,actor_username,build_command,
                       generated_entry,release_notes,output,error,acceptance_status,accepted_by_id,
                       accepted_by_username,accepted_at,candidate_path,candidate_sha256,
                       candidate_size,candidate_generated_at,acceptance_evidence_json,created_at
                FROM module_release_records
                WHERE module_key=? AND id=?
                """,
                (module_key, release_id),
            ).fetchone()
        return self._module_release_item(row) if row else None

    def _module_release_item(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["version_label"] = f"客户版 #{item['id']}"
        item["release_notes"] = item.get("release_notes") or ""
        item["candidate_path"] = item.get("candidate_path") or ""
        item["candidate_sha256"] = item.get("candidate_sha256") or ""
        item["candidate_size"] = int(item.get("candidate_size") or 0)
        item["candidate_generated_at"] = item.get("candidate_generated_at") or ""
        try:
            evidence = json.loads(item.pop("acceptance_evidence_json", "{}") or "{}")
        except (TypeError, ValueError):
            evidence = {}
        item["acceptance_evidence"] = evidence if isinstance(evidence, dict) else {}
        item["rollback_available"] = self._module_candidate_is_available(item)
        return item

    def _module_candidate_is_available(self, record: dict[str, Any]) -> bool:
        if record.get("status") != "built":
            return False
        try:
            candidate = self._module_candidate_path(record.get("module_key", ""), record.get("candidate_path", ""))
            if not candidate.is_file():
                return False
            expected_sha256 = str(record.get("candidate_sha256") or "")
            expected_size = int(record.get("candidate_size") or 0)
            return bool(
                expected_sha256
                and candidate.stat().st_size == expected_size
                and self._sha256_file(candidate) == expected_sha256
            )
        except (ApiError, OSError, ValueError):
            return False

    def _acceptance_evidence(self, payload: dict[str, Any] | None) -> dict[str, bool]:
        raw = (payload or {}).get("acceptance_evidence")
        raw = raw if isinstance(raw, dict) else {}
        missing = [label for key, label in RELEASE_ACCEPTANCE_EVIDENCE_FIELDS if raw.get(key) is not True]
        if missing:
            raise ApiError(400, f"发布前必须提交并通过五项验收证据，缺少：{'、'.join(missing)}")
        return {key: True for key, _ in RELEASE_ACCEPTANCE_EVIDENCE_FIELDS}

    def _accept_day1_release(
        self,
        release_id: int,
        user: dict[str, Any],
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._accept_module_release(
            module_key="day1",
            release_id=release_id,
            user=user,
            acceptance_payload=payload,
            online_path=self.public_dir / "app.html",
            module_name="单日大研学",
        )

    def _accept_module_release(
        self,
        *,
        module_key: str,
        release_id: int,
        user: dict[str, Any],
        acceptance_payload: dict[str, Any] | None,
        online_path: Path,
        module_name: str,
    ) -> dict[str, Any]:
        record = self._get_module_release(module_key, release_id)
        if not record:
            raise ApiError(404, "发布记录不存在")
        if record["status"] != "built":
            raise ApiError(400, "只有生成成功的版本才能验收")
        acceptance_evidence = self._acceptance_evidence(acceptance_payload)
        candidate = self._module_candidate_path(module_key, record.get("candidate_path", ""))
        if not candidate.is_file():
            raise ApiError(409, "候选产物不存在，不能发布")
        expected_sha256 = str(record.get("candidate_sha256") or "")
        actual_sha256 = self._sha256_file(candidate)
        if not expected_sha256 or actual_sha256 != expected_sha256:
            raise ApiError(409, "候选产物哈希校验失败，不能发布")
        if candidate.stat().st_size != int(record.get("candidate_size") or 0):
            raise ApiError(409, "候选产物字节数校验失败，不能发布")

        online_path.parent.mkdir(parents=True, exist_ok=True)
        publish_temp = online_path.parent / f".{online_path.name}-release-{release_id}-{secrets.token_hex(4)}.tmp"
        previous_temp = online_path.parent / f".{online_path.name}-previous-{release_id}-{secrets.token_hex(4)}.tmp"
        had_previous = online_path.is_file()
        try:
            shutil.copyfile(candidate, publish_temp)
            if self._sha256_file(publish_temp) != expected_sha256:
                raise ApiError(409, "发布临时文件哈希校验失败")
            if had_previous:
                shutil.copyfile(online_path, previous_temp)
            os.replace(publish_temp, online_path)
            try:
                now = self._now()
                with self._connect() as conn:
                    conn.execute(
                        "UPDATE module_release_records SET acceptance_status='' WHERE module_key=?",
                        (module_key,),
                    )
                    conn.execute(
                        """
                        UPDATE module_release_records
                        SET acceptance_status='accepted',accepted_by_id=?,accepted_by_username=?,accepted_at=?,
                            acceptance_evidence_json=?
                        WHERE module_key=? AND id=?
                        """,
                        (
                            user.get("id"),
                            user.get("username", ""),
                            now,
                            json.dumps(acceptance_evidence, ensure_ascii=False, sort_keys=True),
                            module_key,
                            release_id,
                        ),
                    )
            except Exception:
                if had_previous and previous_temp.is_file():
                    os.replace(previous_temp, online_path)
                else:
                    online_path.unlink(missing_ok=True)
                raise
        finally:
            publish_temp.unlink(missing_ok=True)
            previous_temp.unlink(missing_ok=True)

        self._write_platform_log(
            "accept_module_release",
            "module",
            release_id,
            module_name,
            user,
            {
                "release_id": release_id,
                "candidate_sha256": expected_sha256,
                "acceptance_evidence": acceptance_evidence,
            },
        )
        accepted = self._get_module_release(module_key, release_id)
        if accepted:
            return accepted
        raise ApiError(404, "发布记录不存在")

    def _module_candidate_path(self, module_key: str, relative_path: str) -> Path:
        module_dir = self._module_release_dir(module_key).resolve()
        if not relative_path:
            return module_dir / "missing-candidate"
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(module_dir)
        except ValueError as exc:
            raise ApiError(409, "候选产物路径无效，不能发布") from exc
        return candidate

    def _module_release_dir(self, module_key: str) -> Path:
        key = str(module_key or "").strip()
        if not key or Path(key).name != key or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in key):
            raise ApiError(400, "模块标识无效")
        return self.module_release_root / key

    def _delete_module_candidate(self, module_key: str, relative_path: str) -> None:
        if not relative_path:
            return
        try:
            candidate = self._module_candidate_path(module_key, relative_path)
        except ApiError:
            return
        candidate.unlink(missing_ok=True)
        try:
            candidate.parent.rmdir()
        except OSError:
            pass

    def _sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _run_build_command(self, command: list[str], cwd: Path | None = None) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                command,
                cwd=Path(cwd or self.project_root),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except FileNotFoundError as exc:
            return {"returncode": 127, "stdout": "", "stderr": str(exc)}
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return {"returncode": 124, "stdout": stdout, "stderr": stderr or "构建超时"}
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _node_executable(self) -> str:
        for candidate in ("/usr/local/bin/node", "/opt/homebrew/bin/node", "/usr/bin/node"):
            if Path(candidate).exists():
                return candidate
        return shutil.which("node") or "node"

    def _list_platform_logs(self, query: dict[str, list[str]]) -> dict[str, Any]:
        page = int(self._num(query.get("page", ["1"])[0]) or 1)
        page = max(1, page)
        page_size = int(self._num(query.get("page_size", query.get("limit", ["30"]))[0]) or 30)
        page_size = max(1, min(page_size, 100))
        where, params = self._platform_log_filter_sql(query)
        offset = (page - 1) * page_size
        with self._connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS count FROM platform_operation_logs{where}",
                params,
            ).fetchone()["count"]
            rows = conn.execute(
                f"""
                SELECT id,actor_id,actor_username,action,target_type,target_id,target_name,details_json,created_at
                FROM platform_operation_logs
                {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, page_size, offset),
            ).fetchall()
        return {"items": self._platform_log_rows(rows), "total": total, "page": page, "page_size": page_size}

    def _export_platform_logs(self, query: dict[str, list[str]]) -> list[dict[str, Any]]:
        where, params = self._platform_log_filter_sql(query)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id,actor_id,actor_username,action,target_type,target_id,target_name,details_json,created_at
                FROM platform_operation_logs
                {where}
                ORDER BY id DESC
                LIMIT 5000
                """,
                params,
            ).fetchall()
        return self._platform_log_rows(rows)

    def _platform_log_filter_sql(self, query: dict[str, list[str]]) -> tuple[str, list[Any]]:
        filters: list[str] = []
        params: list[Any] = []
        action = query.get("action", [""])[0].strip()
        target_type = query.get("target_type", [""])[0].strip()
        keyword = query.get("keyword", [""])[0].strip()
        start_date = query.get("start_date", [""])[0].strip()
        end_date = query.get("end_date", [""])[0].strip()
        if action:
            filters.append("action=?")
            params.append(action)
        if target_type:
            filters.append("target_type=?")
            params.append(target_type)
        if keyword:
            filters.append("(target_name LIKE ? OR actor_username LIKE ? OR action LIKE ?)")
            like = f"%{keyword}%"
            params.extend([like, like, like])
        if start_date:
            filters.append("created_at>=?")
            params.append(normalize_date(start_date) + " 00:00:00")
        if end_date:
            filters.append("created_at<=?")
            params.append(normalize_date(end_date) + " 23:59:59")
        where = " WHERE " + " AND ".join(filters) if filters else ""
        return where, params

    def _platform_log_rows(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        items = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item.pop("details_json") or "{}")
            items.append(item)
        return items

    def _write_platform_log(
        self,
        action: str,
        target_type: str,
        target_id: int | None,
        target_name: str,
        user: dict[str, Any],
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO platform_operation_logs(
                  actor_id,actor_username,action,target_type,target_id,target_name,details_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    user.get("id"),
                    user.get("username", ""),
                    action,
                    target_type,
                    target_id,
                    target_name,
                    json.dumps(details or {}, ensure_ascii=False),
                    self._now(),
                ),
            )

    def _list_platform_backups(self) -> list[dict[str, Any]]:
        backups = []
        for path in sorted(self.backup_dir.glob("saas-backup-*.sqlite"), reverse=True):
            stat = path.stat()
            try:
                validation = self._inspect_platform_backup(path)
            except ApiError as exc:
                validation = {"status": "failed", "message": exc.message}
            backups.append({
                "filename": path.name,
                "size": stat.st_size,
                "created_at": dt.datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0).isoformat(sep=" "),
                "validation": validation,
            })
        return backups

    def _create_platform_backup(
        self,
        user: dict[str, Any],
        *,
        write_log: bool = True,
    ) -> dict[str, Any]:
        filename = f"saas-backup-{self._timestamp()}.sqlite"
        target = self.backup_dir / filename
        source = sqlite3.connect(self.db_path)
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()
        try:
            validation = self._inspect_platform_backup(target, full_integrity=True)
        except ApiError:
            target.unlink(missing_ok=True)
            raise
        stat = target.stat()
        if write_log:
            self._write_platform_log(
                "create_platform_backup",
                "system",
                None,
                "SaaS 数据库备份",
                user,
                {
                    "filename": filename,
                    "size": stat.st_size,
                    "validation": validation,
                },
            )
        return {
            "filename": filename,
            "size": stat.st_size,
            "created_at": dt.datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0).isoformat(sep=" "),
            "validation": validation,
        }

    def _read_platform_backup(self, filename: str) -> dict[str, Any]:
        if "/" in filename or "\\" in filename or not filename.startswith("saas-backup-") or not filename.endswith(".sqlite"):
            raise ApiError(404, "备份文件不存在")
        path = self.backup_dir / filename
        if not path.exists() or not path.is_file():
            raise ApiError(404, "备份文件不存在")
        return {"filename": filename, "data": path.read_bytes()}

    def _restore_platform_backup(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        filename = str(payload.get("filename", "")).strip()
        confirm_text = str(payload.get("confirm_text", "")).strip()
        if confirm_text != "恢复备份":
            raise ApiError(400, "请输入“恢复备份”确认")
        if "/" in filename or "\\" in filename or not filename.startswith("saas-backup-") or not filename.endswith(".sqlite"):
            raise ApiError(404, "备份文件不存在")
        source = self.backup_dir / filename
        if not source.exists() or not source.is_file():
            raise ApiError(404, "备份文件不存在")
        with tempfile.TemporaryDirectory(prefix="restore-check-", dir=self.data_dir) as tmp:
            staged = Path(tmp) / "restore-candidate.sqlite"
            shutil.copy2(source, staged)
            source_validation = self._validate_platform_backup(staged)
            protection = self._create_platform_backup(user, write_log=False)
            os.replace(staged, self.db_path)
        try:
            self._init_db()
            self._clear_all_sessions()
            restored_validation = self._inspect_platform_backup(self.db_path, full_integrity=True)
        except Exception as exc:
            rollback = self.data_dir / f"restore-rollback-{self._timestamp()}.sqlite"
            try:
                shutil.copy2(self.backup_dir / protection["filename"], rollback)
                os.replace(rollback, self.db_path)
                self._init_db()
                self._clear_all_sessions()
            except Exception as rollback_exc:
                rollback.unlink(missing_ok=True)
                raise ApiError(500, f"恢复后校验失败，保护备份回滚也未完成：{rollback_exc}") from exc
            rollback.unlink(missing_ok=True)
            message = exc.message if isinstance(exc, ApiError) else str(exc)
            raise ApiError(500, f"恢复后校验失败，已回滚到保护备份：{message}") from exc
        self._write_platform_log(
            "create_platform_backup",
            "system",
            None,
            "SaaS 数据库备份",
            user,
            {
                "filename": protection["filename"],
                "size": protection["size"],
                "reason": "restore_protection",
                "validation": protection["validation"],
            },
        )
        self._write_platform_log(
            "restore_platform_backup",
            "system",
            None,
            "SaaS 数据库恢复",
            user,
            {
                "filename": filename,
                "protection_backup": protection["filename"],
                "source_validation": source_validation,
                "restored_validation": restored_validation,
            },
        )
        return {
            "restored": filename,
            "protection_backup": protection["filename"],
            "source_validation": source_validation,
            "protection_validation": protection["validation"],
            "restored_validation": restored_validation,
        }

    def _inspect_platform_backup(self, path: Path, *, full_integrity: bool = False) -> dict[str, Any]:
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            pragma = "integrity_check" if full_integrity else "quick_check"
            integrity = [str(row[0]) for row in conn.execute(f"PRAGMA {pragma}").fetchall()]
            if integrity != ["ok"]:
                raise ApiError(400, f"备份数据库完整性校验失败：{'；'.join(integrity)}")
            tables = {
                str(row[0])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            missing_tables = sorted(RESTORE_REQUIRED_TABLES - tables)
            if missing_tables:
                raise ApiError(400, f"备份数据库缺少关键表：{', '.join(missing_tables)}")
            for table, required in RESTORE_REQUIRED_COLUMNS.items():
                columns = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
                missing_columns = sorted(required - columns)
                if missing_columns:
                    raise ApiError(400, f"备份数据库关键表结构不完整：{table}.{', '.join(missing_columns)}")
            core_summary = {
                key: int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) if table in tables else 0
                for key, table in BACKUP_SUMMARY_TABLES.items()
            }
            return {
                "status": "ok",
                "integrity": "ok",
                "table_count": len(tables),
                "core_summary": core_summary,
            }
        except ApiError:
            raise
        except sqlite3.DatabaseError as exc:
            raise ApiError(400, f"备份数据库完整性校验失败：{exc}") from exc
        finally:
            if conn is not None:
                conn.close()

    def _validate_platform_backup(self, path: Path) -> dict[str, Any]:
        self._inspect_platform_backup(path, full_integrity=True)
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            self._ensure_column(conn, "module_release_records", "candidate_path", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "candidate_sha256", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "candidate_size", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "module_release_records", "candidate_generated_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "module_release_records", "acceptance_evidence_json", "TEXT NOT NULL DEFAULT '{}'")
            tables = {
                str(row[0])
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            if "module_schemes" in tables:
                self._ensure_column(conn, "module_schemes", "supplier_bindings_json", "TEXT NOT NULL DEFAULT '{}'")
            conn.commit()
        except ApiError:
            raise
        except sqlite3.DatabaseError as exc:
            raise ApiError(400, f"备份数据库完整性校验失败：{exc}") from exc
        finally:
            if conn is not None:
                conn.close()
        return self._inspect_platform_backup(path, full_integrity=True)

    def _tenant_detail(self, tenant_id: int) -> dict[str, Any]:
        tenant = self._get_tenant(tenant_id)
        if not tenant:
            raise ApiError(404, "客户单位不存在")
        with self._connect() as conn:
            users = conn.execute(
                """
                SELECT id,username,role,is_active,created_at,updated_at
                FROM users
                WHERE tenant_id=?
                ORDER BY CASE role
                  WHEN 'tenant_admin' THEN 1
                  WHEN 'day1_admin' THEN 2
                  WHEN 'user' THEN 3
                  WHEN 'viewer' THEN 4
                  ELSE 5 END, username
                """,
                (tenant_id,),
            ).fetchall()
            recent_schemes = conn.execute(
                """
                SELECT id,customer_name,scheme_name,project_date,version,updated_at
                FROM day1_schemes
                WHERE tenant_id=? AND module_type='day1' AND is_latest=1 AND is_deleted=0
                ORDER BY updated_at DESC,id DESC
                LIMIT 8
                """,
                (tenant_id,),
            ).fetchall()
            recent_logs = conn.execute(
                """
                SELECT id,actor_id,actor_username,action,target_type,target_id,target_name,details_json,created_at
                FROM platform_operation_logs
                WHERE (target_type='tenant' AND target_id=?) OR details_json LIKE ?
                ORDER BY id DESC
                LIMIT 8
                """,
                (tenant_id, f'%"tenant_id": {tenant_id}%'),
            ).fetchall()
        tenant_out = dict(tenant)
        tenant_out.update(self._tenant_counts(tenant_id))
        delete_impact = self._tenant_delete_impact(tenant_id)
        return {
            "tenant": tenant_out,
            "users": [dict(row) for row in users],
            "recent_schemes": [dict(row) for row in recent_schemes],
            "delete_impact": delete_impact,
            "delete_impact_summary": self._tenant_delete_impact_summary(delete_impact),
            "day1_module": self._day1_module_config(),
            "modules": self._tenant_modules(tenant_id),
            "recent_logs": self._platform_log_rows(recent_logs),
        }

    def _tenant_counts(self, tenant_id: int) -> dict[str, int]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM users WHERE tenant_id=? AND is_active=1) AS user_count,
                  (SELECT COUNT(*) FROM customers WHERE tenant_id=?) AS customer_count,
                  (SELECT COUNT(*) FROM suppliers WHERE tenant_id=?) AS supplier_count,
                  ((SELECT COUNT(*) FROM day1_schemes WHERE tenant_id=? AND module_type='day1' AND is_latest=1 AND is_deleted=0)
                   +(SELECT COUNT(*) FROM module_schemes WHERE tenant_id=? AND is_latest=1 AND is_deleted=0)) AS scheme_count,
                  (SELECT COUNT(*) FROM prepurchase_ledgers WHERE tenant_id=? AND is_deleted=0) AS prepurchase_ledger_count
                """,
                (tenant_id, tenant_id, tenant_id, tenant_id, tenant_id, tenant_id),
            ).fetchone()
        return dict(row)

    def _tenant_delete_impact(self, tenant_id: int) -> dict[str, int]:
        impact = self._tenant_counts(tenant_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total_user_count FROM users WHERE tenant_id=?",
                (tenant_id,),
            ).fetchone()
        impact["total_user_count"] = int(row["total_user_count"] if row else 0)
        return impact

    def _tenant_delete_impact_summary(self, impact: dict[str, int]) -> str:
        return (
            f"账号 {int(impact.get('total_user_count') or 0)} 个、"
            f"客户档案 {int(impact.get('customer_count') or 0)} 条、"
            f"供方 {int(impact.get('supplier_count') or 0)} 条、"
            f"方案 {int(impact.get('scheme_count') or 0)} 个、"
            f"预采买台账 {int(impact.get('prepurchase_ledger_count') or 0)} 条"
        )

    def _update_tenant(self, tenant_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        tenant = self._get_tenant(tenant_id)
        if not tenant:
            raise ApiError(404, "客户单位不存在")
        name = str(payload.get("name", tenant["name"])).strip()
        if not name:
            raise ApiError(400, "请输入客户单位名称")
        max_users = int(payload.get("max_users") or tenant["max_users"])
        with self._connect() as conn:
            active_count = conn.execute(
                "SELECT COUNT(*) AS count FROM users WHERE tenant_id=? AND is_active=1",
                (tenant_id,),
            ).fetchone()["count"]
        if max_users < active_count:
            raise ApiError(400, "用户数上限不能小于当前启用账号数")
        expires_at = normalize_optional_date(payload.get("expires_at", tenant["expires_at"]))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tenants
                SET name=?,max_users=?,expires_at=?,updated_at=?
                WHERE id=?
                """,
                (name, max_users, expires_at, self._now(), tenant_id),
            )
        updated = self._get_tenant(tenant_id)
        assert updated is not None
        out = dict(updated)
        out.update(self._tenant_counts(tenant_id))
        self._write_platform_log(
            "update_tenant_profile",
            "tenant",
            tenant_id,
            updated["name"],
            user,
            {
                "old_name": tenant["name"],
                "new_name": updated["name"],
                "old_max_users": tenant["max_users"],
                "new_max_users": updated["max_users"],
                "old_expires_at": tenant.get("expires_at") or "",
                "new_expires_at": updated.get("expires_at") or "",
            },
        )
        return out

    def _reset_tenant_admin_password(self, tenant_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        new_password = str(payload.get("new_password", ""))
        if len(new_password) < 6:
            raise ApiError(400, "新密码至少 6 位")
        tenant = self._get_tenant(tenant_id)
        if not tenant:
            raise ApiError(404, "客户单位不存在")
        with self._connect() as conn:
            admin = conn.execute(
                """
                SELECT id,username FROM users
                WHERE tenant_id=? AND role='tenant_admin' AND is_active=1
                ORDER BY id ASC
                LIMIT 1
                """,
                (tenant_id,),
            ).fetchone()
            if not admin:
                raise ApiError(404, "客户超级管理员不存在")
            conn.execute(
                "UPDATE users SET password_hash=?,updated_at=? WHERE id=?",
                (hash_password(new_password), self._now(), admin["id"]),
            )
        self._write_platform_log(
            "reset_tenant_admin_password",
            "tenant",
            tenant_id,
            tenant["name"],
            user,
            {"admin_username": admin["username"]},
        )
        return {"reset": admin["id"], "username": admin["username"]}

    def _reset_platform_tenant_user_password(
        self,
        tenant_id: int,
        user_id: int,
        payload: dict[str, Any],
        actor: dict[str, Any],
    ) -> dict[str, Any]:
        new_password = str(payload.get("new_password", ""))
        if len(new_password) < 6:
            raise ApiError(400, "新密码至少 6 位")
        target = self._get_tenant_user(tenant_id, user_id)
        if not target:
            raise ApiError(404, "账号不存在")
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET password_hash=?,updated_at=? WHERE id=? AND tenant_id=?",
                (hash_password(new_password), self._now(), user_id, tenant_id),
            )
        self._write_platform_log("reset_tenant_user_password", "user", user_id, target["username"], actor, {"tenant_id": tenant_id})
        return {"reset": user_id, "username": target["username"]}

    def _set_platform_tenant_user_active(
        self,
        tenant_id: int,
        user_id: int,
        active: bool,
        actor: dict[str, Any],
    ) -> dict[str, Any]:
        target = self._get_tenant_user(tenant_id, user_id)
        if not target:
            raise ApiError(404, "账号不存在")
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET is_active=?,updated_at=? WHERE id=? AND tenant_id=?",
                (1 if active else 0, self._now(), user_id, tenant_id),
            )
        if not active:
            self._drop_user_sessions(user_id)
        action = "enable_tenant_user" if active else "disable_tenant_user"
        self._write_platform_log(action, "user", user_id, target["username"], actor, {"tenant_id": tenant_id})
        return {"enabled" if active else "disabled": user_id, "username": target["username"]}

    def _get_tenant_user(self, tenant_id: int, user_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id,tenant_id,username,role,is_active FROM users WHERE id=? AND tenant_id=?",
                (user_id, tenant_id),
            ).fetchone()
        return dict(row) if row else None

    def _create_signup_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        admin_username = str(payload.get("admin_username", "")).strip()
        contact_name = str(payload.get("contact_name", "")).strip()
        contact_phone = " ".join(str(payload.get("contact_phone", "")).split())
        notes = str(payload.get("notes", "")).strip()
        raw_modules = payload.get("requested_modules")
        if not name:
            raise ApiError(400, "请输入客户单位名称")
        if not admin_username:
            raise ApiError(400, "请输入管理员账号")
        if not contact_name:
            raise ApiError(400, "请输入联系人")
        if not contact_phone:
            raise ApiError(400, "请输入联系电话")
        if len(name) > 100:
            raise ApiError(400, "客户单位名称不能超过 100 个字")
        if len(admin_username) > 80:
            raise ApiError(400, "管理员账号不能超过 80 个字")
        if len(contact_name) > 50:
            raise ApiError(400, "联系人不能超过 50 个字")
        if not re.fullmatch(r"[0-9+()\-\s转]{5,30}", contact_phone):
            raise ApiError(400, "请输入有效的联系电话")
        if len(notes) > 500:
            raise ApiError(400, "备注不能超过 500 个字")
        if not isinstance(raw_modules, list):
            raise ApiError(400, "请选择所需模块")
        requested_modules = list(dict.fromkeys(str(item).strip() for item in raw_modules if str(item).strip()))
        unknown_modules = sorted(set(requested_modules) - set(MODULE_CATALOG))
        if unknown_modules:
            raise ApiError(400, f"未知模块：{', '.join(unknown_modules)}")
        if not requested_modules:
            raise ApiError(400, "请至少选择一个所需模块")
        try:
            estimated_users = int(payload.get("estimated_users") or 10)
        except (TypeError, ValueError):
            raise ApiError(400, "预计账号数必须是整数")
        if estimated_users < 1 or estimated_users > 10000:
            raise ApiError(400, "预计账号数必须在 1 到 10000 之间")
        now = self._now()
        trial_token = secrets.token_urlsafe(32) if self.deployment == "public-test" else ""
        trial_token_hash = self._session_token_hash(trial_token) if trial_token else ""
        with self._connect() as conn:
            self._assert_username_available(conn, admin_username, "管理员账号已被占用，请换一个账号")
            cur = conn.execute(
                """
                INSERT INTO signup_requests(
                  name,admin_username,admin_password_hash,contact_name,contact_phone,
                  requested_modules_json,estimated_users,notes,status,trial_token_hash,created_at,updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    name,
                    admin_username,
                    "",
                    contact_name,
                    contact_phone,
                    json.dumps(requested_modules, ensure_ascii=False),
                    estimated_users,
                    notes,
                    "pending",
                    trial_token_hash,
                    now,
                    now,
                ),
            )
            request_id = cur.lastrowid
        return {
            "id": request_id,
            "name": name,
            "admin_username": admin_username,
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "requested_modules": requested_modules,
            "estimated_users": estimated_users,
            "notes": notes,
            "status": "pending",
            "trial_token": trial_token,
        }

    def _list_signup_requests(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id,name,admin_username,contact_name,contact_phone,requested_modules_json,
                       estimated_users,notes,status,approved_tenant_id,created_at,updated_at,
                       CASE WHEN trial_token_hash<>'' THEN 1 ELSE 0 END AS browser_access
                FROM signup_requests
                ORDER BY status DESC,id DESC
                """
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            raw_modules = item.pop("requested_modules_json", "[]")
            try:
                stored_modules = json.loads(raw_modules or "[]")
            except (TypeError, json.JSONDecodeError):
                stored_modules = []
            item["requested_modules"] = [key for key in stored_modules if key in MODULE_CATALOG] or ["day1"]
            items.append(item)
        return items

    def _approve_signup_request(self, request_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        expires_at = normalize_optional_date(payload.get("expires_at"))
        now = self._now()
        with self._connect() as conn:
            request = conn.execute("SELECT * FROM signup_requests WHERE id=?", (request_id,)).fetchone()
            if not request:
                raise ApiError(404, "申请不存在")
            if request["status"] != "pending":
                raise ApiError(400, "申请已处理")
            browser_access = self.deployment == "public-test" and bool(request["trial_token_hash"])
            admin_password = secrets.token_urlsafe(32) if browser_access else str(payload.get("admin_password", ""))
            if len(admin_password) < 6:
                raise ApiError(400, "请设置至少 6 位的客户管理员初始密码")
            try:
                max_users = int(payload.get("max_users") or request["estimated_users"] or 10)
            except (TypeError, ValueError):
                raise ApiError(400, "客户用户数上限必须是整数")
            if max_users < 1 or max_users > 10000:
                raise ApiError(400, "客户用户数上限必须在 1 到 10000 之间")
            try:
                stored_modules = json.loads(request["requested_modules_json"] or "[]")
            except (TypeError, json.JSONDecodeError):
                stored_modules = []
            requested_modules = [key for key in stored_modules if key in MODULE_CATALOG] or ["day1"]
            self._assert_username_available(
                conn,
                request["admin_username"],
                "管理员账号已被占用，请让客户换一个账号后重新提交申请",
            )
            cur = conn.execute(
                """
                INSERT INTO tenants(name,status,max_users,expires_at,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (request["name"], "active", max_users, expires_at, user["id"], now, now),
            )
            tenant_id = cur.lastrowid
            user_cur = conn.execute(
                """
                INSERT INTO users(tenant_id,username,password_hash,role,is_active,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (tenant_id, request["admin_username"], hash_password(admin_password), "tenant_admin", 1, user["id"], now, now),
            )
            approved_user_id = user_cur.lastrowid
            for module_key in MODULE_CATALOG:
                conn.execute(
                    "INSERT INTO tenant_modules(tenant_id,module_key,enabled,updated_by,updated_at) VALUES(?,?,?,?,?)",
                    (tenant_id, module_key, 1 if module_key in requested_modules else 0, user["id"], now),
                )
            conn.execute(
                """
                UPDATE signup_requests
                SET status='approved',approved_tenant_id=?,approved_user_id=?,updated_at=?
                WHERE id=?
                """,
                (tenant_id, approved_user_id, now, request_id),
            )
        self._write_platform_log(
            "approve_signup_request",
            "tenant",
            int(tenant_id),
            request["name"],
            user,
            {
                "signup_request_id": request_id,
                "admin_username": request["admin_username"],
                "max_users": max_users,
                "expires_at": expires_at,
                "requested_modules": requested_modules,
            },
        )
        return {
            "id": request_id,
            "tenant_id": tenant_id,
            "status": "approved",
            "browser_access": browser_access,
        }

    def _public_trial_status(self, trial_token: str | None) -> dict[str, Any]:
        if self.deployment != "public-test":
            raise ApiError(404, "路径不存在")
        if not trial_token:
            return {"tracked": False}
        token_hash = self._session_token_hash(trial_token)
        with self._connect() as conn:
            request = conn.execute(
                """
                SELECT id,name,status,approved_tenant_id,approved_user_id,updated_at
                FROM signup_requests WHERE trial_token_hash=?
                """,
                (token_hash,),
            ).fetchone()
        if not request:
            return {"tracked": False}
        status = str(request["status"])
        can_enter = status == "approved" and bool(request["approved_user_id"])
        return {
            "tracked": True,
            "id": int(request["id"]),
            "name": str(request["name"]),
            "status": status,
            "can_enter": can_enter,
            "updated_at": str(request["updated_at"] or ""),
        }

    def _enter_public_trial(self, trial_token: str | None) -> dict[str, Any]:
        if self.deployment != "public-test":
            raise ApiError(404, "路径不存在")
        if not trial_token:
            raise ApiError(401, "未找到当前浏览器的试用申请")
        token_hash = self._session_token_hash(trial_token)
        with self._connect() as conn:
            request = conn.execute(
                """
                SELECT status,approved_user_id FROM signup_requests WHERE trial_token_hash=?
                """,
                (token_hash,),
            ).fetchone()
            if not request:
                raise ApiError(401, "未找到当前浏览器的试用申请")
            if request["status"] == "pending":
                raise ApiError(409, "试用申请仍在审核中")
            if request["status"] != "approved" or not request["approved_user_id"]:
                raise ApiError(403, "试用申请未通过")
            user = conn.execute(
                "SELECT * FROM users WHERE id=?",
                (request["approved_user_id"],),
            ).fetchone()
        if not user or not user["is_active"]:
            raise ApiError(403, "试用账号已停用")
        user_data = dict(user)
        tenant = self._get_tenant(int(user_data["tenant_id"]))
        if not tenant or tenant["status"] != "active":
            raise ApiError(403, "试用单位已停用")
        if tenant["expires_at"] and tenant["expires_at"] < self._today():
            raise ApiError(403, "试用期限已结束")
        return self._create_user_session(user_data)

    def _reject_signup_request(self, request_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            request = conn.execute("SELECT * FROM signup_requests WHERE id=?", (request_id,)).fetchone()
            if not request:
                raise ApiError(404, "申请不存在")
            if request["status"] != "pending":
                raise ApiError(400, "申请已处理")
            conn.execute(
                "UPDATE signup_requests SET status='rejected',approved_tenant_id=NULL,updated_at=? WHERE id=?",
                (self._now(), request_id),
            )
        return {"id": request_id, "tenant_id": None, "status": "rejected"}

    def _delete_signup_request(self, request_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM signup_requests WHERE id=?", (request_id,))
        if cur.rowcount == 0:
            raise ApiError(404, "申请不存在")
        return {"deleted": request_id}

    def _list_platform_operators(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id,username,role,is_active,created_by,created_at,updated_at
                FROM users
                WHERE tenant_id IS NULL
                ORDER BY CASE role
                  WHEN 'platform_admin' THEN 1
                  WHEN 'platform_customer_ops' THEN 2
                  WHEN 'platform_finance' THEN 3
                  WHEN 'platform_release_manager' THEN 4
                  WHEN 'platform_auditor' THEN 5
                  ELSE 9 END, username
                """
            ).fetchall()
        return [self._platform_operator_item(dict(row)) for row in rows if row["role"] in PLATFORM_ROLES]

    def _platform_operator_item(self, item: dict[str, Any]) -> dict[str, Any]:
        role = str(item.get("role") or "")
        item["role_label"] = PLATFORM_ROLE_LABELS.get(role, role)
        item["permissions"] = sorted(PLATFORM_ROLE_PERMISSIONS.get(role, set()))
        return item

    def _create_platform_operator(self, payload: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        role = str(payload.get("role") or "").strip()
        if len(username) < 3 or len(username) > 40:
            raise ApiError(400, "维护人员账号需为 3 到 40 个字符")
        if len(password) < 8:
            raise ApiError(400, "维护人员初始密码至少 8 位")
        if role not in PLATFORM_ROLES:
            raise ApiError(400, "维护人员角色无效")
        now = self._now()
        with self._connect() as conn:
            self._assert_username_available(conn, username, "维护人员账号已存在，请更换账号")
            cur = conn.execute(
                """
                INSERT INTO users(tenant_id,username,password_hash,role,is_active,created_by,created_at,updated_at)
                VALUES(NULL,?,?,?,?,?,?,?)
                """,
                (username, hash_password(password), role, 1, actor["id"], now, now),
            )
            operator_id = cur.lastrowid
        created = self._get_platform_operator(int(operator_id))
        assert created is not None
        self._write_platform_log(
            "create_platform_operator",
            "platform_operator",
            int(operator_id),
            username,
            actor,
            {"role": role},
        )
        return self._platform_operator_item(created)

    def _update_platform_operator(
        self,
        operator_id: int,
        payload: dict[str, Any],
        actor: dict[str, Any],
    ) -> dict[str, Any]:
        target = self._get_platform_operator(operator_id)
        if not target:
            raise ApiError(404, "维护人员账号不存在")
        role = str(payload.get("role") or "").strip()
        if role not in PLATFORM_ROLES:
            raise ApiError(400, "维护人员角色无效")
        if int(actor.get("id") or 0) == int(operator_id) and role != target["role"]:
            raise ApiError(400, "不能调整当前登录账号自己的权限")
        if target["role"] == "platform_admin" and role != "platform_admin":
            self._assert_another_active_platform_admin(operator_id)
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET role=?,updated_at=? WHERE id=? AND tenant_id IS NULL",
                (role, self._now(), operator_id),
            )
        self._write_platform_log(
            "update_platform_operator_role",
            "platform_operator",
            operator_id,
            target["username"],
            actor,
            {"old_role": target["role"], "new_role": role},
        )
        updated = self._get_platform_operator(operator_id)
        assert updated is not None
        return self._platform_operator_item(updated)

    def _reset_platform_operator_password(
        self,
        operator_id: int,
        payload: dict[str, Any],
        actor: dict[str, Any],
    ) -> dict[str, Any]:
        target = self._get_platform_operator(operator_id)
        if not target:
            raise ApiError(404, "维护人员账号不存在")
        if int(actor.get("id") or 0) == int(operator_id):
            raise ApiError(400, "当前登录账号请使用“修改密码”")
        new_password = str(payload.get("new_password") or "")
        if len(new_password) < 8:
            raise ApiError(400, "新密码至少 8 位")
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET password_hash=?,updated_at=? WHERE id=? AND tenant_id IS NULL",
                (hash_password(new_password), self._now(), operator_id),
            )
        self._drop_user_sessions(operator_id)
        self._write_platform_log(
            "reset_platform_operator_password",
            "platform_operator",
            operator_id,
            target["username"],
            actor,
            {"role": target["role"]},
        )
        return {"reset": operator_id, "username": target["username"]}

    def _set_platform_operator_active(
        self,
        operator_id: int,
        active: bool,
        actor: dict[str, Any],
    ) -> dict[str, Any]:
        target = self._get_platform_operator(operator_id)
        if not target:
            raise ApiError(404, "维护人员账号不存在")
        if int(actor.get("id") or 0) == int(operator_id) and not active:
            raise ApiError(400, "不能停用当前登录账号")
        if target["role"] == "platform_admin" and not active:
            self._assert_another_active_platform_admin(operator_id)
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET is_active=?,updated_at=? WHERE id=? AND tenant_id IS NULL",
                (1 if active else 0, self._now(), operator_id),
            )
        if not active:
            self._drop_user_sessions(operator_id)
        action = "enable_platform_operator" if active else "disable_platform_operator"
        self._write_platform_log(
            action,
            "platform_operator",
            operator_id,
            target["username"],
            actor,
            {"role": target["role"]},
        )
        return {"enabled" if active else "disabled": operator_id, "username": target["username"]}

    def _get_platform_operator(self, operator_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id,username,role,is_active,created_by,created_at,updated_at
                FROM users
                WHERE id=? AND tenant_id IS NULL
                """,
                (operator_id,),
            ).fetchone()
        if not row or row["role"] not in PLATFORM_ROLES:
            return None
        return dict(row)

    def _assert_another_active_platform_admin(self, operator_id: int) -> None:
        with self._connect() as conn:
            count = conn.execute(
                """
                SELECT COUNT(*) AS count FROM users
                WHERE tenant_id IS NULL AND role='platform_admin' AND is_active=1 AND id<>?
                """,
                (operator_id,),
            ).fetchone()["count"]
        if int(count or 0) <= 0:
            raise ApiError(400, "至少需要保留一个启用状态的超级管理员")

    def _disable_tenant(self, tenant_id: int, user: dict[str, Any]) -> dict[str, Any]:
        tenant = self._get_tenant(tenant_id)
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE tenants SET status='disabled',updated_at=? WHERE id=?",
                (self._now(), tenant_id),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "客户单位不存在")
        self._drop_tenant_sessions(tenant_id)
        self._write_platform_log("disable_tenant", "tenant", tenant_id, (tenant or {}).get("name", ""), user)
        return {"disabled": tenant_id}

    def _enable_tenant(self, tenant_id: int, user: dict[str, Any]) -> dict[str, Any]:
        tenant = self._get_tenant(tenant_id)
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE tenants SET status='active',updated_at=? WHERE id=?",
                (self._now(), tenant_id),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "客户单位不存在")
        self._write_platform_log("enable_tenant", "tenant", tenant_id, (tenant or {}).get("name", ""), user)
        return {"enabled": tenant_id}

    def _renew_tenant(self, tenant_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        tenant = self._get_tenant(tenant_id)
        if not tenant:
            raise ApiError(404, "客户单位不存在")
        expires_at = str(payload.get("expires_at", "")).strip()
        if not expires_at:
            raise ApiError(400, "请填写新的到期日期")
        expires_at = normalize_date(expires_at)
        with self._connect() as conn:
            conn.execute(
                "UPDATE tenants SET expires_at=?,updated_at=? WHERE id=?",
                (expires_at, self._now(), tenant_id),
            )
        self._write_platform_log(
            "renew_tenant",
            "tenant",
            tenant_id,
            tenant["name"],
            user,
            {"old_expires_at": tenant.get("expires_at") or "", "new_expires_at": expires_at},
        )
        updated = self._get_tenant(tenant_id)
        assert updated is not None
        out = dict(updated)
        out.update(self._tenant_counts(tenant_id))
        return self._tenant_list_item(out)

    def _update_tenant_quota(self, tenant_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        tenant = self._get_tenant(tenant_id)
        if not tenant:
            raise ApiError(404, "客户单位不存在")
        try:
            max_users = int(payload.get("max_users") or 0)
        except (TypeError, ValueError):
            raise ApiError(400, "用户数上限必须是数字")
        if max_users < 1:
            raise ApiError(400, "用户数上限至少为 1")
        with self._connect() as conn:
            active_count = conn.execute(
                "SELECT COUNT(*) AS count FROM users WHERE tenant_id=? AND is_active=1",
                (tenant_id,),
            ).fetchone()["count"]
            if max_users < active_count:
                raise ApiError(400, "用户数上限不能小于当前启用账号数")
            conn.execute(
                "UPDATE tenants SET max_users=?,updated_at=? WHERE id=?",
                (max_users, self._now(), tenant_id),
            )
        self._write_platform_log(
            "update_tenant_quota",
            "tenant",
            tenant_id,
            tenant["name"],
            user,
            {"old_max_users": tenant.get("max_users"), "new_max_users": max_users},
        )
        updated = self._get_tenant(tenant_id)
        assert updated is not None
        out = dict(updated)
        out.update(self._tenant_counts(tenant_id))
        return self._tenant_list_item(out)

    def _delete_tenant(self, tenant_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        tenant = self._get_tenant(tenant_id)
        if not tenant:
            raise ApiError(404, "客户单位不存在")
        confirm_name = str(payload.get("confirm_name", "")).strip()
        if confirm_name != tenant["name"]:
            raise ApiError(400, "请输入客户单位名称确认删除")
        impact = self._tenant_delete_impact(tenant_id)
        business_total = (
            int(impact.get("customer_count") or 0)
            + int(impact.get("supplier_count") or 0)
            + int(impact.get("scheme_count") or 0)
            + int(impact.get("prepurchase_ledger_count") or 0)
        )
        if business_total > 0:
            raise ApiError(400, "该客户已有业务数据，请先停用客户单位；确需彻底删除时再走高危删除流程")
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM tenants WHERE id=?", (tenant_id,))
        if cur.rowcount == 0:
            raise ApiError(404, "客户单位不存在")
        self._drop_tenant_sessions(tenant_id)
        self._write_platform_log("delete_tenant", "tenant", tenant_id, tenant["name"], user)
        return {"deleted": tenant_id}

    def _purge_tenant(self, tenant_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        tenant = self._get_tenant(tenant_id)
        if not tenant:
            raise ApiError(404, "客户单位不存在")
        confirm_name = str(payload.get("confirm_name", "")).strip()
        confirm_text = str(payload.get("confirm_text", "")).strip()
        if confirm_name != tenant["name"]:
            raise ApiError(400, "请输入客户单位名称确认删除")
        if confirm_text != "彻底删除客户数据":
            raise ApiError(400, "请输入“彻底删除客户数据”确认")
        if tenant["status"] != "disabled":
            raise ApiError(400, "请先停用客户单位，再执行高危彻底删除")
        impact = self._tenant_delete_impact(tenant_id)
        business_total = (
            int(impact.get("customer_count") or 0)
            + int(impact.get("supplier_count") or 0)
            + int(impact.get("scheme_count") or 0)
            + int(impact.get("prepurchase_ledger_count") or 0)
        )
        if business_total <= 0:
            raise ApiError(400, "空客户请使用删除空客户操作")
        protection = self._create_platform_backup(user)
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM tenants WHERE id=?", (tenant_id,))
        if cur.rowcount == 0:
            raise ApiError(404, "客户单位不存在")
        self._drop_tenant_sessions(tenant_id)
        self._write_platform_log(
            "purge_tenant",
            "tenant",
            tenant_id,
            tenant["name"],
            user,
            {"delete_impact": impact, "protection_backup": protection["filename"]},
        )
        return {"purged": tenant_id, "protection_backup": protection["filename"]}

    def _list_users(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id,tenant_id,username,role,is_active,created_at,updated_at
                FROM users
                WHERE tenant_id=?
                ORDER BY role,username
                """,
                (user["tenant_id"],),
            ).fetchall()
        return [dict(row) for row in rows]

    def _change_own_password(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, bool]:
        current_password = str(payload.get("current_password", ""))
        new_password = str(payload.get("new_password", ""))
        if len(new_password) < 6:
            raise ApiError(400, "新密码至少 6 位")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE id=? AND is_active=1",
                (user["id"],),
            ).fetchone()
            if not row:
                raise ApiError(401, "账号不存在或已停用")
            if not verify_password(current_password, row["password_hash"]):
                raise ApiError(400, "当前密码不正确")
            conn.execute(
                "UPDATE users SET password_hash=?,updated_at=? WHERE id=?",
                (hash_password(new_password), self._now(), user["id"]),
            )
        if user["role"] in PLATFORM_ROLES:
            self._write_platform_log(
                "change_platform_password",
                "user",
                user["id"],
                user["username"],
                user,
            )
        return {"changed": True}

    def _reset_user_password(self, user_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, int]:
        new_password = str(payload.get("new_password", ""))
        if len(new_password) < 6:
            raise ApiError(400, "新密码至少 6 位")
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE users SET password_hash=?,updated_at=? WHERE id=? AND tenant_id=?",
                (hash_password(new_password), self._now(), user_id, user["tenant_id"]),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "账号不存在")
        return {"reset": user_id}

    def _set_tenant_user_active(self, user_id: int, active: bool, user: dict[str, Any]) -> dict[str, Any]:
        target = self._get_tenant_user(user["tenant_id"], user_id)
        if not target:
            raise ApiError(404, "账号不存在")
        if not active and int(user_id) == int(user["id"]):
            raise ApiError(400, "不能停用当前登录账号")
        if not active and target["role"] == "tenant_admin":
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM users
                    WHERE tenant_id=? AND role='tenant_admin' AND is_active=1 AND id<>?
                    """,
                    (user["tenant_id"], user_id),
                ).fetchone()
            if int(row["count"] or 0) <= 0:
                raise ApiError(400, "至少保留一个启用的客户超级管理员")
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET is_active=?,updated_at=? WHERE id=? AND tenant_id=?",
                (1 if active else 0, self._now(), user_id, user["tenant_id"]),
            )
        if not active:
            self._drop_user_sessions(user_id)
        return {"enabled" if active else "disabled": user_id, "username": target["username"]}

    def _create_user(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        role = str(payload.get("role", "user")).strip() or "user"
        if role not in {"tenant_admin", "day1_admin", "user", "viewer"}:
            raise ApiError(400, "客户账号角色无效")
        if not username:
            raise ApiError(400, "请输入账号")
        if len(password) < 6:
            raise ApiError(400, "密码至少 6 位")
        self._assert_tenant_user_limit(user)
        now = self._now()
        with self._connect() as conn:
            self._assert_username_available(conn, username, "账号已被占用，请换一个账号")
            cur = conn.execute(
                """
                INSERT INTO users(tenant_id,username,password_hash,role,is_active,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (user["tenant_id"], username, hash_password(password), role, 1, user["id"], now, now),
            )
            user_id = cur.lastrowid
        return {"id": user_id, "tenant_id": user["tenant_id"], "username": username, "role": role}

    def _list_customers(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id,tenant_id,name,contact,phone,notes,created_by,created_at,updated_at
                FROM customers
                WHERE tenant_id=?
                ORDER BY updated_at DESC,id DESC
                """,
                (user["tenant_id"],),
            ).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item["can_delete"] = self._can_manage_shared_library(user)
            item["can_edit"] = self._can_manage_shared_library(user)
        return items

    def _library_fields(self, payload: dict[str, Any], *, entity: str) -> dict[str, str]:
        label = "客户" if entity == "customer" else "供方"
        name = " ".join(str(payload.get("name", "")).split())
        contact = " ".join(str(payload.get("contact", "")).split())
        phone = " ".join(str(payload.get("phone", "")).split())
        notes = str(payload.get("notes", "")).strip()
        if not name:
            raise ApiError(400, f"请输入{label}名称")
        limits = ((name, 100, f"{label}名称"), (contact, 50, "联系人"), (phone, 30, "联系电话"), (notes, 500, "备注"))
        for value, limit, field_label in limits:
            if len(value) > limit:
                raise ApiError(400, f"{field_label}不能超过 {limit} 个字符")
        if phone and (len(phone) < 5 or not re.fullmatch(r"[0-9+()\-\s转]{5,30}", phone)):
            raise ApiError(400, "联系电话格式无效")
        return {"name": name, "contact": contact, "phone": phone, "notes": notes}

    def _assert_library_name_available(
        self,
        conn: sqlite3.Connection,
        table: str,
        tenant_id: int,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> None:
        sql = f"SELECT id FROM {table} WHERE tenant_id=? AND name=? COLLATE NOCASE"
        params: list[Any] = [tenant_id, name]
        if exclude_id is not None:
            sql += " AND id<>?"
            params.append(exclude_id)
        if conn.execute(sql, params).fetchone():
            label = "客户" if table == "customers" else "供方"
            raise ApiError(409, f"同名{label}已存在，请直接使用或修改原档案")

    def _create_customer(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        fields = self._library_fields(payload, entity="customer")
        now = self._now()
        with self._connect() as conn:
            self._assert_library_name_available(conn, "customers", user["tenant_id"], fields["name"])
            cur = conn.execute(
                """
                INSERT INTO customers(tenant_id,name,contact,phone,notes,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    user["tenant_id"],
                    fields["name"],
                    fields["contact"],
                    fields["phone"],
                    fields["notes"],
                    user["id"],
                    now,
                    now,
                ),
            )
            customer_id = cur.lastrowid
        return {"id": customer_id, "tenant_id": user["tenant_id"], "name": fields["name"]}

    def _update_customer(self, customer_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        fields = self._library_fields(payload, entity="customer")
        now = self._now()
        with self._connect() as conn:
            self._assert_library_name_available(
                conn, "customers", user["tenant_id"], fields["name"], exclude_id=customer_id,
            )
            cur = conn.execute(
                """
                UPDATE customers
                SET name=?,contact=?,phone=?,notes=?,updated_at=?
                WHERE id=? AND tenant_id=?
                """,
                (
                    fields["name"],
                    fields["contact"],
                    fields["phone"],
                    fields["notes"],
                    now,
                    customer_id,
                    user["tenant_id"],
                ),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "客户不存在")
        return {"id": customer_id, "tenant_id": user["tenant_id"], "name": fields["name"]}

    def _delete_customer(self, customer_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                "UPDATE day1_schemes SET customer_id=NULL WHERE customer_id=? AND tenant_id=?",
                (customer_id, user["tenant_id"]),
            )
            conn.execute(
                "UPDATE module_schemes SET customer_id=NULL WHERE customer_id=? AND tenant_id=?",
                (customer_id, user["tenant_id"]),
            )
            cur = conn.execute(
                "DELETE FROM customers WHERE id=? AND tenant_id=?",
                (customer_id, user["tenant_id"]),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "客户不存在")
        return {"deleted": customer_id}

    def _list_suppliers(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id,tenant_id,name,type,contact,phone,notes,created_by,created_at,updated_at
                FROM suppliers
                WHERE tenant_id=?
                ORDER BY updated_at DESC,id DESC
                """,
                (user["tenant_id"],),
            ).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item["can_delete"] = self._can_manage_shared_library(user)
            item["can_edit"] = self._can_manage_shared_library(user)
        return items

    def _create_supplier(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        fields = self._library_fields(payload, entity="supplier")
        supplier_type = str(payload.get("type", "其他")).strip() or "其他"
        if len(supplier_type) > 50:
            raise ApiError(400, "供方类型不能超过 50 个字符")
        now = self._now()
        with self._connect() as conn:
            self._assert_library_name_available(conn, "suppliers", user["tenant_id"], fields["name"])
            cur = conn.execute(
                """
                INSERT INTO suppliers(tenant_id,name,type,contact,phone,notes,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    user["tenant_id"],
                    fields["name"],
                    supplier_type,
                    fields["contact"],
                    fields["phone"],
                    fields["notes"],
                    user["id"],
                    now,
                    now,
                ),
            )
            supplier_id = cur.lastrowid
        return {"id": supplier_id, "tenant_id": user["tenant_id"], "name": fields["name"], "type": supplier_type}

    def _update_supplier(self, supplier_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        fields = self._library_fields(payload, entity="supplier")
        supplier_type = str(payload.get("type", "其他")).strip() or "其他"
        if len(supplier_type) > 50:
            raise ApiError(400, "供方类型不能超过 50 个字符")
        now = self._now()
        with self._connect() as conn:
            self._assert_library_name_available(
                conn, "suppliers", user["tenant_id"], fields["name"], exclude_id=supplier_id,
            )
            cur = conn.execute(
                """
                UPDATE suppliers
                SET name=?,type=?,contact=?,phone=?,notes=?,updated_at=?
                WHERE id=? AND tenant_id=?
                """,
                (
                    fields["name"],
                    supplier_type,
                    fields["contact"],
                    fields["phone"],
                    fields["notes"],
                    now,
                    supplier_id,
                    user["tenant_id"],
                ),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "供方不存在")
        return {"id": supplier_id, "tenant_id": user["tenant_id"], "name": fields["name"], "type": supplier_type}

    def _delete_supplier(self, supplier_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                "UPDATE day1_supplier_items SET supplier_id=NULL WHERE supplier_id=? AND tenant_id=?",
                (supplier_id, user["tenant_id"]),
            )
            conn.execute(
                "UPDATE module_supplier_items SET supplier_id=NULL WHERE supplier_id=? AND tenant_id=?",
                (supplier_id, user["tenant_id"]),
            )
            cur = conn.execute(
                "DELETE FROM suppliers WHERE id=? AND tenant_id=?",
                (supplier_id, user["tenant_id"]),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "供方不存在")
        return {"deleted": supplier_id}

    def _create_prepurchase_ledger(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        year = int(self._num(payload.get("year") or dt.date.today().year) or dt.date.today().year)
        if year < 2000 or year > 2100:
            raise ApiError(400, "年度无效")
        supplier_id_raw = payload.get("supplier_id")
        supplier_id = int(supplier_id_raw) if supplier_id_raw not in (None, "", 0, "0") else None
        supplier_name = str(payload.get("supplier_name", "")).strip()
        supplier_type = str(payload.get("supplier_type", "场地")).strip() or "场地"
        if supplier_id:
            supplier = self._get_supplier(supplier_id, user)
            if not supplier:
                raise ApiError(400, "供方不存在")
            supplier_name = supplier["name"]
            supplier_type = supplier["type"]
        if not supplier_name:
            raise ApiError(400, "请选择供方")
        item_scope = str(payload.get("item_scope", "门票/场地")).strip() or "门票/场地"
        if item_scope not in PREPURCHASE_ITEM_SCOPES:
            raise ApiError(400, "适用项目无效")
        purchased_amount = max(0, self._num(payload.get("purchased_amount")))
        if purchased_amount <= 0:
            raise ApiError(400, "采购金额必须大于 0")
        purchased_quantity = self._optional_number(payload.get("purchased_quantity"))
        quantity_unit = str(payload.get("quantity_unit", "张")).strip() or "张"
        valid_from = self._optional_date(payload.get("valid_from"))
        valid_to = self._optional_date(payload.get("valid_to"))
        if valid_from and valid_to and valid_from > valid_to:
            raise ApiError(400, "有效期结束日期不能早于开始日期")
        now = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO prepurchase_ledgers(
                  tenant_id,year,supplier_id,supplier_name_snapshot,supplier_type,item_scope,
                  purchased_amount,purchased_quantity,quantity_unit,valid_from,valid_to,
                  notes,is_deleted,created_by,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    user["tenant_id"],
                    year,
                    supplier_id,
                    supplier_name,
                    supplier_type,
                    item_scope,
                    purchased_amount,
                    purchased_quantity,
                    quantity_unit,
                    valid_from,
                    valid_to,
                    str(payload.get("notes", "")).strip(),
                    0,
                    user["id"],
                    now,
                    now,
                ),
            )
            ledger_id = cur.lastrowid
        return {"id": ledger_id, "year": year, "supplier_id": supplier_id, "supplier_name": supplier_name}

    def _delete_prepurchase_ledger(self, ledger_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE prepurchase_ledgers SET is_deleted=1,updated_at=? WHERE id=? AND tenant_id=?",
                (self._now(), ledger_id, user["tenant_id"]),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "预采买台账不存在")
        return {"deleted": ledger_id}

    def _create_prepurchase_adjustment(self, ledger_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            ledger = conn.execute(
                "SELECT id FROM prepurchase_ledgers WHERE id=? AND tenant_id=? AND is_deleted=0",
                (ledger_id, user["tenant_id"]),
            ).fetchone()
        if not ledger:
            raise ApiError(404, "预采买台账不存在")
        adjustment_type = str(payload.get("adjustment_type", "decrease")).strip() or "decrease"
        if adjustment_type not in {"increase", "decrease"}:
            raise ApiError(400, "调整类型无效")
        amount = max(0, self._num(payload.get("amount")))
        quantity = self._optional_number(payload.get("quantity"))
        if amount <= 0 and (quantity is None or quantity <= 0):
            raise ApiError(400, "调整金额或数量至少填写一项")
        adjustment_date = normalize_date(payload.get("adjustment_date") or self._today())
        now = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO prepurchase_adjustments(
                  tenant_id,ledger_id,adjustment_date,adjustment_type,amount,quantity,notes,created_by,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    user["tenant_id"],
                    ledger_id,
                    adjustment_date,
                    adjustment_type,
                    amount,
                    quantity,
                    str(payload.get("notes", "")).strip(),
                    user["id"],
                    now,
                ),
            )
        return {"id": cur.lastrowid, "ledger_id": ledger_id}

    def _prepurchase_ledgers(self, query: dict[str, list[str]], user: dict[str, Any]) -> dict[str, Any]:
        year = int(self._num(query.get("year", [dt.date.today().year])[0]) or dt.date.today().year)
        supplier_name_filter = query.get("supplier_name", [""])[0].strip()
        where = ["tenant_id=?", "is_deleted=0", "year=?"]
        params: list[Any] = [user["tenant_id"], year]
        if supplier_name_filter:
            where.append("supplier_name_snapshot LIKE ?")
            params.append(f"%{supplier_name_filter}%")
        with self._connect() as conn:
            ledgers = conn.execute(
                f"""
                SELECT * FROM prepurchase_ledgers
                WHERE {" AND ".join(where)}
                ORDER BY supplier_name_snapshot,item_scope,id
                """,
                params,
            ).fetchall()
        summary = []
        details = []
        for row in ledgers:
            ledger = dict(row)
            auto_details = self._prepurchase_auto_details(ledger)
            adjustment_details = self._prepurchase_adjustment_details(ledger)
            auto_amount = sum(float(item["amount"]) for item in auto_details)
            auto_quantity = sum(float(item["quantity"]) for item in auto_details)
            adjustment_amount = 0.0
            adjustment_quantity = 0.0
            for item in adjustment_details:
                sign = 1 if item["adjustment_type"] == "decrease" else -1
                adjustment_amount += sign * float(item["amount"])
                adjustment_quantity += sign * float(item["quantity"] or 0)
            used_amount = auto_amount + adjustment_amount
            purchased_quantity = ledger["purchased_quantity"]
            used_quantity = None if purchased_quantity is None else auto_quantity + adjustment_quantity
            remaining_quantity = None if purchased_quantity is None else float(purchased_quantity) - float(used_quantity or 0)
            purchased_amount = float(ledger["purchased_amount"])
            remaining_amount = purchased_amount - used_amount
            item = {
                "id": ledger["id"],
                "year": ledger["year"],
                "supplier_id": ledger["supplier_id"],
                "supplier_name": ledger["supplier_name_snapshot"],
                "supplier_type": ledger["supplier_type"],
                "item_scope": ledger["item_scope"],
                "purchased_amount": clean_number(purchased_amount),
                "used_amount": clean_number(used_amount),
                "remaining_amount": clean_number(remaining_amount),
                "amount_usage_rate": clean_number((used_amount / purchased_amount * 100) if purchased_amount else 0),
                "purchased_quantity": None if purchased_quantity is None else clean_number(purchased_quantity),
                "used_quantity": None if used_quantity is None else clean_number(used_quantity),
                "remaining_quantity": None if remaining_quantity is None else clean_number(remaining_quantity),
                "quantity_unit": ledger["quantity_unit"],
                "valid_from": ledger["valid_from"] or "",
                "valid_to": ledger["valid_to"] or "",
                "notes": ledger["notes"],
                "can_manage": self._can_manage_day1(user),
            }
            summary.append(item)
            details.extend(auto_details)
            details.extend(adjustment_details)
        return {
            "filters": {"year": year, "supplier_name": supplier_name_filter},
            "summary": summary,
            "details": details,
        }

    def _prepurchase_auto_details(self, ledger: dict[str, Any]) -> list[dict[str, Any]]:
        names = self._prepurchase_item_names(ledger["item_scope"])
        placeholders = ",".join("?" for _ in names)
        where = [
            "s.tenant_id=?",
            "i.tenant_id=?",
            "s.module_type='day1'",
            "s.is_latest=1",
            "s.is_deleted=0",
            "i.cost_category='场地服务'",
            f"i.cost_item IN ({placeholders})",
            "s.project_date>=?",
            "s.project_date<=?",
        ]
        params: list[Any] = [ledger["tenant_id"], ledger["tenant_id"], *names, f"{ledger['year']}-01-01", f"{ledger['year']}-12-31"]
        if ledger.get("valid_from"):
            where.append("s.project_date>=?")
            params.append(ledger["valid_from"])
        if ledger.get("valid_to"):
            where.append("s.project_date<=?")
            params.append(ledger["valid_to"])
        if ledger.get("supplier_id"):
            where.append("i.supplier_id=?")
            params.append(ledger["supplier_id"])
        else:
            where.append("i.supplier_name_snapshot=?")
            params.append(ledger["supplier_name_snapshot"])
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT i.*,s.project_date,s.customer_name,s.scheme_name,u.username AS created_by_name
                FROM day1_supplier_items i
                JOIN day1_schemes s ON s.id=i.scheme_id AND s.tenant_id=i.tenant_id
                LEFT JOIN users u ON u.id=s.created_by
                WHERE {" AND ".join(where)}
                ORDER BY s.project_date ASC,s.id ASC,i.id ASC
                """,
                params,
            ).fetchall()
        return [
            {
                "ledger_id": ledger["id"],
                "date": row["project_date"],
                "customer_name": row["customer_name"],
                "scheme_name": row["scheme_name"],
                "cost_item": row["cost_item"],
                "supplier_name": row["supplier_name_snapshot"],
                "quantity": clean_number(row["quantity"]),
                "unit": row["unit"],
                "amount": clean_number(row["amount"]),
                "source": "方案扣减",
                "created_by": row["created_by_name"] or "",
            }
            for row in rows
        ]

    def _prepurchase_adjustment_details(self, ledger: dict[str, Any]) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT a.*,u.username AS created_by_name
                FROM prepurchase_adjustments a
                LEFT JOIN users u ON u.id=a.created_by
                WHERE a.tenant_id=? AND a.ledger_id=?
                ORDER BY a.adjustment_date ASC,a.id ASC
                """,
                (ledger["tenant_id"], ledger["id"]),
            ).fetchall()
        out = []
        for row in rows:
            out.append(
                {
                    "ledger_id": ledger["id"],
                    "date": row["adjustment_date"],
                    "customer_name": "",
                    "scheme_name": "",
                    "cost_item": row["notes"] or ("手工增加" if row["adjustment_type"] == "increase" else "手工减少"),
                    "supplier_name": ledger["supplier_name_snapshot"],
                    "quantity": clean_number(row["quantity"] or 0),
                    "unit": ledger["quantity_unit"],
                    "amount": clean_number(row["amount"]),
                    "source": "手工调整",
                    "adjustment_type": row["adjustment_type"],
                    "created_by": row["created_by_name"] or "",
                }
            )
        return out

    def _prepurchase_item_names(self, item_scope: str) -> list[str]:
        if item_scope == "门票/场地2":
            return ["门票/场地2"]
        if item_scope == "场地服务全部":
            return ["门票/场地", "门票/场地2"]
        return ["门票/场地"]

    def _tenant_modules(self, tenant_id: int) -> list[dict[str, Any]]:
        if not self._get_tenant(tenant_id):
            raise ApiError(404, "客户单位不存在")
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT module_key,enabled,updated_at FROM tenant_modules WHERE tenant_id=?",
                (tenant_id,),
            ).fetchall()
        stored = {row["module_key"]: dict(row) for row in rows}
        return [
            {
                "key": key,
                "name": definition["name"],
                "enabled": bool(stored.get(key, {}).get("enabled", key == "day1")),
                "customer_entry": definition["customer_entry"],
                "updated_at": stored.get(key, {}).get("updated_at", ""),
            }
            for key, definition in MODULE_CATALOG.items()
        ]

    def _update_tenant_modules(self, tenant_id: int, payload: dict[str, Any], user: dict[str, Any]) -> list[dict[str, Any]]:
        if not self._get_tenant(tenant_id):
            raise ApiError(404, "客户单位不存在")
        raw = payload.get("modules")
        if not isinstance(raw, dict):
            raise ApiError(400, "模块授权数据无效")
        unknown = sorted(set(raw) - set(MODULE_CATALOG))
        if unknown:
            raise ApiError(400, f"未知模块：{', '.join(unknown)}")
        now = self._now()
        with self._connect() as conn:
            for module_key, enabled in raw.items():
                conn.execute(
                    """
                    INSERT INTO tenant_modules(tenant_id,module_key,enabled,updated_by,updated_at)
                    VALUES(?,?,?,?,?)
                    ON CONFLICT(tenant_id,module_key) DO UPDATE SET
                      enabled=excluded.enabled,updated_by=excluded.updated_by,updated_at=excluded.updated_at
                    """,
                    (tenant_id, module_key, 1 if enabled else 0, user.get("id"), now),
                )
        self._write_platform_log(
            "update_tenant_modules",
            "tenant",
            tenant_id,
            self._get_tenant(tenant_id)["name"],
            user,
            {"modules": {key: bool(value) for key, value in raw.items()}},
        )
        self._drop_tenant_sessions(tenant_id)
        return self._tenant_modules(tenant_id)

    def _user_module_roles(self, user_id: int, actor: dict[str, Any]) -> dict[str, str]:
        with self._connect() as conn:
            target = conn.execute("SELECT id,tenant_id,role FROM users WHERE id=? AND tenant_id=?", (user_id, actor["tenant_id"])).fetchone()
            if not target:
                raise ApiError(404, "员工账号不存在")
            rows = conn.execute(
                "SELECT module_key,access_role FROM user_module_roles WHERE user_id=? AND tenant_id=?",
                (user_id, actor["tenant_id"]),
            ).fetchall()
        explicit = {row["module_key"]: row["access_role"] for row in rows}
        return {key: explicit.get(key, self._default_module_access_role(dict(target), key)) for key in MODULE_CATALOG}

    def _update_user_module_roles(self, user_id: int, payload: dict[str, Any], actor: dict[str, Any]) -> dict[str, str]:
        raw = payload.get("roles")
        if not isinstance(raw, dict):
            raise ApiError(400, "模块角色数据无效")
        unknown_modules = sorted(set(raw) - set(MODULE_CATALOG))
        if unknown_modules:
            raise ApiError(400, f"未知模块：{', '.join(unknown_modules)}")
        invalid = sorted({str(value) for value in raw.values()} - MODULE_ACCESS_ROLES)
        if invalid:
            raise ApiError(400, f"未知模块权限：{', '.join(invalid)}")
        with self._connect() as conn:
            target = conn.execute("SELECT id,tenant_id,role FROM users WHERE id=? AND tenant_id=?", (user_id, actor["tenant_id"])).fetchone()
            if not target:
                raise ApiError(404, "员工账号不存在")
            if target["role"] == "tenant_admin":
                raise ApiError(400, "客户超级管理员始终拥有已开通模块的管理权限")
            now = self._now()
            for module_key, access_role in raw.items():
                conn.execute(
                    """
                    INSERT INTO user_module_roles(user_id,tenant_id,module_key,access_role,updated_by,updated_at)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(user_id,module_key) DO UPDATE SET
                      access_role=excluded.access_role,tenant_id=excluded.tenant_id,
                      updated_by=excluded.updated_by,updated_at=excluded.updated_at
                    """,
                    (user_id, actor["tenant_id"], module_key, access_role, actor.get("id"), now),
                )
        self._drop_user_sessions(user_id)
        return self._user_module_roles(user_id, actor)

    def _default_module_access_role(self, user: dict[str, Any], module_key: str) -> str:
        role = user.get("role")
        if role == "tenant_admin":
            return "manager"
        if role == "day1_admin":
            return "manager" if module_key == "day1" else "none"
        if role == "user":
            return "editor"
        if role == "viewer":
            return "viewer"
        return "none"

    def _module_access_role(self, user: dict[str, Any], module_key: str) -> str:
        self._module_definition(module_key)
        tenant_id = user.get("tenant_id")
        if tenant_id is None:
            return "none"
        with self._connect() as conn:
            enabled = conn.execute(
                "SELECT enabled FROM tenant_modules WHERE tenant_id=? AND module_key=?",
                (tenant_id, module_key),
            ).fetchone()
            if not enabled or not enabled["enabled"]:
                return "none"
            explicit = conn.execute(
                "SELECT access_role FROM user_module_roles WHERE user_id=? AND tenant_id=? AND module_key=?",
                (user.get("id"), tenant_id, module_key),
            ).fetchone()
        return explicit["access_role"] if explicit else self._default_module_access_role(user, module_key)

    def _require_module_access(
        self,
        user: dict[str, Any],
        module_key: str,
        *,
        write: bool = False,
        manage: bool = False,
    ) -> str:
        access_role = self._module_access_role(user, module_key)
        if access_role == "none":
            raise ApiError(403, "当前客户未开通此模块或账号无权访问")
        if manage and access_role != "manager":
            raise ApiError(403, "需要模块管理员权限")
        if write and access_role not in {"manager", "editor"}:
            raise ApiError(403, "当前账号只能查看，不能新增或修改数据")
        return access_role

    def _validate_module_scheme_data(self, module_key: str, data: dict[str, Any]) -> None:
        if module_key == "multiday":
            days = self._num(data.get("md_days"))
            students = self._num(data.get("md_studentCount"))
            unit_price = self._num(data.get("md_unitPrice"))
            if days < 2 or days > 30 or not days.is_integer():
                raise ApiError(400, "多日大研学活动天数必须是 2 到 30 天的整数；1 天项目请使用单日大研学")
            if students <= 0:
                raise ApiError(400, "学生人数必须大于 0")
            if unit_price <= 0:
                raise ApiError(400, "人均报价必须大于 0")
            if not str(data.get("md_projectName") or "").strip():
                raise ApiError(400, "请填写项目名称")
            for key, value in data.items():
                if not str(key).startswith("md_") or isinstance(value, bool):
                    continue
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    continue
                if number < 0:
                    raise ApiError(400, "数量、金额和费率不能为负数")
            return
        if module_key == "dispatch":
            trip = data.get("tripInfo") or {}
            classes = data.get("classes") or []
            guides = data.get("guides") or []
            if not isinstance(trip, dict) or not all(str(trip.get(key) or "").strip() for key in ("name", "date", "dest", "school")):
                raise ApiError(400, "请完整填写项目名称、出行日期、目的地和学校名称")
            if not isinstance(classes, list) or not classes:
                raise ApiError(400, "请至少录入一个班级")
            names: set[str] = set()
            for item in classes:
                if not isinstance(item, dict):
                    raise ApiError(400, "班级数据无效")
                name = " ".join(str(item.get("name") or "").split())
                key = name.casefold()
                if not name or self._num(item.get("students")) <= 0 or self._num(item.get("teachers")) < 1:
                    raise ApiError(400, "每个班级必须填写名称、学生人数并至少安排 1 名教师")
                if key in names:
                    raise ApiError(400, "班级名称不能重复")
                names.add(key)
            if not isinstance(guides, list) or not guides:
                raise ApiError(400, "请至少添加一名导游或教官")

    def _normalize_module_supplier_bindings(
        self,
        bindings: dict[str, Any],
        user: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        normalized: dict[str, dict[str, Any]] = {}
        with self._connect() as conn:
            for raw_key, raw_binding in bindings.items():
                key = str(raw_key or "").strip()[:100]
                if not key or not isinstance(raw_binding, dict):
                    raise ApiError(400, "供方绑定无效")
                name = " ".join(str(raw_binding.get("supplierName") or raw_binding.get("name") or "").split())
                if not name:
                    continue
                if len(name) > 100:
                    raise ApiError(400, "供方名称不能超过 100 个字符")
                supplier_type = str(raw_binding.get("supplierType") or "其他").strip()[:50] or "其他"
                item_label = str(raw_binding.get("itemLabel") or key).strip()[:100] or key
                supplier_id_raw = raw_binding.get("supplierId") or raw_binding.get("supplier_id")
                supplier = None
                if supplier_id_raw not in (None, "", 0, "0"):
                    try:
                        supplier_id = int(supplier_id_raw)
                    except (TypeError, ValueError) as exc:
                        raise ApiError(400, f"供方“{name}”绑定无效") from exc
                    supplier = conn.execute(
                        "SELECT id,name,type FROM suppliers WHERE id=? AND tenant_id=?",
                        (supplier_id, user["tenant_id"]),
                    ).fetchone()
                    if not supplier:
                        raise ApiError(400, f"供方“{name}”不属于当前客户单位")
                else:
                    supplier = conn.execute(
                        "SELECT id,name,type FROM suppliers WHERE tenant_id=? AND name=? COLLATE NOCASE ORDER BY id LIMIT 1",
                        (user["tenant_id"], name),
                    ).fetchone()
                normalized[key] = {
                    "supplierId": int(supplier["id"]) if supplier else "",
                    "supplierName": str(supplier["name"]) if supplier else name,
                    "supplierType": str(supplier["type"]) if supplier else supplier_type,
                    "itemLabel": item_label,
                }
        return normalized

    def _save_module_scheme(self, module_key: str, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ApiError(400, "方案数据无效")
        self._validate_module_scheme_data(module_key, data)
        supplier_bindings = payload.get("supplier_bindings") or {}
        if not isinstance(supplier_bindings, dict):
            raise ApiError(400, "供方绑定无效")
        supplier_bindings = self._normalize_module_supplier_bindings(supplier_bindings, user)
        scheme_name = str(payload.get("scheme_name") or "").strip()
        if not scheme_name:
            raise ApiError(400, "请输入方案名称")
        if len(scheme_name) > 100:
            raise ApiError(400, "方案名称不能超过 100 个字符")
        customer_id = payload.get("customer_id")
        customer_id = int(customer_id) if customer_id not in (None, "", 0, "0") else None
        customer_name = str(payload.get("customer_name") or "").strip() or "未关联客户"
        project_date = normalize_optional_date(payload.get("project_date")) or self._today()
        now = self._now()
        with self._connect() as conn:
            if customer_id is not None:
                customer = conn.execute("SELECT id,name FROM customers WHERE id=? AND tenant_id=?", (customer_id, user["tenant_id"])).fetchone()
                if not customer:
                    raise ApiError(400, "关联客户不存在")
                customer_name = customer["name"]
            if customer_id is None:
                previous = conn.execute(
                    """
                    SELECT version FROM module_schemes
                    WHERE tenant_id=? AND module_key=? AND customer_id IS NULL AND customer_name=?
                      AND scheme_name=? AND is_latest=1 AND is_deleted=0
                    ORDER BY id DESC LIMIT 1
                    """,
                    (user["tenant_id"], module_key, customer_name, scheme_name),
                ).fetchone()
                conn.execute(
                    """
                    UPDATE module_schemes SET is_latest=0,updated_at=?
                    WHERE tenant_id=? AND module_key=? AND customer_id IS NULL AND customer_name=?
                      AND scheme_name=? AND is_latest=1
                    """,
                    (now, user["tenant_id"], module_key, customer_name, scheme_name),
                )
            else:
                previous = conn.execute(
                    """
                    SELECT version FROM module_schemes
                    WHERE tenant_id=? AND module_key=? AND customer_id=? AND scheme_name=?
                      AND is_latest=1 AND is_deleted=0
                    ORDER BY id DESC LIMIT 1
                    """,
                    (user["tenant_id"], module_key, customer_id, scheme_name),
                ).fetchone()
                conn.execute(
                    """
                    UPDATE module_schemes SET is_latest=0,updated_at=?
                    WHERE tenant_id=? AND module_key=? AND customer_id=? AND scheme_name=? AND is_latest=1
                    """,
                    (now, user["tenant_id"], module_key, customer_id, scheme_name),
                )
            version = int(previous["version"]) + 1 if previous else 1
            cur = conn.execute(
                """
                INSERT INTO module_schemes(
                  tenant_id,module_key,customer_id,customer_name,scheme_name,project_date,
                  data_json,supplier_bindings_json,version,is_latest,is_deleted,created_by,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,1,0,?,?,?)
                """,
                (user["tenant_id"], module_key, customer_id, customer_name, scheme_name, project_date,
                 json.dumps(data, ensure_ascii=False), json.dumps(supplier_bindings, ensure_ascii=False),
                 version, user.get("id"), now, now),
            )
            scheme_id = int(cur.lastrowid)
            if module_key == "multiday":
                for item in self._build_multiday_supplier_items(data, supplier_bindings, user):
                    conn.execute(
                        """
                        INSERT INTO module_supplier_items(
                          tenant_id,module_key,scheme_id,cost_category,cost_item,item_key,supplier_id,
                          supplier_name_snapshot,supplier_type,service_target,quantity,unit,
                          student_person_times,adult_person_times,amount,created_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            user["tenant_id"], module_key, scheme_id, item["cost_category"], item["cost_item"],
                            item["item_key"], item["supplier_id"], item["supplier_name"], item["supplier_type"],
                            item["service_target"], item["quantity"], item["unit"], item["student_person_times"],
                            item["adult_person_times"], item["amount"], now,
                        ),
                    )
        return {"id": scheme_id, "tenant_id": user["tenant_id"], "module_key": module_key, "version": version}

    def _build_multiday_supplier_items(
        self,
        data: dict[str, Any],
        bindings: dict[str, dict[str, Any]],
        user: dict[str, Any],
    ) -> list[dict[str, Any]]:
        n = lambda key: max(0.0, self._num(data.get(key)))
        students = n("md_studentCount")
        teachers = n("md_teacherCount") + n("md_schoolLeaderCount")
        staff = sum(n(key) for key in (
            "md_guideCount", "md_leaderCount", "md_safetyCount", "md_photographerCount",
            "md_medicCount", "md_lifeTeacherCount",
        ))
        extra_staff_rows = data.get("_mdExtraStaffRows")
        if isinstance(extra_staff_rows, list):
            staff += sum(
                max(0.0, self._num(row.get("count")))
                for row in extra_staff_rows
                if isinstance(row, dict)
            )
        else:
            staff += n("md_extraStaff1Count")
        drivers = n("md_driverCount")
        adults = teachers + staff + drivers
        total_people = students + adults
        items: list[dict[str, Any]] = []

        def add(
            key: str,
            category: str,
            item_name: str,
            amount: float,
            quantity: float,
            unit: str,
            service_target: str,
            student_times: float = 0,
            adult_times: float = 0,
        ) -> None:
            binding = bindings.get(key)
            if not binding or amount <= 0:
                return
            items.append({
                "cost_category": category,
                "cost_item": str(binding.get("itemLabel") or item_name)[:100],
                "item_key": key,
                "supplier_id": int(binding["supplierId"]) if binding.get("supplierId") not in (None, "") else None,
                "supplier_name": str(binding.get("supplierName") or "")[:100],
                "supplier_type": str(binding.get("supplierType") or "其他")[:50],
                "service_target": service_target,
                "quantity": max(0.0, quantity),
                "unit": unit,
                "student_person_times": max(0.0, student_times),
                "adult_person_times": max(0.0, adult_times),
                "amount": round(max(0.0, amount), 4),
            })

        add("md_train", "城市间交通", "高铁/动车", n("md_trainPrice") * n("md_trainCount"), n("md_trainCount"), "人", "出行人员", min(students, n("md_trainCount")), max(0, n("md_trainCount") - students))
        add("md_flight", "城市间交通", "飞机", n("md_flightPrice") * n("md_flightCount"), n("md_flightCount"), "人", "出行人员", min(students, n("md_flightCount")), max(0, n("md_flightCount") - students))
        add("md_long_bus", "城市间交通", "长途包车", n("md_longBusTotal"), 1, "项", "全团")
        local_mode = str(data.get("md_localBusMode") or "trips")
        add("md_local_bus_trips", "市内用车", "市内趟次用车", n("md_busFeePerTrip") * n("md_busCount") * n("md_busTrips") if local_mode != "charter" else 0, n("md_busCount") * n("md_busTrips"), "车次", "全团")
        add("md_local_bus_charter", "市内用车", "市内包车", n("md_busCharterTotal") if local_mode == "charter" else 0, n("md_busCount") or 1, "辆", "全团")

        meal_mode = str(data.get("_mdMealMode") or data.get("md_mealMode") or "legacy")
        if meal_mode == "package":
            counts = {
                "students": n("md_pkg_studentCount"),
                "teachers": n("md_pkg_teacherCount"),
                "staff": n("md_pkg_staffCount"),
                "exStudents": n("md_pkg_studentFree"),
                "exTeachers": n("md_pkg_teacherFree"),
                "exStaff": n("md_pkg_staffFree"),
            }

            def target_count(scope: str) -> float:
                values = {"students": counts["students"], "teachers": counts["teachers"], "staff": counts["staff"]}
                maps = {
                    "studentsTeachers": ("students", "teachers"), "teachersStaff": ("teachers", "staff"),
                    "studentsStaff": ("students", "staff"), "all": ("students", "teachers", "staff"),
                }
                if scope in values:
                    return values[scope]
                return sum(values[key] for key in maps.get(scope, maps["all"]))

            def free_count(scope: str) -> float:
                values = {"students": counts["exStudents"], "teachers": counts["exTeachers"], "staff": counts["exStaff"]}
                if scope in values:
                    return values[scope]
                keys = ("teachers", "staff") if scope == "teachersStaff" else ("students", "teachers", "staff")
                return sum(values[key] for key in keys)

            rows = data.get("_mdPackageRows") or []
            for index, row in enumerate(rows, 1):
                if not isinstance(row, dict):
                    continue
                price = max(0.0, self._num(row.get("price")))
                kind = str(row.get("type") or "unit")
                target = str(row.get("target") or "all")
                raw = 1.0 if kind == "fixed" else target_count(target)
                free = 0.0
                rule = str(row.get("rule") or "none")
                free_scope = target if str(row.get("freeTarget") or "target") == "target" else str(row.get("freeTarget") or "all")
                if kind != "fixed":
                    if rule == "all":
                        free = raw
                    elif rule == "global":
                        free = free_count(free_scope)
                    elif rule == "manual":
                        free = max(0.0, self._num(row.get("param1")))
                    elif rule == "studentRatio":
                        divisor = max(0.0, self._num(row.get("param1")))
                        free = (counts["students"] // divisor) * max(1.0, self._num(row.get("param2"))) if divisor else 0
                charge = max(0.0, raw - min(raw, free))
                amount = price if kind == "fixed" else price * charge
                includes_students = target in {"students", "studentsTeachers", "studentsStaff", "all"}
                student_times = min(charge, counts["students"]) if includes_students else 0
                add(f"md_pkg_{index}", "餐饮住宿", str(row.get("name") or f"打包项目{index}"), amount, charge, "人" if kind != "fixed" else "项", "打包核算", student_times, max(0, charge - student_times))
        else:
            rooms = n("md_hotelStaffRooms") + n("md_hotelStudentRooms")
            days = int(n("md_days"))
            for day in range(1, days + 1):
                add(f"md_day_{day}_hotel", "餐饮住宿", f"第{day}天住宿", rooms * n(f"md_hotel_{day}"), rooms, "间", "住宿")
                for meal_key, meal_name in (("breakfast", "早餐"), ("lunch", "午餐"), ("dinner", "晚餐")):
                    add(f"md_day_{day}_{meal_key}", "餐饮住宿", f"第{day}天{meal_name}", total_people * n(f"md_{meal_key}_{day}"), total_people, "人", "全团", students, adults)

        add("md_ticket", "场地与服务", "门票/场地", students * n("md_ticketPerStudent"), students, "人", "学生", students, 0)
        add("md_ticket2", "场地与服务", "门票/场地2", students * n("md_ticketPerStudent2"), students, "人", "学生", students, 0)
        add("md_insurance", "场地与服务", "保险（含司机）", total_people * n("md_insurancePerStudent"), total_people, "人", "全团", students, adults)
        add("md_session", "场地与服务", "讲解场次", n("md_sessionCount") * n("md_sessionPrice"), n("md_sessionCount"), "场", "全团")
        for row in data.get("_mdExtraServiceRows") or []:
            if isinstance(row, dict):
                index = int(self._num(row.get("index")) or 0)
                add(f"md_extra_service_{index}", "场地与服务", str(row.get("name") or "自定义服务"), self._num(row.get("count")) * self._num(row.get("price")), self._num(row.get("count")), "项", "自定义")

        add("md_hat", "物料与其他", "学生帽子", students * n("md_hatPrice"), students, "份", "学生", students, 0)
        add("md_material", "物料与其他", "手册+教具", students * n("md_materialPerStudent"), students, "份", "学生", students, 0)
        add("md_banner", "物料与其他", "旗子横幅", n("md_bannerCount") * n("md_bannerPrice"), n("md_bannerCount"), "个", "全团")
        add("md_medical", "物料与其他", "应急药箱", n("md_medicalFee"), 1, "项", "全团")
        add("md_misc", "物料与其他", "备用金", n("md_miscFee"), 1, "项", "全团")
        for row in data.get("_mdExtraMaterialRows") or []:
            if isinstance(row, dict):
                index = int(self._num(row.get("index")) or 0)
                add(f"md_extra_material_{index}", "物料与其他", str(row.get("name") or "自定义物料"), self._num(row.get("count")) * self._num(row.get("price")), self._num(row.get("count")), "项", "自定义")
        return items

    def _list_module_schemes(self, module_key: str, user: dict[str, Any]) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.id,s.tenant_id,s.module_key,s.customer_id,s.customer_name,s.scheme_name,
                       s.project_date,s.version,s.created_by,s.created_at,s.updated_at,u.username AS created_by_name
                FROM module_schemes s LEFT JOIN users u ON u.id=s.created_by
                WHERE s.tenant_id=? AND s.module_key=? AND s.is_latest=1 AND s.is_deleted=0
                ORDER BY s.updated_at DESC,s.id DESC
                """,
                (user["tenant_id"], module_key),
            ).fetchall()
        can_delete = self._module_access_role(user, module_key) == "manager"
        return [dict(row) | {"can_delete": can_delete} for row in rows]

    def _get_module_scheme(self, module_key: str, scheme_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM module_schemes WHERE id=? AND tenant_id=? AND module_key=? AND is_deleted=0",
                (scheme_id, user["tenant_id"], module_key),
            ).fetchone()
        if not row:
            raise ApiError(404, "方案不存在")
        item = dict(row)
        item["data"] = json.loads(item.pop("data_json") or "{}")
        item["supplier_bindings"] = json.loads(item.pop("supplier_bindings_json") or "{}")
        item["can_delete"] = self._module_access_role(user, module_key) == "manager"
        return item

    def _delete_module_scheme(self, module_key: str, scheme_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE module_schemes SET is_deleted=1,is_latest=0,updated_at=?
                WHERE id=? AND tenant_id=? AND module_key=?
                """,
                (self._now(), scheme_id, user["tenant_id"], module_key),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "方案不存在")
        return {"deleted": scheme_id}

    def _save_day1_scheme(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data") or {}
        if not isinstance(data, dict):
            raise ApiError(400, "方案数据无效")
        day_count = self._num(data.get("days")) if data.get("days") not in (None, "") else 1.0
        if abs(day_count - 1.0) > 1e-9:
            raise ApiError(400, "单日大研学活动天数固定为 1 天，多日项目请使用多日大研学模块")
        if not str(data.get("projectName") or "").strip():
            raise ApiError(400, "请填写项目名称")
        if self._num(data.get("studentCount")) <= 0:
            raise ApiError(400, "学员人数必须大于 0")
        if self._num(data.get("unitPrice")) <= 0:
            raise ApiError(400, "人均报价必须大于 0")
        for key, value in data.items():
            if str(key).startswith("_") or isinstance(value, bool):
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number < 0:
                raise ApiError(400, "数量、金额和费率不能为负数")
        supplier_bindings = payload.get("supplier_bindings") or {}
        if not isinstance(supplier_bindings, dict):
            raise ApiError(400, "供方绑定无效")
        customer_id = payload.get("customer_id")
        customer_id = int(customer_id) if customer_id not in (None, "", 0, "0") else None
        customer_name = str(payload.get("customer_name", "")).strip() or "未关联客户"
        scheme_name = str(payload.get("scheme_name", "")).strip()
        if not scheme_name:
            raise ApiError(400, "请输入方案名称")
        if len(scheme_name) > 100:
            raise ApiError(400, "方案名称不能超过 100 个字符")
        project_date = normalize_optional_date(payload.get("project_date")) or self._today()
        now = self._now()
        with self._connect() as conn:
            if customer_id is not None:
                customer = conn.execute(
                    "SELECT id,name FROM customers WHERE id=? AND tenant_id=?",
                    (customer_id, user["tenant_id"]),
                ).fetchone()
                if not customer:
                    raise ApiError(400, "关联客户不存在")
                customer_name = customer["name"]
            previous = self._find_latest_scheme(conn, user["tenant_id"], customer_id, customer_name, scheme_name)
            version = int(previous["version"]) + 1 if previous else 1
            self._mark_previous_versions(conn, user["tenant_id"], customer_id, customer_name, scheme_name, now)
            cur = conn.execute(
                """
                INSERT INTO day1_schemes(
                  tenant_id,customer_id,customer_name,scheme_name,module_type,project_date,
                  data_json,supplier_bindings_json,version,is_latest,is_deleted,created_by,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    user["tenant_id"],
                    customer_id,
                    customer_name,
                    scheme_name,
                    "day1",
                    project_date,
                    json.dumps(data, ensure_ascii=False),
                    json.dumps(supplier_bindings, ensure_ascii=False),
                    version,
                    1,
                    0,
                    user["id"],
                    now,
                    now,
                ),
            )
            scheme_id = cur.lastrowid
            for item in self._build_supplier_items(data, supplier_bindings, user, scheme_id):
                conn.execute(
                    """
                    INSERT INTO day1_supplier_items(
                      tenant_id,scheme_id,cost_category,cost_item,item_key,supplier_id,
                      supplier_name_snapshot,supplier_type,service_target,quantity,unit,
                      student_person_times,adult_person_times,amount,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        user["tenant_id"],
                        scheme_id,
                        item["cost_category"],
                        item["cost_item"],
                        item["item_key"],
                        item["supplier_id"],
                        item["supplier_name"],
                        item["supplier_type"],
                        item["service_target"],
                        item["quantity"],
                        item["unit"],
                        item["student_person_times"],
                        item["adult_person_times"],
                        item["amount"],
                        now,
                    ),
                )
        return {"id": scheme_id, "tenant_id": user["tenant_id"], "version": version}

    def _list_day1_schemes(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.id,s.tenant_id,s.customer_id,s.customer_name,s.scheme_name,s.project_date,
                       s.version,s.created_by,s.created_at,s.updated_at,u.username AS created_by_name
                FROM day1_schemes s
                LEFT JOIN users u ON u.id=s.created_by
                WHERE s.tenant_id=? AND s.module_type='day1' AND s.is_latest=1 AND s.is_deleted=0
                ORDER BY s.updated_at DESC,s.id DESC
                """,
                (user["tenant_id"],),
            ).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item["can_delete"] = self._can_manage_day1(user)
        return items

    def _get_day1_scheme(self, scheme_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM day1_schemes
                WHERE id=? AND tenant_id=? AND is_deleted=0
                """,
                (scheme_id, user["tenant_id"]),
            ).fetchone()
        if not row:
            raise ApiError(404, "方案不存在")
        item = dict(row)
        item["data"] = json.loads(item.pop("data_json") or "{}")
        item["supplier_bindings"] = json.loads(item.pop("supplier_bindings_json") or "{}")
        item["can_delete"] = self._can_manage_day1(user)
        return item

    def _delete_day1_scheme(self, scheme_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE day1_schemes SET is_deleted=1,is_latest=0,updated_at=?
                WHERE id=? AND tenant_id=?
                """,
                (self._now(), scheme_id, user["tenant_id"]),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "方案不存在")
        return {"deleted": scheme_id}

    def _supplier_stats(self, raw_query: str, user: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.parse_qs(raw_query)
        start_date = query.get("start_date", ["1900-01-01"])[0]
        end_date = query.get("end_date", ["2999-12-31"])[0]
        filters = {
            "supplier_type": query.get("supplier_type", [""])[0],
            "supplier_name": query.get("supplier_name", [""])[0],
            "customer": query.get("customer", [""])[0],
            "scheme_name": query.get("scheme_name", [""])[0],
        }
        visible_modules = [
            key for key in ("day1", "multiday")
            if self._module_access_role(user, key) != "none"
        ]
        if not visible_modules:
            return {"summary": [], "details": []}
        unions: list[str] = []
        params: list[Any] = []
        if "day1" in visible_modules:
            unions.append(
                """
                SELECT 'day1' AS module_key,i.*,s.project_date,s.customer_name,s.scheme_name,
                       s.id AS scheme_row_id,u.username AS created_by
                FROM day1_supplier_items i
                JOIN day1_schemes s ON s.id=i.scheme_id AND s.tenant_id=i.tenant_id
                LEFT JOIN users u ON u.id=s.created_by
                WHERE i.tenant_id=? AND s.is_latest=1 AND s.is_deleted=0
                """
            )
            params.append(user["tenant_id"])
        if "multiday" in visible_modules:
            unions.append(
                """
                SELECT 'multiday' AS module_key,i.id,i.tenant_id,i.scheme_id,i.cost_category,i.cost_item,
                       i.item_key,i.supplier_id,i.supplier_name_snapshot,i.supplier_type,i.service_target,
                       i.quantity,i.unit,i.student_person_times,i.adult_person_times,i.amount,i.created_at,
                       s.project_date,s.customer_name,s.scheme_name,s.id AS scheme_row_id,u.username AS created_by
                FROM module_supplier_items i
                JOIN module_schemes s ON s.id=i.scheme_id AND s.tenant_id=i.tenant_id AND s.module_key=i.module_key
                LEFT JOIN users u ON u.id=s.created_by
                WHERE i.tenant_id=? AND i.module_key='multiday' AND s.is_latest=1 AND s.is_deleted=0
                """
            )
            params.append(user["tenant_id"])
        where = ["project_date BETWEEN ? AND ?"]
        params.extend([start_date, end_date])
        if filters["supplier_type"]:
            where.append("supplier_type=?")
            params.append(filters["supplier_type"])
        if filters["supplier_name"]:
            where.append("supplier_name_snapshot LIKE ?")
            params.append(f"%{filters['supplier_name']}%")
        if filters["customer"]:
            where.append("customer_name LIKE ?")
            params.append(f"%{filters['customer']}%")
        if filters["scheme_name"]:
            where.append("scheme_name LIKE ?")
            params.append(f"%{filters['scheme_name']}%")
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                WITH usage AS ({' UNION ALL '.join(unions)})
                SELECT * FROM usage
                WHERE {" AND ".join(where)}
                ORDER BY project_date DESC,scheme_row_id DESC,id
                """,
                params,
            ).fetchall()
        details = []
        summary_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            detail = {
                "module_key": row["module_key"],
                "module_name": MODULE_CATALOG[row["module_key"]]["name"],
                "date": row["project_date"],
                "customer_name": row["customer_name"],
                "scheme_name": row["scheme_name"],
                "cost_category": row["cost_category"],
                "cost_item": row["cost_item"],
                "supplier_id": row["supplier_id"],
                "supplier_name": row["supplier_name_snapshot"],
                "supplier_type": row["supplier_type"],
                "service_target": row["service_target"],
                "quantity": row["quantity"],
                "unit": row["unit"],
                "student_person_times": row["student_person_times"],
                "adult_person_times": row["adult_person_times"],
                "amount": row["amount"],
                "created_by": row["created_by"] or "",
            }
            details.append(detail)
            key = (detail["supplier_name"], detail["supplier_type"])
            summary = summary_by_key.setdefault(key, {
                "supplier_name": detail["supplier_name"],
                "supplier_type": detail["supplier_type"],
                "scheme_count": set(),
                "student_person_times": 0.0,
                "adult_person_times": 0.0,
                "total_person_times": 0.0,
                "service_quantity": 0.0,
                "total_amount": 0.0,
            })
            summary["scheme_count"].add((detail["module_key"], detail["customer_name"], detail["scheme_name"], detail["date"]))
            summary["student_person_times"] += float(detail["student_person_times"] or 0)
            summary["adult_person_times"] += float(detail["adult_person_times"] or 0)
            summary["total_person_times"] += float(detail["student_person_times"] or 0) + float(detail["adult_person_times"] or 0)
            summary["service_quantity"] += float(detail["quantity"] or 0)
            summary["total_amount"] += float(detail["amount"] or 0)
        summaries = []
        for item in summary_by_key.values():
            row = dict(item)
            row["scheme_count"] = len(row["scheme_count"])
            summaries.append(row)
        summaries.sort(key=lambda item: (-float(item["total_amount"]), item["supplier_name"]))
        return {"summary": summaries, "details": details}

    def _build_supplier_items(
        self,
        data: dict[str, Any],
        supplier_bindings: dict[str, Any],
        user: dict[str, Any],
        scheme_id: int,
    ) -> list[dict[str, Any]]:
        student_count = self._num(data.get("studentCount"))
        days = 1.0
        teacher_count = self._num(data.get("teacherCount"))
        school_leaders = self._num(data.get("schoolLeaderCount"))
        guide_count = self._num(data.get("guideCount"))
        leader_count = self._num(data.get("leaderCount"))
        safety_count = self._num(data.get("safetyCount"))
        photographer_count = self._num(data.get("photographerCount"))
        medic_count = self._num(data.get("medicCount"))
        life_teacher_count = self._num(data.get("lifeTeacherCount"))
        custom_personnel = self._custom_personnel(data)
        custom_staff = sum(item["count"] for item in custom_personnel)
        adult_count = teacher_count + school_leaders + guide_count + leader_count + safety_count + photographer_count + medic_count + life_teacher_count + custom_staff
        driver_count = self._num(data.get("busCount"))
        items = []
        personnel_specs = (
            ("personnel_guide", "讲解导游", "guideCount", "guidePrice"),
            ("personnel_leader", "导游", "leaderCount", "leaderPrice"),
            ("personnel_safety", "安全员/教官", "safetyCount", "safetyPrice"),
            ("personnel_photographer", "摄影师", "photographerCount", "photographerPrice"),
            ("personnel_medic", "队医", "medicCount", "medicPrice"),
            ("personnel_life_teacher", "生活老师", "lifeTeacherCount", "lifeTeacherPrice"),
        )
        for key, label, count_key, price_key in personnel_specs:
            count = self._num(data.get(count_key))
            amount = count * self._num(data.get(price_key)) * days
            if amount and supplier_bindings.get(key):
                items.append(self._supplier_item(key, "人员费", label, "服务", supplier_bindings, user, count * days, "研学执行人员", 0, "人天", amount, count * days))
        for index, personnel in enumerate(custom_personnel, start=1):
            key = f"personnel_custom_{index}"
            amount = personnel["count"] * personnel["price"] * days
            if amount and supplier_bindings.get(key):
                items.append(self._supplier_item(key, "人员费", personnel["name"], "服务", supplier_bindings, user, personnel["count"] * days, "研学执行人员", 0, "人天", amount, personnel["count"] * days))
        ticket_price = self._num(data.get("ticketPerStudent"))
        if ticket_price:
            items.append(self._supplier_item("ticket", "场地服务", "门票/场地", "场地", supplier_bindings, user, student_count * days, "学员", student_count * days, "人次", ticket_price * student_count * days))
        ticket2_price = self._num(data.get("ticketPerStudent2"))
        if ticket2_price:
            items.append(self._supplier_item("ticket2", "场地服务", "门票/场地2", "场地", supplier_bindings, user, student_count * days, "学员", student_count * days, "人次", ticket2_price * student_count * days))
        insurance_price = self._num(data.get("insurancePerStudent"))
        if insurance_price:
            insured = (student_count + adult_count + driver_count) * days
            items.append(self._supplier_item("insurance", "场地服务", "保险费", "服务", supplier_bindings, user, insured, "全员（含司机）", student_count * days, "人次", insurance_price * insured, (adult_count + driver_count) * days))
        session_amount = self._num(data.get("sessionCount")) * self._num(data.get("sessionPrice"))
        if session_amount:
            items.append(self._supplier_item("session", "场地服务", "导师/讲解", "服务", supplier_bindings, user, self._num(data.get("sessionCount")), "场次", 0, "场", session_amount))
        for index, service in enumerate(self._extra_services(data), start=1):
            amount = service["count"] * service["price"]
            if amount:
                items.append(self._supplier_item(f"extra_service_{index}", "场地服务", service["name"], "服务", supplier_bindings, user, service["count"], "自定义数量", 0, "项", amount))
        bus_amount = self._num(data.get("busFeePerTrip")) * self._num(data.get("busCount")) * self._num(data.get("busTrips")) * days
        if bus_amount:
            quantity = self._num(data.get("busCount")) * self._num(data.get("busTrips"))
            items.append(self._supplier_item("bus", "交通费", "大巴交通", "交通", supplier_bindings, user, quantity * days, "全员", student_count * days, "车趟", bus_amount, adult_count * days))
        major_traffic_amount = self._num(data.get("majorTrafficPeople")) * self._num(data.get("majorTrafficPrice")) * self._num(data.get("majorTrafficTrips"))
        if major_traffic_amount:
            traffic_type = str(data.get("majorTrafficType") or "大交通").strip() or "大交通"
            quantity = self._num(data.get("majorTrafficPeople")) * self._num(data.get("majorTrafficTrips"))
            items.append(self._supplier_item("major_traffic", "交通费", f"大交通-{traffic_type}", "交通", supplier_bindings, user, quantity, "全员", student_count * days, "人趟", major_traffic_amount, adult_count * days))
        meal_student_amount = self._num(data.get("mealStudent")) * student_count * days
        if meal_student_amount:
            items.append(self._supplier_item("meal_student", "餐饮住宿", "学员餐费", "餐饮", supplier_bindings, user, student_count * days, "学员", student_count * days, "人餐", meal_student_amount))
        staff_meal_count = photographer_count + medic_count + life_teacher_count
        meal_staff_amount = self._num(data.get("mealStaff")) * staff_meal_count * days
        if meal_staff_amount:
            items.append(self._supplier_item("meal_staff", "餐饮住宿", "全职人员餐费", "餐饮", supplier_bindings, user, staff_meal_count * days, "成人/随行", 0, "人餐", meal_staff_amount, staff_meal_count * days))
        parttime_meal_count = leader_count + safety_count
        meal_parttime_amount = self._num(data.get("mealParttime")) * parttime_meal_count * days
        if meal_parttime_amount:
            items.append(self._supplier_item("meal_parttime", "餐饮住宿", "兼职人员餐费", "餐饮", supplier_bindings, user, parttime_meal_count * days, "成人/随行", 0, "人餐", meal_parttime_amount, parttime_meal_count * days))
        driver_count = self._num(data.get("busCount"))
        meal_driver_amount = self._num(data.get("mealDriver")) * driver_count * days
        if meal_driver_amount:
            items.append(self._supplier_item("meal_driver", "餐饮住宿", "司机餐费", "餐饮", supplier_bindings, user, driver_count * days, "成人/随行", 0, "人餐", meal_driver_amount, driver_count * days))
        for index, service in enumerate(self._meal_services(data), start=1):
            amount = service["count"] * service["price"]
            if amount:
                items.append(self._supplier_item(f"meal_service_{index}", "餐饮住宿", service["name"], "餐饮", supplier_bindings, user, service["count"], "自定义数量", 0, "项", amount))
        meal_adjustment_amount = self._num(data.get("mealAdjustmentAmount"))
        if meal_adjustment_amount:
            adjustment_name = str(data.get("mealAdjustmentName") or "餐饮住宿加减项").strip() or "餐饮住宿加减项"
            items.append(self._supplier_item("meal_adjustment", "餐饮住宿", adjustment_name, "餐饮", supplier_bindings, user, 1, "调整项", 0, "项", meal_adjustment_amount))
        hotel_nights = self._num(data.get("hotelNights"))
        rooms = self._num(data.get("hotelStaffRooms")) + self._num(data.get("hotelTeacherRooms")) + self._num(data.get("hotelStudentRooms"))
        hotel_amount = self._num(data.get("hotelPrice")) * rooms * hotel_nights
        if hotel_amount:
            items.append(self._supplier_item("hotel", "餐饮住宿", "住宿", "住宿", supplier_bindings, user, rooms * hotel_nights, "住宿", 0, "间夜", hotel_amount))
        return items

    def _extra_services(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        raw = data.get("_day1ExtraServices") or []
        if not isinstance(raw, list):
            return []
        out = []
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or f"自定义服务{index}").strip() or f"自定义服务{index}"
            count = self._num(item.get("count"))
            price = self._num(item.get("price"))
            if count or price:
                out.append({"name": name, "count": count, "price": price})
        return out

    def _meal_services(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        raw = data.get("_day1MealServices") or []
        if not isinstance(raw, list):
            return []
        out = []
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or f"餐饮住宿服务{index}").strip() or f"餐饮住宿服务{index}"
            count = max(0, self._num(item.get("count")))
            price = max(0, self._num(item.get("price")))
            if count or price:
                out.append({"name": name, "count": count, "price": price})
        return out

    def _custom_personnel(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        raw = data.get("_day1CustomPersonnel") or []
        if not isinstance(raw, list):
            return []
        out = []
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or f"自定义岗位{index}").strip() or f"自定义岗位{index}"
            out.append({"name": name, "count": self._num(item.get("count")), "price": self._num(item.get("price"))})
        return out

    def _supplier_item(
        self,
        key: str,
        category: str,
        item_name: str,
        default_type: str,
        bindings: dict[str, Any],
        user: dict[str, Any],
        quantity: float,
        target: str,
        student_person_times: float,
        unit: str,
        amount: float,
        adult_person_times: float = 0,
    ) -> dict[str, Any]:
        binding = bindings.get(key) or {}
        supplier_id = binding.get("supplier_id")
        supplier_id = int(supplier_id) if supplier_id not in (None, "", 0, "0") else None
        supplier_name = str(binding.get("supplier_name", "")).strip()
        supplier_type = str(binding.get("supplier_type", default_type)).strip() or default_type
        if supplier_id:
            supplier = self._get_supplier(supplier_id, user)
            if not supplier:
                raise ApiError(400, "供方不存在")
            supplier_name = supplier_name or supplier["name"]
            supplier_type = supplier["type"]
        if not supplier_name:
            supplier_name = "未指定供方"
        return {
            "cost_category": category,
            "cost_item": item_name,
            "item_key": key,
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "supplier_type": supplier_type,
            "service_target": target,
            "quantity": quantity,
            "unit": unit,
            "student_person_times": student_person_times,
            "adult_person_times": adult_person_times,
            "amount": amount,
        }

    def _find_latest_scheme(
        self,
        conn: sqlite3.Connection,
        tenant_id: int,
        customer_id: int | None,
        customer_name: str,
        scheme_name: str,
    ) -> sqlite3.Row | None:
        if customer_id is None:
            return conn.execute(
                """
                SELECT * FROM day1_schemes
                WHERE tenant_id=? AND customer_id IS NULL AND customer_name=? AND scheme_name=? AND module_type='day1'
                ORDER BY version DESC,id DESC LIMIT 1
                """,
                (tenant_id, customer_name, scheme_name),
            ).fetchone()
        return conn.execute(
            """
            SELECT * FROM day1_schemes
            WHERE tenant_id=? AND customer_id=? AND scheme_name=? AND module_type='day1'
            ORDER BY version DESC,id DESC LIMIT 1
            """,
            (tenant_id, customer_id, scheme_name),
        ).fetchone()

    def _mark_previous_versions(
        self,
        conn: sqlite3.Connection,
        tenant_id: int,
        customer_id: int | None,
        customer_name: str,
        scheme_name: str,
        now: str,
    ) -> None:
        if customer_id is None:
            conn.execute(
                """
                UPDATE day1_schemes SET is_latest=0,updated_at=?
                WHERE tenant_id=? AND customer_id IS NULL AND customer_name=? AND scheme_name=? AND module_type='day1'
                """,
                (now, tenant_id, customer_name, scheme_name),
            )
            return
        conn.execute(
            """
            UPDATE day1_schemes SET is_latest=0,updated_at=?
            WHERE tenant_id=? AND customer_id=? AND scheme_name=? AND module_type='day1'
            """,
            (now, tenant_id, customer_id, scheme_name),
        )

    def _get_supplier(self, supplier_id: int, user: dict[str, Any]) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM suppliers WHERE id=? AND tenant_id=?",
                (supplier_id, user["tenant_id"]),
            ).fetchone()
        return dict(row) if row else None

    def _num(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _optional_number(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        return max(0, self._num(value))

    def _optional_date(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        return normalize_date(value)

    def _assert_username_available(self, conn: sqlite3.Connection, username: str, message: str) -> None:
        exists = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if exists:
            raise ApiError(409, message)

    def _assert_tenant_user_limit(self, user: dict[str, Any]) -> None:
        tenant = self._get_tenant(int(user["tenant_id"]))
        if not tenant:
            raise ApiError(404, "客户单位不存在")
        with self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS count FROM users WHERE tenant_id=? AND is_active=1",
                (user["tenant_id"],),
            ).fetchone()["count"]
        if count >= tenant["max_users"]:
            raise ApiError(400, "已达到用户数上限")

    def _get_user_by_username(self, username: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None

    def _get_tenant(self, tenant_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        return dict(row) if row else None

    def _require_user(self, token: str | None) -> dict[str, Any]:
        if not token:
            raise ApiError(401, "请先登录")
        token_hash = self._session_token_hash(token)
        with self._connect() as conn:
            session = conn.execute(
                "SELECT user_id,expires_at FROM web_sessions WHERE token_hash=?",
                (token_hash,),
            ).fetchone()
            session_expired = bool(session and session["expires_at"] <= self._now())
            if not session or session_expired:
                row = None
            else:
                row = conn.execute(
                    "SELECT id,tenant_id,username,role,is_active FROM users WHERE id=?",
                    (session["user_id"],),
                ).fetchone()
        if not session or session_expired:
            self._delete_session(token)
            raise ApiError(401, "请先登录")
        if not row or not row["is_active"]:
            self._delete_session(token)
            raise ApiError(401, "登录已失效，请重新登录")
        current = self._session_user(dict(row))
        if current["tenant_id"] is not None:
            tenant = self._get_tenant(int(current["tenant_id"]))
            if (
                not tenant
                or tenant["status"] != "active"
                or (tenant["expires_at"] and tenant["expires_at"] < self._today())
            ):
                self._delete_session(token)
                raise ApiError(401, "登录已失效，请重新登录")
        self.sessions[token] = current
        return current

    def _require_platform_admin(self, user: dict[str, Any]) -> None:
        if user["role"] != "platform_admin":
            raise ApiError(403, "需要平台管理员权限")

    def _require_platform_permission(self, user: dict[str, Any], permission: str) -> None:
        if user["role"] not in PLATFORM_ROLES:
            raise ApiError(403, "需要平台维护权限")
        if permission not in PLATFORM_ROLE_PERMISSIONS.get(user["role"], set()):
            raise ApiError(403, "当前平台维护账号无权执行该操作")

    def _require_tenant_admin(self, user: dict[str, Any]) -> None:
        if user["role"] != "tenant_admin":
            raise ApiError(403, "需要客户管理员权限")

    def _require_tenant_user(self, user: dict[str, Any]) -> None:
        if user["tenant_id"] is None or user["role"] not in TENANT_ROLES:
            raise ApiError(403, "需要客户单位账号")

    def _require_tenant_writer(self, user: dict[str, Any]) -> None:
        if user["tenant_id"] is None or user["role"] not in TENANT_WRITE_ROLES:
            raise ApiError(403, "当前账号只能查看，不能新增或修改数据")

    def _require_day1_manager(self, user: dict[str, Any]) -> None:
        self._require_module_access(user, "day1", manage=True)

    def _can_manage_day1(self, user: dict[str, Any]) -> bool:
        return self._module_access_role(user, "day1") == "manager"

    def _require_shared_library_manager(self, user: dict[str, Any]) -> None:
        if user["tenant_id"] is None or not self._can_manage_shared_library(user):
            raise ApiError(403, "需要客户超级管理员或已开通模块的管理员权限")

    def _can_manage_shared_library(self, user: dict[str, Any]) -> bool:
        if self._can_manage_day1(user):
            return True
        return any(self._module_access_role(user, key) == "manager" for key in ("multiday", "dispatch"))

    def _drop_tenant_sessions(self, tenant_id: int) -> None:
        for token, session_user in list(self.sessions.items()):
            if session_user.get("tenant_id") == tenant_id:
                self.sessions.pop(token, None)
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM web_sessions WHERE user_id IN (SELECT id FROM users WHERE tenant_id=?)",
                (tenant_id,),
            )

    def _drop_user_sessions(self, user_id: int) -> None:
        for token, session_user in list(self.sessions.items()):
            if int(session_user.get("id") or 0) == int(user_id):
                self.sessions.pop(token, None)
        with self._connect() as conn:
            conn.execute("DELETE FROM web_sessions WHERE user_id=?", (user_id,))

    def _session_user(self, user: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": user["id"],
            "tenant_id": user["tenant_id"],
            "username": user["username"],
            "role": user["role"],
        }

    def _public_user(self, user: dict[str, Any]) -> dict[str, Any]:
        public = dict(user)
        role = str(public.get("role") or "")
        if role in PLATFORM_ROLES:
            public["role_label"] = PLATFORM_ROLE_LABELS.get(role, role)
            public["platform_permissions"] = sorted(PLATFORM_ROLE_PERMISSIONS.get(role, set()))
        return public

    def _decode_body(self, body: Any) -> dict[str, Any]:
        if body is None or body == b"":
            return {}
        if isinstance(body, dict):
            return body
        if isinstance(body, bytes):
            return json.loads(body.decode("utf-8"))
        if isinstance(body, str):
            return json.loads(body)
        raise ApiError(400, "请求体无效")

    def _json(self, payload: Any, status: int = 200) -> ApiResponse:
        return ApiResponse(
            status,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            {"Content-Type": "application/json; charset=utf-8"},
        )

    def _route_int(self, route: str, prefix: str) -> int:
        try:
            return int(route[len(prefix):])
        except ValueError as exc:
            raise ApiError(404, "路径无效") from exc

    def _platform_tenant_user_route(self, route: str) -> tuple[int, int, str]:
        parts = route.strip("/").split("/")
        if len(parts) != 7 or parts[:3] != ["api", "platform", "tenants"] or parts[4] != "users":
            raise ApiError(404, "路径无效")
        try:
            tenant_id = int(parts[3])
            user_id = int(parts[5])
        except ValueError as exc:
            raise ApiError(404, "路径无效") from exc
        action = parts[6] if len(parts) > 6 else ""
        return tenant_id, user_id, action

    def _now(self) -> str:
        return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")

    def _today(self) -> str:
        return dt.date.today().isoformat()

    def _timestamp(self) -> str:
        return dt.datetime.now().strftime("%Y-%m-%d-%H%M%S-%f")


def clean_number(value: Any) -> int | float:
    value = round(float(value or 0), 6)
    if value.is_integer():
        return int(value)
    return value


def normalize_date(value: Any) -> str:
    text = str(value or dt.date.today().isoformat()).strip()
    try:
        return dt.date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return dt.date.today().isoformat()


def normalize_optional_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    candidates = [text[:10], text.replace("年", "-").replace("月", "-").replace("日", "")]
    candidates.extend([text.replace("/", "-"), text.replace(".", "-")])
    for candidate in candidates:
        parts = candidate.strip().split("-")
        if len(parts) == 3 and all(part.strip().isdigit() for part in parts):
            try:
                return dt.date(int(parts[0]), int(parts[1]), int(parts[2])).isoformat()
            except ValueError:
                continue
        try:
            return dt.date.fromisoformat(candidate[:10]).isoformat()
        except ValueError:
            continue
    raise ApiError(400, "日期格式无效，请使用 YYYY-MM-DD")


def build_xlsx(summary: list[dict[str, Any]], details: list[dict[str, Any]]) -> bytes:
    summary_headers = [
        "供方名称",
        "类型",
        "方案数",
        "学员人次",
        "成人/随行人次",
        "总服务人次",
        "服务数量",
        "总金额",
    ]
    summary_rows = [
        [
            row["supplier_name"],
            row["supplier_type"],
            row["scheme_count"],
            row["student_person_times"],
            row["adult_person_times"],
            row["total_person_times"],
            row["service_quantity"],
            row["total_amount"],
        ]
        for row in summary
    ]
    detail_headers = [
        "业务模块",
        "日期",
        "客户",
        "方案名称",
        "费用大类",
        "费用项",
        "供方",
        "服务对象",
        "数量",
        "单位",
        "学员人次",
        "成人/随行人次",
        "金额",
        "创建人",
    ]
    detail_rows = [
        [
            row.get("module_name", "单日大研学"),
            row["date"],
            row["customer_name"],
            row["scheme_name"],
            row["cost_category"],
            row["cost_item"],
            row["supplier_name"],
            row["service_target"],
            row["quantity"],
            row["unit"],
            row["student_person_times"],
            row["adult_person_times"],
            row["amount"],
            row["created_by"],
        ]
        for row in details
    ]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", ROOT_RELS_XML)
        zf.writestr("xl/workbook.xml", WORKBOOK_XML)
        zf.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
        zf.writestr("xl/styles.xml", XLSX_STYLES_XML)
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            worksheet_xml(
                [summary_headers, *summary_rows],
                [24, 16, 12, 14, 18, 16, 14, 16],
                {8},
            ),
        )
        zf.writestr(
            "xl/worksheets/sheet2.xml",
            worksheet_xml(
                [detail_headers, *detail_rows],
                [16, 14, 24, 30, 18, 22, 22, 18, 12, 12, 14, 18, 16, 16],
                {13},
            ),
        )
    return out.getvalue()


def build_prepurchase_xlsx(summary: list[dict[str, Any]], details: list[dict[str, Any]]) -> bytes:
    summary_headers = [
        "年度",
        "供方",
        "适用项目",
        "采购金额",
        "已用金额",
        "剩余金额",
        "金额使用率",
        "采购数量",
        "已用数量",
        "剩余数量",
        "数量单位",
        "有效开始",
        "有效结束",
        "备注",
    ]
    summary_rows = [
        [
            row["year"],
            row["supplier_name"],
            row["item_scope"],
            row["purchased_amount"],
            row["used_amount"],
            row["remaining_amount"],
            row["amount_usage_rate"],
            row["purchased_quantity"],
            row["used_quantity"],
            row["remaining_quantity"],
            row["quantity_unit"],
            row["valid_from"],
            row["valid_to"],
            row["notes"],
        ]
        for row in summary
    ]
    detail_headers = [
        "日期",
        "客户",
        "方案名称",
        "费用项",
        "供方",
        "数量",
        "单位",
        "金额",
        "来源",
        "创建人",
    ]
    detail_rows = [
        [
            row["date"],
            row["customer_name"],
            row["scheme_name"],
            row["cost_item"],
            row["supplier_name"],
            row["quantity"],
            row["unit"],
            row["amount"],
            row["source"],
            row["created_by"],
        ]
        for row in details
    ]
    workbook_xml = workbook_xml_with_sheets("预采买汇总", "使用明细")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", ROOT_RELS_XML)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
        zf.writestr("xl/styles.xml", XLSX_STYLES_XML)
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            worksheet_xml(
                [summary_headers, *summary_rows],
                [10, 24, 24, 16, 16, 16, 14, 14, 14, 14, 12, 14, 14, 30],
                {4, 5, 6},
            ),
        )
        zf.writestr(
            "xl/worksheets/sheet2.xml",
            worksheet_xml(
                [detail_headers, *detail_rows],
                [14, 24, 30, 22, 24, 14, 12, 16, 18, 16],
                {8},
            ),
        )
    return out.getvalue()


def build_platform_logs_xlsx(logs: list[dict[str, Any]], exported_at: str) -> bytes:
    headers = ["时间", "操作人", "动作", "对象类型", "对象名称", "对象ID", "详情"]
    rows = [
        [
            item.get("created_at", ""),
            item.get("actor_username", ""),
            PLATFORM_ACTION_NAMES.get(str(item.get("action", "")), item.get("action", "")),
            item.get("target_type", ""),
            item.get("target_name", ""),
            item.get("target_id", ""),
            json.dumps(item.get("details") or {}, ensure_ascii=False),
        ]
        for item in logs
    ]
    summary_rows = [
        ["导出时间", exported_at],
        ["记录条数", len(logs)],
        ["导出范围", "按后台当前筛选条件导出，最多 5000 条"],
    ]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", ROOT_RELS_XML)
        zf.writestr("xl/workbook.xml", workbook_xml_with_sheets("操作日志", "导出说明"))
        zf.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
        zf.writestr("xl/styles.xml", XLSX_STYLES_XML)
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            worksheet_xml([headers, *rows], [20, 18, 22, 18, 28, 12, 60]),
        )
        zf.writestr(
            "xl/worksheets/sheet2.xml",
            worksheet_xml(summary_rows, [18, 52]),
        )
    return out.getvalue()


def workbook_xml_with_sheets(sheet1: str, sheet2: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        f'<sheet name="{xml_escape(sheet1)}" sheetId="1" r:id="rId1"/>'
        f'<sheet name="{xml_escape(sheet2)}" sheetId="2" r:id="rId2"/>'
        "</sheets>"
        "</workbook>"
    )


def col_name(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def worksheet_xml(
    rows: list[list[Any]],
    column_widths: list[int | float] | None = None,
    currency_columns: set[int] | None = None,
) -> str:
    currency_columns = currency_columns or set()
    sheet_rows = []
    for r_index, row in enumerate(rows, start=1):
        cells = []
        for c_index, value in enumerate(row, start=1):
            ref = f"{col_name(c_index)}{r_index}"
            style_id = 1 if r_index == 1 else 2 if c_index in currency_columns else 3
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{ref}" s="{style_id}"><v>{value}</v></c>')
            else:
                text = xml_escape(str(value if value is not None else ""))
                cells.append(f'<c r="{ref}" s="{style_id}" t="inlineStr"><is><t>{text}</t></is></c>')
        height = ' ht="24" customHeight="1"' if r_index == 1 else ''
        sheet_rows.append(f'<row r="{r_index}"{height}>{"".join(cells)}</row>')
    max_columns = max((len(row) for row in rows), default=1)
    last_row = max(len(rows), 1)
    dimensions = f'A1:{col_name(max_columns)}{last_row}'
    columns = ""
    if column_widths:
        columns = "<cols>" + "".join(
            f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
            for index, width in enumerate(column_widths, start=1)
        ) + "</cols>"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimensions}"/>'
        '<sheetViews><sheetView workbookViewId="0" showGridLines="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        f'{columns}<sheetData>{"".join(sheet_rows)}</sheetData>'
        f'<autoFilter ref="{dimensions}"/>'
        "</worksheet>"
    )


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

ROOT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="供方汇总" sheetId="1" r:id="rId1"/>
    <sheet name="供方明细" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""

WORKBOOK_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

XLSX_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="1"><numFmt numFmtId="164" formatCode="¥#,##0.00;[Red]-¥#,##0.00"/></numFmts>
  <fonts count="2">
    <font><sz val="11"/><name val="Microsoft YaHei"/><family val="2"/></font>
    <font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Microsoft YaHei"/><family val="2"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF3157C8"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFD8E1EC"/></left><right style="thin"><color rgb="FFD8E1EC"/></right><top style="thin"><color rgb="FFD8E1EC"/></top><bottom style="thin"><color rgb="FFD8E1EC"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="4">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


class SaaSHostRequestHandler(BaseHTTPRequestHandler):
    app: SaaSHostApp
    server_version = "Yaocheng"
    sys_version = ""
    platform_session_cookie_name = "yaocheng_platform_session"
    customer_session_cookie_name = "yaocheng_customer_session"
    platform_csrf_cookie_name = "yaocheng_platform_csrf"
    customer_csrf_cookie_name = "yaocheng_customer_csrf"
    legacy_session_cookie_name = "yaocheng_session"
    legacy_csrf_cookie_name = "yaocheng_csrf"
    trial_cookie_name = "yaocheng_trial"
    session_scope_header_name = "X-Yaocheng-Session-Scope"

    def do_GET(self) -> None:
        if self.path.startswith("/api/"):
            self._send(self.app.api_request(
                "GET",
                self.path,
                token=self._token(),
                client_key=self._client_key(),
                trial_token=self._trial_token(),
            ))
            return
        self._send(self.app.serve_static(self.path))

    def do_POST(self) -> None:
        csrf_error = self._csrf_error("POST")
        if csrf_error:
            self._send(csrf_error)
            return
        self._send(self.app.api_request(
            "POST",
            self.path,
            token=self._token(),
            body=self._body(),
            client_key=self._client_key(),
            trial_token=self._trial_token(),
        ))

    def do_PATCH(self) -> None:
        csrf_error = self._csrf_error("PATCH")
        if csrf_error:
            self._send(csrf_error)
            return
        self._send(self.app.api_request("PATCH", self.path, token=self._token(), body=self._body(), client_key=self._client_key()))

    def do_DELETE(self) -> None:
        csrf_error = self._csrf_error("DELETE")
        if csrf_error:
            self._send(csrf_error)
            return
        self._send(self.app.api_request("DELETE", self.path, token=self._token(), body=self._body(), client_key=self._client_key()))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.client_address[0]} - {fmt % args}")

    def _session_scope(self) -> str:
        requested = self.headers.get(self.session_scope_header_name, "").strip().lower()
        if requested in {"platform", "customer"}:
            return requested
        route = urllib.parse.urlparse(self.path).path
        if route.startswith("/api/platform/"):
            return "platform"
        referer_path = urllib.parse.urlparse(self.headers.get("Referer", "")).path
        if referer_path.endswith("/admin.html"):
            return "platform"
        return "customer"

    def _session_cookie_names(self, scope: str) -> tuple[str, str]:
        if scope == "platform":
            return self.platform_session_cookie_name, self.platform_csrf_cookie_name
        return self.customer_session_cookie_name, self.customer_csrf_cookie_name

    def _token(self) -> str | None:
        header = self.headers.get("Authorization", "")
        bearer = header.removeprefix("Bearer ").strip()
        if bearer:
            self._session_cookie_source = "authorization"
            self._resolved_session_token = bearer
            return bearer
        scope = self._session_scope()
        session_cookie_name, _ = self._session_cookie_names(scope)
        token = self._cookie_value(session_cookie_name)
        if token:
            self._session_cookie_source = scope
            self._resolved_session_token = token
            return token
        legacy_token = self._cookie_value(self.legacy_session_cookie_name)
        if legacy_token:
            self._session_cookie_source = "legacy"
            self._resolved_session_token = legacy_token
            return legacy_token
        self._session_cookie_source = ""
        self._resolved_session_token = ""
        return None

    def _trial_token(self) -> str | None:
        return self._cookie_value(self.trial_cookie_name) or None

    def _cookie_value(self, name: str) -> str:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return ""
        morsel = cookie.get(name)
        return morsel.value if morsel else ""

    def _csrf_error(self, method: str) -> ApiResponse | None:
        route = urllib.parse.urlparse(self.path).path
        if method not in {"POST", "PATCH", "DELETE"}:
            return None
        if route in {
            "/api/login",
            "/api/setup/initialize",
            "/api/signup-requests",
            "/api/signup-requests/enter",
        }:
            return None
        if self.headers.get("Authorization", "").removeprefix("Bearer ").strip():
            return None
        scope = self._session_scope()
        session_cookie_name, csrf_cookie_name = self._session_cookie_names(scope)
        has_scoped_session = bool(self._cookie_value(session_cookie_name))
        has_legacy_session = bool(self._cookie_value(self.legacy_session_cookie_name))
        if not has_scoped_session and not has_legacy_session:
            return None
        csrf_cookie = self._cookie_value(csrf_cookie_name if has_scoped_session else self.legacy_csrf_cookie_name)
        csrf_header = self.headers.get("X-CSRF-Token", "").strip()
        if csrf_cookie and csrf_header and hmac.compare_digest(csrf_cookie, csrf_header):
            return None
        return self.app._json({"error": "安全校验已失效，请刷新页面后重试"}, 403)

    def _client_key(self) -> str:
        if self.app.trusted_proxy:
            forwarded = self.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
            if forwarded:
                return forwarded[:120]
        return str(self.client_address[0] or "unknown")[:120]

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or 0)
        return self.rfile.read(length) if length else b""

    def _send(self, response: ApiResponse) -> None:
        response, cookies = self._prepare_session_response(response)
        self.send_response(response.status)
        self._cors()
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        if self.app.trusted_proxy and self.headers.get("X-Forwarded-Proto", "").strip().lower() == "https":
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        if response.body:
            self.wfile.write(response.body)

    def _prepare_session_response(self, response: ApiResponse) -> tuple[ApiResponse, list[str]]:
        route = urllib.parse.urlparse(self.path).path
        cookies: list[str] = []
        if route == "/api/signup-requests" and 200 <= response.status < 300:
            try:
                payload = response.json()
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, dict) and payload.get("trial_token"):
                trial_token = str(payload.pop("trial_token"))
                cookies.append(self._cookie_header(
                    self.trial_cookie_name,
                    trial_token,
                    http_only=True,
                    max_age=30 * 24 * 3600,
                ))
                response = self.app._json(payload, response.status)
        if route in {"/api/login", "/api/setup/initialize", "/api/signup-requests/enter"} and 200 <= response.status < 300:
            try:
                payload = response.json()
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, dict) and payload.get("token"):
                token = str(payload.pop("token"))
                csrf = secrets.token_urlsafe(24)
                user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
                scope = "platform" if str(user.get("role") or "") in PLATFORM_ROLES else "customer"
                session_cookie_name, csrf_cookie_name = self._session_cookie_names(scope)
                cookies.extend((
                    self._cookie_header(session_cookie_name, token, http_only=True),
                    self._cookie_header(csrf_cookie_name, csrf, http_only=False),
                ))
                cookies.extend(self._expired_legacy_session_cookies())
                response = self.app._json(payload, response.status)
        if route == "/api/logout" and 200 <= response.status < 300:
            cookies.extend(self._expired_session_cookies(self._session_scope()))
            if getattr(self, "_session_cookie_source", "") == "legacy":
                cookies.extend(self._expired_legacy_session_cookies())
        elif response.status == 401 and getattr(self, "_session_cookie_source", ""):
            if self._session_cookie_source == "legacy":
                cookies.extend(self._expired_legacy_session_cookies())
            elif self._session_cookie_source != "authorization":
                cookies.extend(self._expired_session_cookies(self._session_scope()))
        elif (
            route not in {"/api/login", "/api/setup/initialize", "/api/signup-requests/enter"}
            and response.status < 300
            and getattr(self, "_session_cookie_source", "") == "legacy"
        ):
            try:
                payload = response.json()
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = None
            user = payload.get("user") if isinstance(payload, dict) and isinstance(payload.get("user"), dict) else {}
            scope = self._session_scope()
            role = str(user.get("role") or "")
            role_matches_scope = (scope == "platform" and role in PLATFORM_ROLES) or (
                scope == "customer" and role in TENANT_ROLES
            )
            if role_matches_scope and self._resolved_session_token:
                session_cookie_name, csrf_cookie_name = self._session_cookie_names(scope)
                cookies.extend((
                    self._cookie_header(session_cookie_name, self._resolved_session_token, http_only=True),
                    self._cookie_header(csrf_cookie_name, secrets.token_urlsafe(24), http_only=False),
                ))
                cookies.extend(self._expired_legacy_session_cookies())
        return response, cookies

    def _cookie_header(self, name: str, value: str, *, http_only: bool, max_age: int | None = None) -> str:
        cookie_max_age = self.app.session_hours * 3600 if max_age is None else int(max_age)
        parts = [f"{name}={value}", "Path=/", "SameSite=Lax", f"Max-Age={cookie_max_age}"]
        if http_only:
            parts.append("HttpOnly")
        if self.app.public_url.startswith("https://") or (
            self.app.trusted_proxy and self.headers.get("X-Forwarded-Proto", "").strip().lower() == "https"
        ):
            parts.append("Secure")
        return "; ".join(parts)

    def _expired_session_cookies(self, scope: str) -> list[str]:
        secure = self.app.public_url.startswith("https://") or (
            self.app.trusted_proxy and self.headers.get("X-Forwarded-Proto", "").strip().lower() == "https"
        )
        suffix = "; Secure" if secure else ""
        common = "; Path=/; SameSite=Lax; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT" + suffix
        session_cookie_name, csrf_cookie_name = self._session_cookie_names(scope)
        return [f"{session_cookie_name}={common}", f"{csrf_cookie_name}={common}"]

    def _expired_legacy_session_cookies(self) -> list[str]:
        secure = self.app.public_url.startswith("https://") or (
            self.app.trusted_proxy and self.headers.get("X-Forwarded-Proto", "").strip().lower() == "https"
        )
        suffix = "; Secure" if secure else ""
        common = "; Path=/; SameSite=Lax; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT" + suffix
        return [f"{self.legacy_session_cookie_name}={common}", f"{self.legacy_csrf_cookie_name}={common}"]

    def _cors(self) -> None:
        origin = self.headers.get("Origin", "").strip()
        host = self.headers.get("Host", "").strip()
        if origin and urllib.parse.urlparse(origin).netloc == host:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-CSRF-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")


def run_server(
    host: str,
    port: int,
    root: Path,
    *,
    public_url: str | None = None,
    deployment: str | None = None,
    trusted_proxy: bool | None = None,
    session_hours: int | None = None,
) -> None:
    app = SaaSHostApp(
        root,
        public_url=public_url,
        deployment=deployment,
        trusted_proxy=trusted_proxy,
        session_hours=session_hours,
    )
    handler = type("ConfiguredSaaSHostRequestHandler", (SaaSHostRequestHandler,), {"app": app})
    server = ThreadingHTTPServer((host, port), handler)
    print("曜程已启动")
    print(f"访问地址: {app.public_url or f'http://{host}:{port}'}")
    if app._setup_required():
        print(f"首次启用: {(app.public_url or f'http://{host}:{port}')}/setup.html")
    else:
        print(f"管理中心: {(app.public_url or f'http://{host}:{port}')}/admin.html")
    print("按 Ctrl+C 停止服务")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="曜程线上 SaaS 服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8776)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--public-url", default=os.environ.get("YAOCHENG_PUBLIC_URL", ""))
    parser.add_argument(
        "--deployment",
        choices=("local-development", "public-test", "online-saas"),
        default=os.environ.get("YAOCHENG_DEPLOYMENT") or None,
    )
    parser.add_argument("--trusted-proxy", action="store_true", default=None)
    parser.add_argument("--session-hours", type=int, default=None)
    args = parser.parse_args(argv)
    try:
        run_server(
            args.host,
            args.port,
            args.root,
            public_url=args.public_url,
            deployment=args.deployment,
            trusted_proxy=args.trusted_proxy,
            session_hours=args.session_hours,
        )
    except KeyboardInterrupt:
        print("\n曜程服务已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
