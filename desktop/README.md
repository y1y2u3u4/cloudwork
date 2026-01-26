# CloudWork Desktop

基于 WorkAny 的 Tauri + React 桌面端，连接 CloudWork Python 后端。

## 架构

```
desktop/
├── src/               # React 前端 (复用 WorkAny)
├── src-tauri/         # Tauri 桌面壳 (复用 WorkAny)
├── api/               # Python FastAPI 桥接层 (新建)
└── package.json       # 前端依赖
```

## 与 Bot 的关系

- Bot 继续运行在 VPS 上 (systemd 服务)
- 桌面端通过 API 连接同一个后端
- 共享: sessions.json, memory 系统, Claude CLI
- 不冲突: 桌面端是可选的增强 UI

## 开发

```bash
# 安装依赖
cd desktop && pnpm install

# 启动 API 桥接层
cd api && python -m uvicorn main:app --reload --port 2026

# 启动前端开发
pnpm dev

# 构建桌面应用
pnpm tauri build
```

## 技术栈

- **前端**: React 19 + TypeScript + Vite + Tailwind CSS
- **桌面壳**: Tauri 2 (Rust)
- **API 层**: Python FastAPI + WebSocket
- **共享**: CloudWork 现有的 session/memory/claude 服务

## 安全注意事项

**Desktop API 默认只绑定 localhost (127.0.0.1)**，不会暴露到公网。

如需远程访问，**必须使用 Cloudflare Tunnel**，不要直接暴露端口：

```bash
# 安装 cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# 登录 Cloudflare
cloudflared tunnel login

# 创建 tunnel
cloudflared tunnel create cloudwork-api

# 配置 tunnel (创建 ~/.cloudflared/config.yml)
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: cloudwork-api
credentials-file: /home/claude/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: cloudwork-api.yourdomain.com
    service: http://localhost:2026
  - service: http_status:404
EOF

# 添加 DNS 记录
cloudflared tunnel route dns cloudwork-api cloudwork-api.yourdomain.com

# 运行 tunnel
cloudflared tunnel run cloudwork-api
```

这样 API 通过 Cloudflare 代理，可添加 Access 策略进行身份认证。

**千万不要**：
- 直接设置 `API_HOST=0.0.0.0` 暴露到公网
- Desktop API 没有内置身份认证，暴露后任何人都能调用 Claude CLI
