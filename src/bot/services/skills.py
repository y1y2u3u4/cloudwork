"""
CloudWork Skills Service

实现 planning-with-files 和 ralph-loop 两个技能的核心逻辑
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ============ Planning-with-Files Skill ============

PLANNING_PROMPT_PREFIX = """[PLANNING MODE ACTIVATED]

你正在使用 planning-with-files 模式执行复杂任务。这个模式将帮助你：
- 创建结构化的任务计划
- 记录发现和中间结果
- 追踪执行进度

核心原则：
1. Context Window = RAM, Filesystem = Disk
2. 先写计划，再执行
3. 2-action rule: 每执行 2 个操作后，将发现写入 findings.md
4. Read before decide: 执行前先读取相关计划文件
5. Update after act: 执行后更新 progress.md

请先创建以下文件结构（如果不存在）：
- task_plan.md: 任务计划和步骤分解
- findings.md: 研究发现和中间结果
- progress.md: 执行进度追踪

然后开始执行用户的任务：

"""

TASK_PLAN_TEMPLATE = """# Task Plan

## Objective
{objective}

## Created
{created}

## Steps
- [ ] Step 1: [待填写]
- [ ] Step 2: [待填写]
- [ ] Step 3: [待填写]

## Critical Files
- [待发现]

## Key Decisions
- [待记录]

## Risk Areas
- [待识别]
"""

FINDINGS_TEMPLATE = """# Findings

## Session: {session}

### Discoveries
- [记录你的发现]

### Code Patterns
- [记录代码模式]

### Dependencies
- [记录依赖关系]
"""

PROGRESS_TEMPLATE = """# Progress

## Current Status: Planning

## Completed Steps
- [x] Started planning session

## In Progress
- [ ] [当前进行中的步骤]

## Blocked
- [阻塞项]

## Last Updated
{updated}
"""


class PlanningManager:
    """Planning-with-files 技能管理器"""

    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir

    def get_planning_dir(self, project_dir: str) -> str:
        """获取项目的计划目录"""
        planning_dir = os.path.join(project_dir, '.claude', 'planning')
        return planning_dir

    def ensure_planning_files(self, project_dir: str, objective: str = "") -> Dict[str, str]:
        """确保计划文件存在，返回文件路径"""
        planning_dir = self.get_planning_dir(project_dir)

        # 创建目录
        os.makedirs(planning_dir, exist_ok=True)

        files = {
            'task_plan': os.path.join(planning_dir, 'task_plan.md'),
            'findings': os.path.join(planning_dir, 'findings.md'),
            'progress': os.path.join(planning_dir, 'progress.md')
        }

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 创建 task_plan.md
        if not os.path.exists(files['task_plan']):
            with open(files['task_plan'], 'w', encoding='utf-8') as f:
                f.write(TASK_PLAN_TEMPLATE.format(
                    objective=objective or "[待填写]",
                    created=now
                ))
            logger.info(f"Created task_plan.md in {planning_dir}")

        # 创建 findings.md
        if not os.path.exists(files['findings']):
            with open(files['findings'], 'w', encoding='utf-8') as f:
                f.write(FINDINGS_TEMPLATE.format(session=now[:10]))
            logger.info(f"Created findings.md in {planning_dir}")

        # 创建 progress.md
        if not os.path.exists(files['progress']):
            with open(files['progress'], 'w', encoding='utf-8') as f:
                f.write(PROGRESS_TEMPLATE.format(updated=now))
            logger.info(f"Created progress.md in {planning_dir}")

        return files

    def build_planning_prompt(self, original_prompt: str, project_dir: str) -> str:
        """构建带有计划模式前缀的 prompt"""
        # 确保计划文件存在
        files = self.ensure_planning_files(project_dir, original_prompt)

        # 构建完整的 prompt
        full_prompt = PLANNING_PROMPT_PREFIX + original_prompt

        return full_prompt

    def get_planning_status(self, project_dir: str) -> Optional[Dict[str, Any]]:
        """获取计划状态"""
        planning_dir = self.get_planning_dir(project_dir)

        if not os.path.exists(planning_dir):
            return None

        status = {
            'exists': True,
            'files': {}
        }

        for filename in ['task_plan.md', 'findings.md', 'progress.md']:
            filepath = os.path.join(planning_dir, filename)
            if os.path.exists(filepath):
                stat = os.stat(filepath)
                status['files'][filename] = {
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                }

        return status

    def clear_planning(self, project_dir: str) -> bool:
        """清除计划文件"""
        planning_dir = self.get_planning_dir(project_dir)

        if not os.path.exists(planning_dir):
            return False

        import shutil
        try:
            shutil.rmtree(planning_dir)
            logger.info(f"Cleared planning directory: {planning_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear planning: {e}")
            return False


# ============ Ralph-Loop Skill ============

RALPH_LOOP_PROMPT_SUFFIX = """

