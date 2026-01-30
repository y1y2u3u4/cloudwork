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


# 全局管理器实例
planning_manager: Optional[PlanningManager] = None
ralph_loop_manager = RalphLoopManager()
keyword_mining_manager: Optional[KeywordMiningManager] = None


def init_skills(workspace_dir: str):
    """初始化技能管理器"""
    global planning_manager, keyword_mining_manager
    planning_manager = PlanningManager(workspace_dir)
    keyword_mining_manager = KeywordMiningManager(workspace_dir)
    logger.info("Skills managers initialized (planning, ralph-loop, keyword-mining)")
