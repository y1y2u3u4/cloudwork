# CloudWork 快速开始

5 分钟让你的 Claude 在云端跑起来！

## 📋 准备工作

开始前，你需要准备：

| 项目 | 获取方式 |
|------|----------|
| **Telegram Bot Token** | 在 Telegram 搜索 `@BotFather`，发送 `/newbot` 创建机器人 |
| **你的 User ID** | 在 Telegram 搜索 `@userinfobot`，发送任意消息获取 |
| **Claude API** | [Anthropic Console](https://console.anthropic.com/) 或自定义代理 |

## 🚀 三步启动

### 第一步：安装

```bash
# 克隆项目
git clone https://github.com/y1y2u3u4/cloudwork.git
cd cloudwork

# 安装依赖
pip install -r requirements.txt
```

### 第二步：配置

```bash
# 复制配置模板
cp config/.env.example config/.env

# 编辑配置文件
nano config/.env
```

填入以下内容：

```bash
# Telegram 配置
TELEGRAM_BOT_TOKEN=你的Bot Token
TELEGRAM_ALLOWED_USERS=你的User ID

# Claude API (官方)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 或者使用代理
# ANTHROPIC_BASE_URL=https://your-proxy.com/api
# ANTHROPIC_AUTH_TOKEN=your_token
```

### 第三步：启动

```bash
python -m src.bot.main
```

看到以下输出说明启动成功：

```
INFO - Starting CloudWork Bot...
INFO - Allowed users: [你的UserID]
INFO - Bot is starting polling...
```

## ✅ 验证安装

打开 Telegram，找到你的 Bot，发送：

```
/start
```

Bot 回复帮助信息 = 安装成功！🎉

---

## 📱 基本使用

### 快速测试流程

```
1. /start              # 查看帮助
2. /new 测试会话       # 创建新会话
3. 写个 Hello World    # 发送任务
4. /sessions           # 查看所有会话
5. /model              # 切换模型
```

### 核心命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/new` | 创建新会话 | `/new Flask项目` |
| `/run` | 独立执行（不影响会话）| `/run 写个排序算法` |
| `/sessions` | 查看/切换会话 | `/sessions` |
| `/model` | 切换模型 | `/model` 然后选择 |
| `/settings` | 所有设置 | `/settings` |

### 两种对话方式

**1. 直接发消息** → 在当前会话中继续

```
你: 创建一个用户登录API
Bot: [执行中...]

你: 加上密码加密
Bot: [在同一会话继续...]
```

**2. 回复历史消息** → 自动切回那个会话

```
[回复之前的消息]
你: 修复这个Bug
Bot: 🔄 已切换回该会话，继续执行...
```

---

## 🔧 常见场景

### 场景 1：开始新项目

```
/new 电商后台
帮我设计用户管理模块
```

### 场景 2：快速查询（不保留历史）

```
/run Python 如何读取 JSON 文件
```

### 场景 3：切换到更强的模型

```
/model
→ 选择 opus
帮我分析这个内存泄漏问题
```

### 场景 4：管理多个项目

```
/project
→ 切换到 myapp 项目
修复首页的显示问题
```

---

## 🚀 生产部署

### 方式一：systemd 服务（推荐）

```bash
# 复制服务文件
sudo cp scripts/cloudwork.service /etc/systemd/system/

# 启动服务
sudo systemctl start cloudwork
sudo systemctl enable cloudwork  # 开机自启

# 查看状态
sudo systemctl status cloudwork

# 查看日志
sudo journalctl -u cloudwork -f
```

### 方式二：Docker

```bash
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 方式三：后台运行

```bash
nohup python -m src.bot.main > logs/bot.log 2>&1 &
```

---

## 🛠️ 故障排除

### Bot 无响应

```bash
# 检查进程
ps aux | grep "src.bot.main"

# 检查日志
tail -50 logs/cloudwork.log

# 重启
pkill -f "src.bot.main" && python -m src.bot.main
```

### 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `Unauthorized` | Bot Token 错误 | 检查 `TELEGRAM_BOT_TOKEN` |
| `User not allowed` | 用户未授权 | 检查 `TELEGRAM_ALLOWED_USERS` |
| `API Error` | Claude API 问题 | 检查 API Key 或网络 |
| `Command timeout` | 执行超时 | 增加 `COMMAND_TIMEOUT` 值 |

---

## 📁 重要文件

```
cloudwork/
├── config/.env              # 配置文件 ⚙️
├── data/sessions.json       # 会话数据 💾
├── logs/cloudwork.log       # 运行日志 📋
├── workspace/               # 项目工作空间 📂
└── src/bot/main.py          # Bot 入口 🚀
```

---

## 💡 最佳实践

### 1. 会话命名

```
✅ /new 电商后台API
✅ /new 数据爬虫优化
❌ /new 项目1
❌ /new 测试
```

### 2. 模型选择

| 模型 | 适用场景 |
|------|----------|
| **Haiku** | 简单任务：格式化、小修改 |
| **Sonnet** | 日常开发：写功能、重构 |
| **Opus** | 复杂任务：架构设计、疑难调试 |

### 3. 执行模式

| 模式 | 适用场景 |
|------|----------|
| **Auto** | 快速开发，自动执行 |
| **Plan** | 大型重构，先看计划再执行 |

---

**快速上手**: 5 分钟
**完全掌握**: 30 分钟
**立即开始**: 👇

```bash
git clone https://github.com/y1y2u3u4/cloudwork.git && cd cloudwork
```
