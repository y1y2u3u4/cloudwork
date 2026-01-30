# 本地节点执行配置指南

通过 Telegram Bot 远程控制本地 Mac 上的 Claude Code 执行。

## 架构概述

```
┌──────────────┐     Telegram      ┌─────────────┐     Tailscale     ┌──────────────┐
│   用户手机    │ ◄──────────────► │   VPS Bot   │ ◄───────────────► │  本地 Mac    │
│  Telegram    │                   │ (代理转发)   │    内网穿透        │ Desktop API  │
└──────────────┘                   └─────────────┘                   └──────────────┘
                                         │                                  │
                                         │ execution_target="local"         │ Claude CLI
                                         │ 时转发请求到本地                    │ 本地执行
                                         ▼                                  ▼
                                   ┌─────────────┐                   ┌──────────────┐
                                   │ sessions.json│                   │ 本地项目目录  │
                                   │ 记录节点配置  │                   │              │
                                   └─────────────┘                   └──────────────┘
```

## 前置条件

1. **Tailscale** - 本地 Mac 和 VPS 都需要安装并连接到同一个 Tailscale 网络
2. **Desktop API** - 本地 Mac 需要运行 CloudWork Desktop API
3. **Claude CLI** - 本地 Mac 需要安装并配置好 Claude CLI

---

## 第一步：本地 Mac 环境准备

### 1. 确保 Tailscale 已安装并连接

```bash
# 检查 Tailscale 状态
tailscale status

# 获取本机 Tailscale IP
tailscale ip -4
# 记下输出的 IP，类似: 100.x.x.x
```

### 2. 确保 Claude CLI 已安装并配置

```bash
# 测试 Claude CLI 是否可用
claude --version
```

---

## 第二步：启动本地 Desktop API

### 1. 进入项目目录

```bash
cd /Users/zhanggongqing/project/孵化项目/cloudwork
```

### 2. 安装依赖（如果还没有）

```bash
pip install fastapi uvicorn aiohttp
```

### 3. 启动 Desktop API（启用认证）

```bash
# 生成一个随机 Token（或自己设定一个）
export MY_TOKEN=$(openssl rand -hex 16)
echo "你的 Token: $MY_TOKEN"

# 启动 API（绑定所有网卡，启用认证）
CLOUDWORK_REQUIRE_AUTH=true \
CLOUDWORK_API_TOKEN=$MY_TOKEN \
API_HOST=0.0.0.0 \
python desktop/api/main.py
```

启动成功后会显示：

```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:2026
```

### 4. 验证 API 运行正常

新开一个终端窗口：

```bash
# 健康检查（不需要认证）
curl http://localhost:2026/health
# 应返回: {"status":"ok","service":"cloudwork-desktop"}

# 测试认证（需要 Token）
curl -X POST http://localhost:2026/agent \
  -H "Authorization: Bearer $MY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"echo hello"}'
# 应返回 SSE 流
```

### 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_PORT` | 2026 | API 监听端口 |
| `API_HOST` | 127.0.0.1 | 绑定地址，远程访问需设为 `0.0.0.0` |
| `CLOUDWORK_REQUIRE_AUTH` | false | 是否启用认证 |
| `CLOUDWORK_API_TOKEN` | (空) | API 访问令牌 |
| `DESKTOP_USER_ID` | 0 | 桌面端用户 ID |

---

## 第三步：Telegram Bot 配置

在 Telegram 中向 Bot 发送以下命令：

### 1. 设置本地节点 URL

```
/target local http://100.x.x.x:2026
```

（将 `100.x.x.x` 替换为你的 Tailscale IP）

### 2. 设置认证 Token

```
/target token 你的Token值
```

（就是上面 `echo "你的 Token: $MY_TOKEN"` 显示的那个值）

### 3. 确认配置

```
/target
```

应该显示类似：

```
💻 执行目标

当前: LOCAL
本地节点: http://100.x.x.x:2026
API Token: ✅ 已设置
```

---

## 第四步：测试本地执行

在 Telegram 中发送任意消息测试：

```
请列出当前目录下的文件
```

Bot 应该显示：

1. `🔗 连接本地节点 http://100.x.x.x:2026...`
2. `🖥️ 本地节点执行中...`
3. 然后返回本地 Mac 上的执行结果

---

## 切换执行目标

```
# 切换回 VPS 执行
/target vps

# 再次切换到本地（使用已保存的 URL）
/target local

# 查看当前状态
/target
```

---

## 快速参考

| 操作 | 命令 |
|------|------|
| 查看当前目标 | `/target` |
| 切换到本地 | `/target local http://100.x.x.x:2026` |
| 设置 Token | `/target token xxx` |
| 切回 VPS | `/target vps` |
| 清除 Token | `/target token` |