[RALPH LOOP MODE]

当前迭代: {iteration}/{max_iterations}
完成承诺: {completion_promise}

重要指令:
1. 完成任务后，在输出末尾添加确切的完成标记: {completion_promise}
2. 如果任务尚未完成，不要添加完成标记
3. 如果遇到问题需要更多迭代，描述剩余工作并继续
4. 每次迭代都应该取得实质性进展

{additional_context}
"""


class RalphLoopManager:
    """Ralph-Loop 技能管理器"""

    DEFAULT_COMPLETION_PROMISE = "RALPH_DONE"
    DEFAULT_MAX_ITERATIONS = 10

    def __init__(self):
        # 存储活跃的 Ralph Loop 状态
        # key: (user_id, session_id), value: RalphLoopState
        self.active_loops: Dict[Tuple[int, str], 'RalphLoopState'] = {}

    def start_loop(
        self,
        user_id: int,
        session_id: str,
        original_prompt: str,
        completion_promise: Optional[str] = None,
        max_iterations: Optional[int] = None
    ) -> 'RalphLoopState':
        """启动一个 Ralph Loop"""
        state = RalphLoopState(
            original_prompt=original_prompt,
            completion_promise=completion_promise or self.DEFAULT_COMPLETION_PROMISE,
            max_iterations=max_iterations or self.DEFAULT_MAX_ITERATIONS,
            current_iteration=0
        )

        key = (user_id, session_id)
        self.active_loops[key] = state

        logger.info(f"Started Ralph Loop for user {user_id}, session {session_id[:8]}...")
        return state

    def get_loop(self, user_id: int, session_id: str) -> Optional['RalphLoopState']:
        """获取 Ralph Loop 状态"""
        key = (user_id, session_id)
        return self.active_loops.get(key)

    def stop_loop(self, user_id: int, session_id: str) -> bool:
        """停止 Ralph Loop"""
        key = (user_id, session_id)
        if key in self.active_loops:
            del self.active_loops[key]
            logger.info(f"Stopped Ralph Loop for user {user_id}")
            return True
        return False

    def build_iteration_prompt(
        self,
        state: 'RalphLoopState',
        previous_output: Optional[str] = None
    ) -> str:
        """构建迭代 prompt"""
        state.current_iteration += 1

        # 构建额外上下文（包含上一次迭代的输出摘要）
        additional_context = ""
        if previous_output:
            # 截取最后 2000 字符作为上下文
            context_snippet = previous_output[-2000:] if len(previous_output) > 2000 else previous_output
            additional_context = f"\n上一次迭代的输出摘要:\n{context_snippet}\n"

        # 第一次迭代使用原始 prompt
        if state.current_iteration == 1:
            base_prompt = state.original_prompt
        else:
            # 后续迭代使用精简的继续提示
            base_prompt = f"继续执行任务: {state.original_prompt[:200]}..."

        # 添加 Ralph Loop 后缀
        suffix = RALPH_LOOP_PROMPT_SUFFIX.format(
            iteration=state.current_iteration,
            max_iterations=state.max_iterations,
            completion_promise=state.completion_promise,
            additional_context=additional_context
        )

        return base_prompt + suffix

    def check_completion(self, state: 'RalphLoopState', output: str) -> bool:
        """检查是否完成"""
        # 检查输出中是否包含完成承诺
        if state.completion_promise in output:
            state.completed = True
            logger.info(f"Ralph Loop completed with promise: {state.completion_promise}")
            return True

        # 检查是否达到最大迭代次数
        if state.current_iteration >= state.max_iterations:
            state.max_iterations_reached = True
            logger.warning(f"Ralph Loop reached max iterations: {state.max_iterations}")
            return True

        return False

    def get_status_text(self, state: 'RalphLoopState') -> str:
        """获取状态文本"""
        if state.completed:
            return f"✅ Ralph Loop 完成 (迭代 {state.current_iteration}/{state.max_iterations})"
        elif state.max_iterations_reached:
            return f"⚠️ Ralph Loop 达到最大迭代次数 ({state.max_iterations})"
        else:
            return f"🔄 Ralph Loop 进行中 (迭代 {state.current_iteration}/{state.max_iterations})"


class RalphLoopState:
    """Ralph Loop 状态"""

    def __init__(
        self,
        original_prompt: str,
        completion_promise: str,
        max_iterations: int,
        current_iteration: int = 0
    ):
        self.original_prompt = original_prompt
        self.completion_promise = completion_promise
        self.max_iterations = max_iterations
        self.current_iteration = current_iteration
        self.completed = False
        self.max_iterations_reached = False
        self.iteration_outputs: list = []
        self.started_at = datetime.now()

    def add_output(self, output: str):
        """添加迭代输出"""
        self.iteration_outputs.append({
            'iteration': self.current_iteration,
            'output': output,
            'timestamp': datetime.now().isoformat()
        })

    def get_total_duration(self) -> str:
        """获取总耗时"""
        delta = datetime.now() - self.started_at
        minutes = int(delta.total_seconds() // 60)
        seconds = int(delta.total_seconds() % 60)
        return f"{minutes}分{seconds}秒"


# ============ Keyword Mining Skill ============

KEYWORD_MINING_PROMPT = """[KEYWORD MINING MODE - SEO 关键词挖掘专家]

