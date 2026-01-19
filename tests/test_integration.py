#!/usr/bin/env python3
"""
CloudWork Integration Tests

测试核心功能的集成测试脚本
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.services.session import SessionManager, Session
from src.bot.services.claude import ClaudeExecutor


def test_session_manager():
    """测试会话管理器"""
    print("\n" + "="*60)
    print("测试 SessionManager")
    print("="*60)

    # 创建临时数据目录
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager(data_dir=tmpdir)

        # 测试 1: 创建用户数据
        print("\n[测试 1] 创建用户数据")
        user_id = 123456789
        user_data = manager.get_or_create_user_data(user_id)
        print(f"✓ 用户数据创建成功: model={user_data.model}, mode={user_data.execution_mode}")

        # 测试 2: 创建会话
        print("\n[测试 2] 创建会话")
        session_id = "test_session_001"
        session = manager.create_session(
            user_id=user_id,
            session_id=session_id,
            name="测试会话"
        )
        print(f"✓ 会话创建成功: id={session.id}, name={session.name}")

        # 测试 3: 获取活跃会话
        print("\n[测试 3] 获取活跃会话")
        active_id = manager.get_active_session_id(user_id)
        assert active_id == session_id
        print(f"✓ 活跃会话正确: {active_id}")

        # 测试 4: 更新会话
        print("\n[测试 4] 更新会话")
        manager.update_session(user_id, session_id, name="更新后的名称")
        session_data = manager.get_session(user_id, session_id)
        assert session_data["name"] == "更新后的名称"
        print(f"✓ 会话更新成功: name={session_data['name']}")

        # 测试 5: 创建多个会话
        print("\n[测试 5] 创建多个会话")
        session2 = manager.create_session(user_id, "test_session_002", "第二个会话")
        session3 = manager.create_session(user_id, "test_session_003", "第三个会话")
        all_sessions = manager.get_all_sessions(user_id)
        assert len(all_sessions) == 3
        print(f"✓ 多会话创建成功: 共 {len(all_sessions)} 个会话")

        # 测试 6: 归档会话
        print("\n[测试 6] 归档会话")
        manager.archive_session(user_id, session_id)
        archived = manager.get_archived_sessions(user_id)
        assert len(archived) == 1
        print(f"✓ 会话归档成功: 已归档 {len(archived)} 个会话")

        # 测试 7: 恢复归档会话
        print("\n[测试 7] 恢复归档会话")
        manager.unarchive_session(user_id, session_id)
        archived = manager.get_archived_sessions(user_id)
        assert len(archived) == 0
        active_id = manager.get_active_session_id(user_id)
        assert active_id == session_id
        print(f"✓ 会话恢复成功")

        # 测试 8: 删除会话
        print("\n[测试 8] 删除会话")
        deleted = manager.delete_session(user_id, session_id)
        assert deleted
        all_sessions = manager.get_all_sessions(user_id)
        assert len(all_sessions) == 2
        print(f"✓ 会话删除成功: 剩余 {len(all_sessions)} 个会话")

        # 测试 9: 用户设置
        print("\n[测试 9] 用户设置管理")
        manager.set_user_model(user_id, "opus")
        assert manager.get_user_model(user_id) == "opus"
        manager.set_user_execution_mode(user_id, "plan")
        assert manager.get_user_execution_mode(user_id) == "plan"
        manager.set_user_project(user_id, "my_project")
        assert manager.get_user_project(user_id) == "my_project"
        print(f"✓ 用户设置管理成功")

        # 测试 10: 持久化
        print("\n[测试 10] 数据持久化")
        sessions_file = os.path.join(tmpdir, "sessions.json")
        assert os.path.exists(sessions_file)

        with open(sessions_file) as f:
            data = json.load(f)

        assert str(user_id) in data
        assert data[str(user_id)]["model"] == "opus"
        assert data[str(user_id)]["execution_mode"] == "plan"
        print(f"✓ 数据持久化成功")

        # 测试 11: 重新加载
        print("\n[测试 11] 重新加载数据")
        manager2 = SessionManager(data_dir=tmpdir)
        assert manager2.get_user_model(user_id) == "opus"
        assert len(manager2.get_all_sessions(user_id)) == 2
        print(f"✓ 数据重新加载成功")

        # 测试 12: 消息映射
        print("\n[测试 12] 消息-会话映射")
        message_id = 999888777
        manager.map_message_to_session(message_id, "test_session_002")
        mapped_session = manager.get_session_from_message(message_id)
        assert mapped_session == "test_session_002"
        print(f"✓ 消息映射成功")

        # 测试 13: 临时会话 ID
        print("\n[测试 13] 临时会话 ID 生成")
        pending_id = SessionManager.generate_pending_session_id(user_id)
        assert pending_id.startswith("pending_")
        assert SessionManager.is_pending_session(pending_id)
        assert not SessionManager.is_pending_session("test_session_002")
        print(f"✓ 临时会话 ID: {pending_id}")

    print("\n" + "="*60)
    print("✅ SessionManager 所有测试通过！")
    print("="*60)


def test_claude_executor():
    """测试 Claude 执行器"""
    print("\n" + "="*60)
    print("测试 ClaudeExecutor")
    print("="*60)

    executor = ClaudeExecutor()

    # 测试 1: 项目发现
    print("\n[测试 1] 项目发现")
    projects = executor.projects
    print(f"✓ 发现 {len(projects)} 个项目:")
    for name, path in projects.items():
        print(f"  - {name}: {path}")

    # 测试 2: 获取项目目录
    print("\n[测试 2] 获取项目目录")
    default_dir = executor.get_project_dir("default")
    print(f"✓ 默认项目目录: {default_dir}")

    # 测试 3: 构建环境变量
    print("\n[测试 3] 构建环境变量")
    env = executor.build_claude_env()
    print(f"✓ 环境变量准备完成 ({len(env)} 个变量)")

    # 测试 4: UUID 验证
    print("\n[测试 4] UUID 验证")
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    invalid_uuid = "not-a-uuid"
    assert executor.is_valid_uuid(valid_uuid)
    assert not executor.is_valid_uuid(invalid_uuid)
    print(f"✓ UUID 验证功能正常")

    # 测试 5: 构建命令
    print("\n[测试 5] 构建 Claude CLI 命令")

    # 无会话 ID
    cmd1 = executor.build_command("test prompt", None, "sonnet", "auto")
    print(f"✓ 无会话命令: {' '.join(cmd1)}")
    assert "claude" in cmd1
    assert "--dangerously-skip-permissions" in cmd1
    assert "--model" in cmd1
    assert "sonnet" in cmd1

    # 有效会话 ID
    cmd2 = executor.build_command("test prompt", valid_uuid, "opus", "auto")
    print(f"✓ 有会话命令: {' '.join(cmd2)}")
    assert "--resume" in cmd2
    assert valid_uuid in cmd2

    # pending 会话 ID（应被忽略）
    cmd3 = executor.build_command("test prompt", "pending_123_abc", "haiku", "auto")
    print(f"✓ pending 会话命令: {' '.join(cmd3)}")
    assert "--resume" not in cmd3

    # plan 模式
    cmd4 = executor.build_command("test prompt", None, "sonnet", "plan")
    print(f"✓ plan 模式命令: {' '.join(cmd4)}")
    assert "--permission-mode" in cmd4
    assert "plan" in cmd4
    assert "--dangerously-skip-permissions" not in cmd4

    print("\n" + "="*60)
    print("✅ ClaudeExecutor 所有测试通过！")
    print("="*60)


def test_data_structure():
    """测试数据结构"""
    print("\n" + "="*60)
    print("测试数据结构")
    print("="*60)

    # 测试 Session
    print("\n[测试 1] Session 数据类")
    session = Session(
        id="test_id",
        name="测试会话",
        created_at="2026-01-19T10:00:00",
        last_active="2026-01-19T10:30:00",
        message_count=5
    )

    # 转换为字典
    session_dict = session.to_dict()
    print(f"✓ Session 转字典: {json.dumps(session_dict, ensure_ascii=False)}")

    # 从字典创建
    session2 = Session.from_dict(session_dict)
    assert session2.id == session.id
    assert session2.name == session.name
    print(f"✓ Session 从字典创建成功")

    print("\n" + "="*60)
    print("✅ 数据结构测试通过！")
    print("="*60)


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print(" "*15 + "CloudWork 集成测试")
    print("="*70)

    try:
        test_data_structure()
        test_session_manager()
        test_claude_executor()

        print("\n" + "="*70)
        print(" "*20 + "🎉 所有测试通过！")
        print("="*70 + "\n")

        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
