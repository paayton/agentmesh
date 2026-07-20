#!/usr/bin/env python3
"""AgentMesh Stop hook.

VS Code 智能体会话结束时触发:
  1. 从 stdin 读官方 hook payload（含 session_id / cwd / transcript_path）。
  2. 从 transcript_path 生成 metadata + tool_calls 摘要（不含原始对话）。
  3. 如果 AGENTMESH_UPLOAD_TRANSCRIPT=true，附带 transcript_ref（本机路径），
     供中台去标识化 pipeline 拉取；默认只传 metadata。
  4. POST /api/sessions/ingest，中台再转 Langfuse trace。

失败策略：exit 0，异常写日志；不阻塞用户 session 结束。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def log(msg: str) -> None:
    cwd = Path(os.environ.get("AGENTMESH_LOG_DIR", ".agentmesh/logs"))
    cwd.mkdir(parents=True, exist_ok=True)
    with (cwd / "stop.log").open("a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")


def http_post(url: str, token: str | None, payload: dict[str, Any], timeout: int = 15) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def summarize_transcript(path: str | None) -> dict[str, Any]:
    """从 transcript 文件里抽 metadata：轮次数、工具调用统计。

    注意：transcript 格式非稳定 API（VS Code 官方文档 §Common input fields 明确提醒），
    这里只做尽力而为的粗统计，不解析结构化字段。
    """
    summary: dict[str, Any] = {"turns": 0, "toolCalls": {}, "sizeBytes": 0}
    if not path:
        return summary
    p = Path(path)
    if not p.is_file():
        return summary
    summary["sizeBytes"] = p.stat().st_size
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return summary
    # 极简统计：按行数近似轮次；正则匹配常见工具名
    summary["turns"] = text.count('"role"')
    for tool in ("editFiles", "runTerminalCommand", "createFile", "readFile", "searchWorkspace"):
        c = text.count(f'"{tool}"')
        if c:
            summary["toolCalls"][tool] = c
    return summary


def emit(output: dict[str, Any]) -> None:
    json.dump(output, sys.stdout)
    sys.stdout.write("\n")


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    session_id = payload.get("session_id", "")
    workspace_root = payload.get("cwd") or os.getcwd()
    transcript_path = payload.get("transcript_path")

    api = os.environ.get("AGENTMESH_API")
    client_id = os.environ.get("AGENTMESH_CLIENT_ID")
    token = os.environ.get("AGENTMESH_TOKEN")
    upload_transcript = os.environ.get("AGENTMESH_UPLOAD_TRANSCRIPT", "").lower() == "true"

    if not api or not client_id:
        log("[Stop] AGENTMESH_API 或 AGENTMESH_CLIENT_ID 未配置，跳过 ingest。")
        emit({"continue": True})
        return 0

    body: dict[str, Any] = {
        "sessionId": session_id,
        "clientId": client_id,
        "workspaceRoot": workspace_root,
        "toolCallsSummary": summarize_transcript(transcript_path),
    }
    if upload_transcript and transcript_path:
        body["transcriptRef"] = transcript_path

    try:
        http_post(f"{api.rstrip('/')}/api/sessions/ingest", token, body)
        log(f"[Stop] ingest ok session_id={session_id}")
    except (urllib.error.URLError, TimeoutError) as exc:
        log(f"[Stop] ingest failed: {exc}")

    emit({"continue": True})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"[Stop] fatal: {exc!r}")
        emit({"continue": True})
        sys.exit(0)