你现在是一个专业的 SEO 关键词挖掘专家。请按照以下 SOP 流程进行系统性的关键词挖掘。

## 挖掘目标
领域: {niche}
方向: {direction}
目标: 找到高价值、低竞争的关键词机会

## 执行 SOP 流程

### Phase 1: 种子词扩展
使用以下策略扩展关键词：

**修饰词矩阵:**
- 意图词: best, top, free, cheap, online, no signup
- 对比词: vs, versus, alternative, alternatives to, like
- 问题词: what is, how to, how does, is, can, why
- 场景词: for beginners, for business, for students, for marketing
- 时间词: 2024, 2025, new, latest

**扩展公式:**
```
[修饰词] + [核心词]          → "best ai video generator"
[核心词] + [场景]            → "ai tools for marketing"
[产品名] + alternative       → "sora alternative free"
[产品A] vs [产品B]          → "runway vs pika"
how to + [动作] + [工具]    → "how to use midjourney"
```

### Phase 2: 机会评估
对每个关键词进行评分 (使用 WebSearch 验证):

| 指标 | 权重 | 评分标准 |
|------|------|---------|
| 搜索意图匹配 | 30% | 是否有明确的用户需求 |
| 竞争程度 | 30% | SERP 首页是否有弱站 |
| 商业价值 | 20% | 是否能导向产品/变现 |
| 内容可行性 | 20% | 是否容易产出优质内容 |

**机会等级:**
- 🔥 蓝海词: 高需求 + 低竞争 + 高商业价值
- ⭐ 优质词: 中高需求 + 中等竞争
- ✓ 可做词: 有需求 + 可突破
- ○ 观望词: 暂不建议

### Phase 3: SERP 分析
对高分词进行 SERP 分析：
1. 搜索该关键词
2. 分析 TOP 10 结果
3. 识别内容缺口
4. 评估排名可能性

### Phase 4: 输出格式

**关键词机会报告:**

```markdown
# {niche} 关键词机会报告

## 📊 挖掘概览
- 分析种子词: X 个
- 扩展关键词: X 个
- 筛选机会词: X 个

## 🔥 TOP 10 蓝海词机会

| 序号 | 关键词 | 预估搜索量 | 竞争度 | 机会评级 | 内容建议 |
|-----|-------|----------|-------|---------|---------|
| 1 | xxx | 高/中/低 | 低/中/高 | 🔥/⭐/✓ | 榜单/对比/教程 |

## 📝 内容规划建议

### 优先创作 (本周)
1. [标题建议] - 目标词: xxx
2. ...

### 中期规划 (本月)
1. ...

### 长期布局
1. ...

## 🎯 细分方向建议
- 方向A: [具体建议]
- 方向B: [具体建议]
```

---

现在开始执行关键词挖掘任务:

{user_prompt}

---

