# CloudWork 快速开始

## 🚀 5分钟快速启动

### 1. 检查系统 (30秒)

```bash
cd /home/claude/vps-cloud-runner/tasks/cloudwork
./check_system.sh
```

预期输出: `✅ All checks passed!`

### 2. 启动 Bot (10秒)

```bash
python3 -m src.bot.main
```

预期输出:
```
INFO - Starting CloudWork Bot...
INFO - Allowed users: [6975672957]
INFO - Bot is starting polling...
```

### 3. Telegram 测试 (2分钟)

打开 Telegram，找到你的 Bot，发送:

```
/start
```

Bot 应该回复帮助信息。

---

## 📱 基本命令

### 快速测试流程

```
1. /start              # 查看帮助
2. /new 测试会话       # 创建新会话
3. 写个 Hello World    # 在会话中对话
4. /sessions           # 查看所有会话
5. /model opus         # 切换到 Opus 模型
6. 再写一个 Flask API  # 继续对话
7. /archived           # 查看归档会话
```

### 所有可用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/start` | 显示帮助信息 | `/start` |
| `/run` | 独立执行任务 | `/run 写个排序算法` |
| `/new` | 创建新会话 | `/new Flask项目` |
| `/sessions` | 查看/切换会话 | `/sessions` |
| `/archived` | 查看归档会话 | `/archived` |
| `/model` | 切换模型 | `/model opus` |
| `/mode` | 切换执行模式 | `/mode plan` |
| `/project` | 切换项目 | `/project myapp` |
| `/settings` | 查看设置 | `/settings` |
| `/status` | 查看运行状态 | `/status` |
| `/cancel` | 取消当前任务 | `/cancel` |
| `/delete` | 删除会话 | `/delete sess_123` |

---

## 🔧 常见操作

### 创建新会话并开始工作

```
你: /new 电商项目
Bot: ✅ 已创建新会话: 电商项目

你: 创建一个商品管理的 CRUD API
Bot: 🔧 正在执行...
     [实时显示 Claude 的输出]
     ✅ 已创建 app.py, models.py, ...
```

### 在现有会话中继续工作

```
你: 添加用户认证功能
Bot: 🔧 正在执行...
     [在同一会话上下文中工作]
```

### 切换会话

```
你: /sessions
Bot: 📋 你的会话:
     [显示会话列表和按钮]

你: [点击某个会话按钮]
Bot: ✅ 已切换到: 电商项目
```

### 回复历史消息

```
你: [回复之前某个会话的消息]
    修复这个 Bug

Bot: 🔄 已切换回该会话
     🔧 正在执行...
```

### 切换模型

```
你: /model opus
Bot: ✅ 已切换到: Claude Opus

你: 帮我重构这段代码
Bot: [使用 Opus 模型执行]
```

### 使用 Plan 模式

```
你: /mode plan
Bot: ✅ 已切换到: 计划模式

你: 实现用户注册功能
Bot: 📋 执行计划:
     1. 创建数据库模型
     2. 实现 API 端点
     3. 添加验证逻辑
     [等待确认]
```

---

## 📊 实时监控

### 查看日志

```bash
# 实时日志
tail -f logs/cloudwork.log

# 最近100行
tail -100 logs/cloudwork.log

# 搜索错误
grep -i error logs/cloudwork.log
```

### 查看运行状态

在 Telegram 发送:
```
/status
```

Bot 回复:
```
📊 系统状态
- 运行时间: 2小时15分钟
- 活跃任务: 0
- 总会话数: 5
- 模型: sonnet
- 执行模式: auto
```

---

## 🛠️ 故障排除

### Bot 无响应

1. 检查 Bot 是否在运行:
   ```bash
   ps aux | grep "src.bot.main"
   ```

2. 查看日志:
   ```bash
   tail -50 logs/cloudwork.log
   ```

3. 重启 Bot:
   ```bash
   pkill -f "src.bot.main"
   python3 -m src.bot.main
   ```

### 执行超时

默认超时 300秒，可在 `config/.env` 修改:
```bash
COMMAND_TIMEOUT=600
```

### 会话丢失

会话数据在 `data/sessions.json`，检查:
```bash
cat data/sessions.json | jq .
```

备份恢复:
```bash
cp data/sessions.json data/sessions.json.backup
```

### API 连接失败

检查网络:
```bash
curl http://80.251.221.185:3000/api
```

检查配置:
```bash
grep ANTHROPIC config/.env
```

---

## 📁 重要文件位置

```
cloudwork/
├── config/.env              # 配置文件 ⚙️
├── data/sessions.json       # 会话数据 💾
├── logs/cloudwork.log       # 运行日志 📋
├── workspace/               # 项目工作空间 📂
├── src/bot/main.py          # Bot 入口 🚀
└── check_system.sh          # 系统检查 ✅
```

---

## 🔄 启动/停止

### 前台运行 (开发)

```bash
python3 -m src.bot.main
```

按 `Ctrl+C` 停止

### 后台运行 (生产)

```bash
# 启动
nohup python3 -m src.bot.main > logs/nohup.log 2>&1 &

# 停止
pkill -f "src.bot.main"

# 查看日志
tail -f logs/nohup.log
```

### 使用 systemd (推荐)

```bash
# 创建服务文件 (如果还没有)
sudo cp scripts/cloudwork.service /etc/systemd/system/

# 启动
sudo systemctl start cloudwork

# 停止
sudo systemctl stop cloudwork

# 重启
sudo systemctl restart cloudwork

# 开机自启
sudo systemctl enable cloudwork

# 查看状态
sudo systemctl status cloudwork

# 查看日志
sudo journalctl -u cloudwork -f
```

---

## 💡 最佳实践

### 1. 会话命名
使用描述性名称:
```
✅ /new 电商后台API
✅ /new 数据爬虫优化
❌ /new 项目1
❌ /new 测试
```

### 2. 模型选择
- **Haiku**: 简单任务 (格式化代码、修复 typo)
- **Sonnet**: 日常开发 (实现功能、重构)
- **Opus**: 复杂任务 (架构设计、难题调试)

### 3. 执行模式
- **Auto**: 快速开发，跳过确认
- **Plan**: 大型重构，先看计划

### 4. 会话管理
- 每个独立任务用新会话
- 定期清理归档会话
- 重要会话手动备份

---

## 📚 更多文档

- [完整功能说明](README.md)
- [测试报告](TEST_REPORT.md)
- [测试总结](TEST_SUMMARY.md)
- [开发指南](CLAUDE.md)

---

## 🆘 获取帮助

在 Telegram 发送 `/start` 查看内置帮助。

查看日志分析问题:
```bash
tail -100 logs/cloudwork.log
```

---

**快速上手**: 5分钟
**完整掌握**: 30分钟
**开始使用**: 现在！

```bash
python3 -m src.bot.main
```
