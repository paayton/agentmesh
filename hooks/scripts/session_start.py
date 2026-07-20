#!/usr/bin/env python3
"""AgentMesh SessionStart hook.

VS Code 智能体会话开始时触发:
  1. 从 stdin 读官方 hook payload（含 session_id / cwd / hook_event_name）。
  2. 调 agentmesh-api /api/hooks/resolve 拿本工作区绑定的 asset variants。
  3. 逐个 kit unpack 到 .github/（触发 VS Code 热加载）。
  4. 通过 stdout 返 `{"continue": true, "systemMessage": ...}` 让 VS Code 显示绑定信息。

失败策略：任何异常都以 exit 0 + `continue:true` 返回，避免阻塞用户会话；
异常内容通过 systemMessage 提示，并写到本地日志。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def log(msg: str) -> None:
    """写审计日志到工作区 .agentmesh/logs/session_start.log。"""
    cwd = Path(os.environ.get("AGENTMESH_LOG_DIR", ".agentmesh/logs"))
    cwd.mkdir(parents=True, exist_ok=True)
    with (cwd / "session_start.log").open("a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")


def http_post(url: str, token: str | None, payload: dict[str, Any], timeout: int = 15) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - 内网调用
        return json.loads(resp.read().decode("utf-8"))


def kit_unpack(kit_ref: str, dest: Path) -> None:
    """调 `kit unpack` 落盘 ModelKit。失败抛异常，由上层记日志。"""
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603 - kit 由用户显式安装
        ["kit", "unpack", kit_ref, "-d", str(dest), "--overwrite"],
        check=True,
        capture_output=True,
    )


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
    log(f"[SessionStart] session_id={session_id} cwd={workspace_root}")

    api = os.environ.get("AGENTMESH_API")
    client_id = os.environ.get("AGENTMESH_CLIENT_ID")
    token = os.environ.get("AGENTMESH_TOKEN")

    if not api or not client_id:
        emit({
            "continue": True,
            "systemMessage": "[AgentMesh] AGENTMESH_API 或 AGENTMESH_CLIENT_ID 未配置，跳过资产解析。",
        })
        return 0

    try:
        result = http_post(
            f"{api.rstrip('/')}/api/hooks/resolve",
            token,
            {"clientId": client_id, "workspaceRoot": workspace_root},
        )
    except (urllib.error.URLError, TimeoutError) as exc:
        log(f"[SessionStart] resolve failed: {exc}")
        emit({
            "continue": True,
            "systemMessage": f"[AgentMesh] variant 解析失败，使用本地缓存资产：{exc}",
        })
        return 0

    assignments = result.get("assignments", []) or []
    if not assignments:
        emit({
            "continue": True,
            "systemMessage": "[AgentMesh] 本工作区未绑定任何资产。",
        })
        return 0

    dest_root = Path(workspace_root) / ".github"
    loaded, failed = [], []
    for a in assignments:
        kit_ref = a.get("kitRef")
        version = a.get("version", "")
        asset_id = a.get("assetId", "")
        if not kit_ref:
            continue
        try:
            kit_unpack(kit_ref, dest_root)
            loaded.append(f"{asset_id}@{version}")
        except subprocess.CalledProcessError as exc:
            log(f"[SessionStart] kit unpack failed ref={kit_ref}: {exc.stderr!r}")
            failed.append(f"{asset_id}@{version}")

    msg = "[AgentMesh] 已加载资产：" + ", ".join(loaded) if loaded else "[AgentMesh] 无资产落盘。"
    if failed:
        msg += "；失败：" + ", ".join(failed)
    log(f"[SessionStart] {msg}")
    emit({"continue": True, "systemMessage": msg})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - hook 必须永不阻塞
        log(f"[SessionStart] fatal: {exc!r}")
        emit({"continue": True, "systemMessage": f"[AgentMesh] SessionStart 异常：{exc}"})
        sys.exit(0)