**执行要求:**
1. 使用 WebSearch 工具验证关键词的真实搜索情况
2. 分析 SERP 竞争情况
3. 输出结构化的机会报告
4. 给出可执行的内容建议
"""

# 预定义的热门产品词库
PRODUCT_KEYWORDS = {
    "video": ["sora", "runway", "pika", "heygen", "synthesia", "kling", "luma", "invideo"],
    "image": ["midjourney", "dall-e", "stable diffusion", "leonardo", "ideogram", "firefly", "canva ai"],
    "agent": ["autogpt", "babyagi", "crewai", "langchain", "manus", "devin", "claude computer use"],
    "writing": ["jasper", "copy ai", "writesonic", "grammarly", "notion ai", "chatgpt"],
    "code": ["github copilot", "cursor", "tabnine", "codeium", "replit ai"],
}

# 场景词库
SCENE_KEYWORDS = {
    "audience": ["for beginners", "for business", "for students", "for marketing", "for developers", "for designers", "for content creators"],
    "platform": ["for youtube", "for tiktok", "for instagram", "for twitter", "for linkedin"],
    "use_case": ["for ecommerce", "for real estate", "for education", "for healthcare"],
}


class KeywordMiningManager:
    """Keyword Mining 技能管理器"""

    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.data_dir = os.path.join(workspace_dir, 'data', 'keyword_mining')

    def get_mining_dir(self, project_dir: str) -> str:
        """获取关键词挖掘数据目录"""
        mining_dir = os.path.join(project_dir, '.claude', 'keyword_mining')
        return mining_dir

    def ensure_mining_files(self, project_dir: str, niche: str = "") -> Dict[str, str]:
        """确保挖掘相关文件存在"""
        mining_dir = self.get_mining_dir(project_dir)
        os.makedirs(mining_dir, exist_ok=True)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_str = datetime.now().strftime("%Y%m%d")

        files = {
            'report': os.path.join(mining_dir, f'report_{date_str}.md'),
            'keywords': os.path.join(mining_dir, f'keywords_{date_str}.json'),
            'history': os.path.join(mining_dir, 'mining_history.json')
        }

        # 初始化历史记录文件
        if not os.path.exists(files['history']):
            import json
            with open(files['history'], 'w', encoding='utf-8') as f:
                json.dump({
                    "created": now,
                    "sessions": []
                }, f, ensure_ascii=False, indent=2)

        return files

    def build_mining_prompt(
        self,
        user_prompt: str,
        niche: str = "AI Tools",
        direction: str = "general"
    ) -> str:
        """构建关键词挖掘 prompt"""
        return KEYWORD_MINING_PROMPT.format(
            niche=niche,
            direction=direction,
            user_prompt=user_prompt
        )

    def parse_niche_from_prompt(self, prompt: str) -> Tuple[str, str]:
        """从用户 prompt 中解析 niche 和 direction"""
        prompt_lower = prompt.lower()

        # 检测方向
        direction = "general"
        direction_keywords = {
            "video": ["video", "视频", "sora", "runway"],
            "image": ["image", "图片", "图像", "midjourney", "art"],
            "agent": ["agent", "智能体", "自动化", "autogpt"],
            "writing": ["writing", "写作", "文案", "copywriting"],
            "code": ["code", "coding", "编程", "开发"],
        }

        for dir_name, keywords in direction_keywords.items():
            for kw in keywords:
                if kw in prompt_lower:
                    direction = dir_name
                    break

        # 检测 niche
        niche = "AI Tools"
        if "seo" in prompt_lower:
            niche = "SEO Tools"
        elif "ai" in prompt_lower or "人工智能" in prompt_lower:
            niche = "AI Tools"

        return niche, direction

    def get_product_keywords(self, direction: str) -> list:
        """获取特定方向的产品关键词"""
        return PRODUCT_KEYWORDS.get(direction, [])

    def get_expansion_suggestions(self, seed: str, direction: str = "general") -> Dict[str, list]:
        """获取关键词扩展建议"""
        products = self.get_product_keywords(direction)

        suggestions = {
            "modifier_combos": [
                f"best {seed}",
                f"free {seed}",
                f"top {seed} 2025",
                f"{seed} online",
                f"{seed} no signup",
            ],
            "question_combos": [
                f"what is {seed}",
                f"how to use {seed}",
                f"is {seed} free",
            ],
            "alternative_combos": [
                f"{p} alternative" for p in products[:5]
            ],
            "comparison_combos": [
                f"{products[i]} vs {products[i+1]}"
                for i in range(min(3, len(products)-1))
            ] if len(products) > 1 else [],
            "scene_combos": [
                f"{seed} {scene}"
                for scene in SCENE_KEYWORDS["audience"][:4]
            ]
        }

        return suggestions

    def get_mining_status(self, project_dir: str) -> Optional[Dict[str, Any]]:
        """获取挖掘状态"""
        mining_dir = self.get_mining_dir(project_dir)

        if not os.path.exists(mining_dir):
            return None

        status = {
            'exists': True,
            'reports': [],
            'total_keywords': 0
        }

        # 扫描报告文件
        for filename in os.listdir(mining_dir):
            if filename.startswith('report_') and filename.endswith('.md'):
                filepath = os.path.join(mining_dir, filename)
                stat = os.stat(filepath)
                status['reports'].append({
                    'filename': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                })

        return status


# ============ Transcribe Skill ============

# ============ 音频来源解析器 ============

# 已知的音频分享平台 URL 模式 → 解析方法
# Plaud: https://web.plaud.cn/share/{share_id}
PLAUD_SHARE_PATTERN = r'https?://web\.plaud\.cn/share/([a-zA-Z0-9]+)'


async def resolve_audio_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    解析音频 URL，支持直接音频链接和平台分享链接

    支持的来源：
    - 直接音频 URL（.mp3/.m4a/.wav/.ogg 等）→ 原样返回
    - Plaud 分享链接 → 调用 API 获取临时下载 URL

    Args:
        url: 用户提供的 URL

    Returns:
        (audio_url, filename) — 音频下载地址和文件名，失败返回 (None, None)
    """
    import re
    import httpx

    url = url.strip()

    # 1. Plaud 分享链接
    plaud_match = re.match(PLAUD_SHARE_PATTERN, url)
    if plaud_match:
        share_id = plaud_match.group(1)
        return await _resolve_plaud_url(share_id)

    # 2. 直接音频 URL（以音频扩展名结尾，忽略 query string）
    audio_ext_pattern = re.compile(
        r'https?://\S+\.(?:mp3|m4a|wav|ogg|flac|aac|wma|opus|webm)(?:\?\S*)?$',
        re.IGNORECASE
    )
    if audio_ext_pattern.match(url):
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        filename = os.path.basename(unquote(parsed.path)) or "audio.mp3"
        return url, filename

    return None, None