---

## 后台运行 Desktop API

如果想让 Desktop API 持续在后台运行：

### 方法 1: 使用 nohup

```bash
# 后台启动
nohup env CLOUDWORK_REQUIRE_AUTH=true \
  CLOUDWORK_API_TOKEN=your-token \
  API_HOST=0.0.0.0 \
  python desktop/api/main.py > ~/desktop-api.log 2>&1 &

# 查看日志
tail -f ~/desktop-api.log

# 停止
pkill -f "desktop/api/main.py"
```

### 方法 2: 使用 launchd (macOS 推荐)

创建 `~/Library/LaunchAgents/com.cloudwork.desktop-api.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cloudwork.desktop-api</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/zhanggongqing/project/孵化项目/cloudwork/desktop/api/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/zhanggongqing/project/孵化项目/cloudwork</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>CLOUDWORK_REQUIRE_AUTH</key>
        <string>true</string>
        <key>CLOUDWORK_API_TOKEN</key>
        <string>your-token-here</string>
        <key>API_HOST</key>
        <string>0.0.0.0</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/cloudwork-desktop-api.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cloudwork-desktop-api.err</string>
</dict>
</plist>
```

启动服务：

```bash
launchctl load ~/Library/LaunchAgents/com.cloudwork.desktop-api.plist
```

---

## 安全建议

1. **启用认证**: 生产环境务必设置 `CLOUDWORK_REQUIRE_AUTH=true`
2. **强密码**: API Token 使用随机生成的强密码（至少 32 字符）
3. **Tailscale ACL**: 配置 Tailscale ACL 限制访问来源
4. **定期更换**: 定期更换 API Token

---

## 故障排查

### 无法连接本地节点

```
❌ 无法连接本地节点
http://100.x.x.x:2026
```

**检查步骤：**

1. Desktop API 是否在运行
   ```bash
   ps aux | grep "desktop/api"
   ```

2. Tailscale 是否连接
   ```bash
   tailscale status
   ```

3. 端口是否正确
   ```bash
   curl http://100.x.x.x:2026/health
   ```

4. 防火墙是否放行
   ```bash
   # macOS
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps
   ```

### 认证失败

```
❌ 本地节点错误 (401): Missing authentication token
```

**检查步骤：**

1. Bot 是否设置了 Token
   ```
   /target
   ```
   查看 "API Token" 状态是否显示 "✅ 已设置"

2. Token 是否正确
   - 对比本地环境变量 `echo $CLOUDWORK_API_TOKEN`
   - 和 Bot 中设置的 Token

3. 重新设置
   ```
   /target token your-correct-token
   ```

### 响应超时

```
❌ 本地节点响应超时 (300秒)
```

**可能原因：**

1. 任务执行时间过长
2. 网络不稳定
3. Claude CLI 卡住

**解决方法：**

1. 检查本地 Claude CLI 是否正常
   ```bash
   claude -p "hello" --model haiku
   ```

2. 查看 Desktop API 日志
   ```bash
   tail -f ~/desktop-api.log
   ```

---

## API 端点参考

Desktop API 提供以下端点供 Bot 调用：

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/health` | GET | 否 | 健康检查 |
| `/agent` | POST | 是 | 执行 Claude 任务 (SSE) |
| `/agent/plan` | POST | 是 | 规划模式执行 |
| `/agent/execute` | POST | 是 | 执行计划 |
| `/api/agent/run` | POST | 是 | CloudWork 原生执行 |
| `/api/agent/stop` | POST | 否 | 停止执行 |
| `/ws` | WebSocket | 是* | 实时通信 |

*WebSocket 认证通过 `?token=xxx` 查询参数传递

---

## 完整配置示例

### 本地 Mac 一键启动脚本

创建 `~/start-cloudwork-api.sh`:

```bash
#!/bin/bash

# CloudWork Desktop API 启动脚本

export CLOUDWORK_REQUIRE_AUTH=true
export CLOUDWORK_API_TOKEN="your-secret-token-here"
export API_HOST=0.0.0.0
export API_PORT=2026

cd /Users/zhanggongqing/project/孵化项目/cloudwork

echo "启动 CloudWork Desktop API..."
echo "Tailscale IP: $(tailscale ip -4)"
echo "监听地址: http://0.0.0.0:$API_PORT"
echo "认证: 已启用"

python desktop/api/main.py
```

```bash
chmod +x ~/start-cloudwork-api.sh
~/start-cloudwork-api.sh
```

### Telegram Bot 配置命令

```
/target local http://100.x.x.x:2026
/target token your-secret-token-here
/target
```
