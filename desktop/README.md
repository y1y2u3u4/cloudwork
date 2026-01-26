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
