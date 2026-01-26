"""
CloudWork Desktop API Bridge

将 CloudWork 的 Python 后端服务暴露给 React 前端。
复用现有的 session/memory/claude 服务，不影响 Telegram Bot。

端口: 2026 (开发) / 2620 (生产)
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Optional, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# 将 cloudwork 根目录加入 path，复用现有模块
cloudwork_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, cloudwork_root)

from src.bot.services.session import session_manager
from src.bot.services.claude import claude_executor, AVAILABLE_MODELS, EXECUTION_MODES
from src.bot.services.memory import get_memory_manager, init_memory
from src.utils.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CloudWork Desktop API", version="0.1.0")

# CORS - 允许前端开发服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://localhost:5173", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化记忆系统
data_dir = os.path.join(cloudwork_root, "data")
init_memory(data_dir)

# 默认用户 ID (桌面端单用户)
DESKTOP_USER_ID = int(os.environ.get("DESKTOP_USER_ID", "0"))


# =================== Health ===================

@app.get("/health")
async def health():
    return {"status": "ok", "service": "cloudwork-desktop"}


# =================== Sessions ===================

@app.get("/api/sessions")
async def list_sessions():
    """获取所有会话"""
    sessions = session_manager.get_all_sessions(DESKTOP_USER_ID, include_archived=False)
    active_id = session_manager.get_active_session_id(DESKTOP_USER_ID)
    return {
        "sessions": sessions,
        "active_session_id": active_id
    }


@app.post("/api/sessions")
async def create_session(data: Optional[Dict[str, Any]] = None):
    """创建新会话"""
    name = data.get("name") if data else None
    if name:
        session_manager.set_pending_name(DESKTOP_USER_ID, name)
    else:
        user_data = session_manager.get_or_create_user_data(DESKTOP_USER_ID)
        user_data.active = None
        session_manager.save_sessions()
    return {"status": "ok"}


@app.post("/api/sessions/{session_id}/switch")
async def switch_session(session_id: str):
    """切换会话"""
    session_manager.set_active_session(DESKTOP_USER_ID, session_id)
    return {"status": "ok", "session_id": session_id}


@app.get("/api/sessions/archived")
async def list_archived():
    """获取归档会话"""
    sessions = session_manager.get_archived_sessions(DESKTOP_USER_ID)
    return {"sessions": sessions}


# =================== Agent (Claude 执行) ===================
# 兼容 WorkAny 前端 API 格式

# 活跃进程追踪 (session_id -> process)
_active_processes: Dict[str, Any] = {}


def _make_claude_sse_stream(prompt: str, session_id: Optional[str], model: str, mode: str):
    """创建 Claude CLI SSE 流 - 兼容 WorkAny 前端消息格式"""

    async def event_stream():
        if not session_id:
            active_id = session_manager.get_active_session_id(DESKTOP_USER_ID)
        else:
            active_id = session_id

        work_dir = claude_executor.get_user_project_dir(DESKTOP_USER_ID)
        cmd = claude_executor.build_command(prompt, active_id, model, mode)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            env=claude_executor.build_claude_env(),
            limit=16 * 1024 * 1024
        )

        new_session_id = active_id
        accumulated_text = ""

        # 追踪进程
        track_id = new_session_id or "default"
        _active_processes[track_id] = process

        try:
            while True:
                try:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(), timeout=300
                    )
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'error', 'content': 'Timeout'})}\n\n"
                    break

                if not line_bytes:
                    break

                line_text = line_bytes.decode('utf-8', errors='replace').strip()
                if not line_text:
                    continue

                if line_text.startswith('{'):
                    try:
                        event = json.loads(line_text)
                        event_type = event.get("type", "")

                        if event_type == "system":
                            sid = event.get("session_id")
                            if sid:
                                new_session_id = sid
                                _active_processes[sid] = process
                            yield f"data: {json.dumps({'type': 'session', 'sessionId': sid})}\n\n"

                        elif event_type == "assistant":
                            message = event.get("message", {})
                            for block in message.get("content", []):
                                if block.get("type") == "text":
                                    text = block.get("text", "")
                                    accumulated_text += text
                                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"
                                elif block.get("type") == "tool_use":
                                    yield f"data: {json.dumps({'type': 'tool_use', 'name': block.get('name', ''), 'input': block.get('input', {}), 'toolUseId': block.get('id', '')})}\n\n"

                        elif event_type == "user":
                            for block in event.get("content", []):
                                if block.get("type") == "tool_result":
                                    yield f"data: {json.dumps({'type': 'tool_result', 'toolUseId': block.get('tool_use_id', ''), 'output': str(block.get('content', ''))[:500]})}\n\n"

                        elif event_type == "result":
                            result_text = event.get("result", "")
                            if result_text and not accumulated_text.strip():
                                accumulated_text = result_text
                            yield f"data: {json.dumps({'type': 'done', 'sessionId': new_session_id})}\n\n"

                    except json.JSONDecodeError:
                        pass

            await process.wait()
            yield f"data: {json.dumps({'type': 'done', 'sessionId': new_session_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            _active_processes.pop(track_id, None)
            _active_processes.pop(new_session_id or "", None)
            if process.returncode is None:
                process.terminate()
                await process.wait()

    return event_stream()


def _sse_response(stream):
    """构造 SSE 响应"""
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# WorkAny 兼容端点: POST /agent (直接执行)
@app.post("/agent")
async def agent_direct(data: Dict[str, Any]):
    """直接执行 - 兼容 WorkAny useAgent.ts"""
    prompt = data.get("prompt", "")
    model_config = data.get("modelConfig") or {}
    model = model_config.get("model", session_manager.get_user_model(DESKTOP_USER_ID))
    if model not in AVAILABLE_MODELS:
        model = session_manager.get_user_model(DESKTOP_USER_ID)

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    stream = _make_claude_sse_stream(prompt, None, model, "auto")
    return _sse_response(stream)


# WorkAny 兼容端点: POST /agent/plan (生成计划)
@app.post("/agent/plan")
async def agent_plan(data: Dict[str, Any]):
    """规划模式 - 使用 Claude plan mode"""
    prompt = data.get("prompt", "")
    model_config = data.get("modelConfig") or {}
    model = model_config.get("model", session_manager.get_user_model(DESKTOP_USER_ID))
    if model not in AVAILABLE_MODELS:
        model = session_manager.get_user_model(DESKTOP_USER_ID)

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    stream = _make_claude_sse_stream(prompt, None, model, "plan")
    return _sse_response(stream)


# WorkAny 兼容端点: POST /agent/execute (执行已批准计划)
@app.post("/agent/execute")
async def agent_execute(data: Dict[str, Any]):
    """执行计划 - 实际上 CloudWork 直接用 auto 模式"""
    prompt = data.get("prompt", "")
    model_config = data.get("modelConfig") or {}
    model = model_config.get("model", session_manager.get_user_model(DESKTOP_USER_ID))
    if model not in AVAILABLE_MODELS:
        model = session_manager.get_user_model(DESKTOP_USER_ID)

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    stream = _make_claude_sse_stream(prompt, None, model, "auto")
    return _sse_response(stream)


# WorkAny 兼容端点: POST /agent/stop/{session_id}
@app.post("/agent/stop/{session_id}")
async def agent_stop_session(session_id: str):
    """停止指定会话"""
    process = _active_processes.get(session_id)
    if process and process.returncode is None:
        process.terminate()
        await process.wait()
        _active_processes.pop(session_id, None)
        return {"status": "ok", "stopped": session_id}
    return {"status": "not_found"}


# WorkAny 兼容端点: POST /agent/permission
@app.post("/agent/permission")
async def agent_permission(data: Dict[str, Any]):
    """权限响应 - CloudWork auto 模式无需权限"""
    return {"status": "ok"}


# CloudWork 自有端点
@app.post("/api/agent/run")
async def agent_run(data: Dict[str, Any]):
    """CloudWork 原生执行端点"""
    prompt = data.get("prompt", "")
    session_id = data.get("session_id")
    model = data.get("model", session_manager.get_user_model(DESKTOP_USER_ID))
    mode = data.get("mode", "auto")

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    stream = _make_claude_sse_stream(prompt, session_id, model, mode)
    return _sse_response(stream)


@app.post("/api/agent/stop")
async def agent_stop():
    """停止所有执行"""
    stopped = 0
    for sid, process in list(_active_processes.items()):
        if process.returncode is None:
            process.terminate()
            stopped += 1
    _active_processes.clear()
    return {"status": "ok", "cancelled": stopped}


# =================== Provider 兼容层 ===================
# WorkAny 前端调用的 Provider API

@app.get("/providers/agents")
async def get_agent_providers():
    """Agent 提供商列表 - 返回 CloudWork 作为唯一提供商"""
    return {
        "current": "claude-cli",
        "available": [
            {"type": "claude-cli", "name": "Claude CLI", "description": "CloudWork Claude CLI executor"}
        ]
    }


@app.get("/providers/agents/available")
async def get_available_agents():
    return [{"type": "claude-cli", "name": "Claude CLI"}]


@app.get("/providers/sandbox")
async def get_sandbox_providers():
    """沙箱提供商 - CloudWork 不使用沙箱"""
    return {"current": "native", "available": [{"type": "native", "name": "Native (VPS)"}]}


@app.get("/providers/sandbox/available")
async def get_available_sandbox():
    return [{"type": "native", "name": "Native (VPS)"}]


@app.post("/providers/settings/sync")
async def sync_provider_settings(data: Dict[str, Any] = None):
    """同步设置"""
    return {"status": "ok"}


@app.get("/providers/config")
async def get_provider_config():
    return {"agentProvider": "claude-cli", "sandboxProvider": "native"}


# =================== 健康检查兼容 ===================

@app.get("/health/dependencies")
async def health_dependencies():
    """依赖检查"""
    return {"dependencies": [], "allInstalled": True}


# =================== 文件兼容端点 ===================

@app.post("/files/readdir")
async def files_readdir(data: Dict[str, Any] = None):
    """读取目录"""
    path = data.get("path", "") if data else ""
    work_dir = claude_executor.get_user_project_dir(DESKTOP_USER_ID)
    target = os.path.join(work_dir, path) if path else work_dir

    if not os.path.exists(target):
        return {"entries": []}

    entries = []
    for item in sorted(os.listdir(target)):
        if item.startswith('.'):
            continue
        full_path = os.path.join(target, item)
        entries.append({
            "name": item,
            "isDirectory": os.path.isdir(full_path),
            "path": os.path.join(path, item) if path else item
        })

    return {"entries": entries}


@app.get("/files/skills-dir")
async def files_skills_dir():
    """技能目录"""
    skills_dir = os.path.join(cloudwork_root, "skills")
    return {"path": skills_dir}


# =================== MCP 兼容端点 ===================

@app.get("/mcp/all-configs")
async def mcp_all_configs():
    """MCP 配置 - CloudWork 暂无 MCP"""
    return {"configs": []}


# =================== Settings ===================

@app.get("/api/settings")
async def get_settings():
    """获取当前设置"""
    return {
        "model": session_manager.get_user_model(DESKTOP_USER_ID),
        "mode": session_manager.get_user_execution_mode(DESKTOP_USER_ID),
        "project": session_manager.get_user_project(DESKTOP_USER_ID),
        "available_models": AVAILABLE_MODELS,
        "available_modes": EXECUTION_MODES,
        "projects": list(claude_executor.projects.keys()),
    }


@app.post("/api/settings")
async def update_settings(data: Dict[str, Any]):
    """更新设置"""
    if "model" in data:
        session_manager.set_user_model(DESKTOP_USER_ID, data["model"])
    if "mode" in data:
        session_manager.set_user_execution_mode(DESKTOP_USER_ID, data["mode"])
    if "project" in data:
        session_manager.set_user_project(DESKTOP_USER_ID, data["project"])
    return {"status": "ok"}


# =================== Memory ===================

@app.get("/api/memory")
async def get_memory_status():
    """获取记忆系统状态"""
    mm = get_memory_manager()
    if not mm:
        raise HTTPException(status_code=500, detail="Memory system not initialized")
    return mm.get_status()


@app.get("/api/memory/search")
async def search_memory(keyword: str):
    """搜索记忆"""
    mm = get_memory_manager()
    if not mm:
        raise HTTPException(status_code=500, detail="Memory system not initialized")
    results = mm.search(keyword)
    return {"results": results}


@app.get("/api/memory/learned")
async def list_learned():
    """列出学习的模式"""
    mm = get_memory_manager()
    if not mm:
        raise HTTPException(status_code=500, detail="Memory system not initialized")
    patterns = mm.list_learned()
    # 序列化 datetime
    for p in patterns:
        if "modified" in p:
            p["modified"] = p["modified"].isoformat()
    return {"patterns": patterns}


@app.get("/api/memory/forget/preview")
async def forget_preview():
    """遗忘预览"""
    mm = get_memory_manager()
    if not mm:
        raise HTTPException(status_code=500, detail="Memory system not initialized")
    candidates = mm.get_forgettable_memories(threshold=25.0)
    return {"candidates": candidates}


@app.post("/api/memory/forget")
async def forget_confirm():
    """执行遗忘"""
    mm = get_memory_manager()
    if not mm:
        raise HTTPException(status_code=500, detail="Memory system not initialized")
    deleted = mm.forget(auto=True, threshold=25.0, dry_run=False)
    return {"deleted": deleted, "count": len(deleted)}


# =================== Projects ===================

@app.get("/api/projects")
async def list_projects():
    """列出可用项目"""
    return {
        "projects": [
            {"name": name, "path": path}
            for name, path in claude_executor.projects.items()
        ],
        "current": session_manager.get_user_project(DESKTOP_USER_ID)
    }


# =================== WebSocket (实时通信) ===================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点，用于实时双向通信

    消息格式:
    { "type": "ping" } → { "type": "pong" }
    { "type": "run", "prompt": "..." } → 流式结果
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "run":
                prompt = data.get("prompt", "")
                session_id = data.get("session_id")
                model = data.get("model", "sonnet")

                work_dir = claude_executor.get_user_project_dir(DESKTOP_USER_ID)
                cmd = claude_executor.build_command(prompt, session_id, model, "auto")

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=work_dir,
                    env=claude_executor.build_claude_env(),
                    limit=16 * 1024 * 1024
                )

                while True:
                    try:
                        line_bytes = await asyncio.wait_for(
                            process.stdout.readline(), timeout=300
                        )
                    except asyncio.TimeoutError:
                        await websocket.send_json({"type": "error", "content": "Timeout"})
                        break

                    if not line_bytes:
                        break

                    line_text = line_bytes.decode('utf-8', errors='replace').strip()
                    if line_text.startswith('{'):
                        try:
                            event = json.loads(line_text)
                            await websocket.send_json(event)
                        except json.JSONDecodeError:
                            pass

                await process.wait()
                await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("API_PORT", "2026"))
    uvicorn.run(app, host="0.0.0.0", port=port)
