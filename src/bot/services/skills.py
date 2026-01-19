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


# 全局管理器实例
planning_manager: Optional[PlanningManager] = None
ralph_loop_manager = RalphLoopManager()


def init_skills(workspace_dir: str):
    """初始化技能管理器"""
    global planning_manager
    planning_manager = PlanningManager(workspace_dir)
    logger.info("Skills managers initialized")