async def _resolve_plaud_url(share_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    从 Plaud 分享 ID 获取音频下载 URL

    Plaud API 流程：
    1. GET /file/share-content/{share_id} → 获取文件信息（文件名、时长等）
    2. GET /file/share-file-temp/{share_id} → 获取 S3 临时下载 URL（1小时有效）
    """
    import httpx

    api_base = "https://api.plaud.cn"
    headers = {
        "Content-Type": "application/json",
        "app-platform": "web",
        "edit-from": "web",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 获取文件信息
            info_resp = await client.get(
                f"{api_base}/file/share-content/{share_id}",
                headers=headers
            )
            info_data = info_resp.json()

            filename = "plaud_recording.mp3"
            if info_data.get("status") == 0:
                data_file = info_data.get("data_file", {})
                ori_fullname = data_file.get("ori_fullname", "")
                if ori_fullname:
                    filename = ori_fullname
                duration_ms = data_file.get("duration", 0)
                logger.info(
                    f"Plaud 文件: {filename}, "
                    f"时长: {duration_ms // 1000}s, "
                    f"大小: {data_file.get('filesize', 0)} bytes"
                )

            # 获取临时下载 URL
            temp_resp = await client.get(
                f"{api_base}/file/share-file-temp/{share_id}",
                headers=headers
            )
            temp_data = temp_resp.json()

            if temp_data.get("status") == 0 and temp_data.get("temp_url"):
                return temp_data["temp_url"], filename

            logger.error(f"Plaud 获取下载 URL 失败: {temp_data}")
            return None, None

    except Exception as e:
        logger.error(f"Plaud URL 解析失败: {e}")
        return None, None


# ============ Transcribe Skill ============

TRANSCRIBE_TEMPLATES = {
    "meeting": {
        "name": "会议纪要",
        "emoji": "📋",
        "prompt": (
            "请将以下语音转录文本整理为结构化的会议纪要。\n\n"
            "要求：\n"
            "1. 按讨论主题分节，每节包含讨论要点和关键数据\n"
            "2. 用表格列出关键决议（决议 | 详情）\n"
            "3. 提取所有 Action Items，用 checklist 格式，标注责任人和时间\n"
            "4. 口语化内容（对对对、嗯嗯）需过滤，保留实质信息\n"
            "5. 使用清晰的 Markdown 格式，包含二级和三级标题\n\n"
            "转录文本：\n{text}"
        ),
    },
    "summary": {
        "name": "内容摘要",
        "emoji": "📝",
        "prompt": (
            "请将以下语音转录文本提炼为简洁的内容摘要。\n\n"
            "要求：\n"
            "1. 提取核心观点和关键信息\n"
            "2. 按逻辑分层归纳，使用二级标题分节\n"
            "3. 保留重要的数据、名称和结论\n"
            "4. 过滤口语化表达和重复内容\n"
            "5. 摘要长度控制在原文的 20%-30%\n\n"
            "转录文本：\n{text}"
        ),
    },
    "todo": {
        "name": "待办提取",
        "emoji": "✅",
        "prompt": (
            "请从以下语音转录文本中提取所有行动项和待办事项。\n\n"
            "要求：\n"
            "1. 提取所有明确或隐含的任务和行动项\n"
            "2. 标注优先级（高/中/低）\n"
            "3. 标注责任人和截止时间（如有提及）\n"
            "4. 使用 checklist 格式输出：- [ ] **[优先级]** 任务描述 @责任人 截止时间\n\n"
            "转录文本：\n{text}"
        ),
    },
    "article": {
        "name": "文章整理",
        "emoji": "📰",
        "prompt": (
            "请将以下口述内容整理为一篇通顺、有条理的文章。\n\n"
            "要求：\n"
            "1. 去除口语化表达、重复和语气词（嗯、对对对、然后等）\n"
            "2. 理顺逻辑结构，添加合适的段落划分和小标题\n"
            "3. 保留原意，不添加未提及的内容\n"
            "4. 使用清晰的 Markdown 格式输出\n\n"
            "口述内容：\n{text}"
        ),
    },
    "raw": {
        "name": "仅转录",
        "emoji": "📄",
        "prompt": None,  # 不加工，直接返回转录文本
    },
}


class TranscribeManager:
    """音频转录 + 文字加工技能管理器"""

    @staticmethod
    def build_process_prompt(template_key: str, transcribed_text: str) -> Optional[str]:
        """
        根据模版构建加工 prompt

        Args:
            template_key: 模版 key (meeting/summary/todo/article/raw)
            transcribed_text: 转录文本

        Returns:
            加工 prompt，raw 模版返回 None
        """
        template = TRANSCRIBE_TEMPLATES.get(template_key)
        if not template:
            return None

        prompt_tpl = template.get("prompt")
        if prompt_tpl is None:
            return None

        return prompt_tpl.format(text=transcribed_text)

    @staticmethod
    def get_template_keyboard(user_id: int):
        """
        构建模版选择的 InlineKeyboard

        Args:
            user_id: 用户 ID（用于回调数据）

        Returns:
            InlineKeyboardMarkup
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = [
            [
                InlineKeyboardButton(
                    "📋 会议纪要",
                    callback_data=f"transcribe_tpl:meeting:{user_id}"
                ),
                InlineKeyboardButton(
                    "📝 内容摘要",
                    callback_data=f"transcribe_tpl:summary:{user_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "✅ 待办提取",
                    callback_data=f"transcribe_tpl:todo:{user_id}"
                ),
                InlineKeyboardButton(
                    "📰 文章整理",
                    callback_data=f"transcribe_tpl:article:{user_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📄 仅转录",
                    callback_data=f"transcribe_tpl:raw:{user_id}"
                ),
                InlineKeyboardButton(
                    "✏️ 自定义提示",
                    callback_data=f"transcribe_custom:{user_id}"
                ),
            ],
        ]

        return InlineKeyboardMarkup(keyboard)


transcribe_manager = TranscribeManager()


# 全局管理器实例
planning_manager: Optional[PlanningManager] = None
ralph_loop_manager = RalphLoopManager()
keyword_mining_manager: Optional[KeywordMiningManager] = None


def init_skills(workspace_dir: str):
    """初始化技能管理器"""
    global planning_manager, keyword_mining_manager
    planning_manager = PlanningManager(workspace_dir)
    keyword_mining_manager = KeywordMiningManager(workspace_dir)
    logger.info("Skills managers initialized (planning, ralph-loop, keyword-mining, transcribe)")
