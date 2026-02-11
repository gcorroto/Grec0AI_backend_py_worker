# -*- coding: utf-8 -*-
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.services.agent_adapters import (
    AgentAdapter,
    ClaudeAdapter,
    CodexAdapter,
    CopilotAdapter,
    GeminiAdapter,
)

def _read_int_env(env_key: str, default: int) -> int:
    raw_value = os.getenv(env_key)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(
            "Valor inválido para {}: {}".format(env_key, raw_value)
        ) from exc


DEFAULT_MAX_RETRIES = _read_int_env("AGENT_MAX_RETRIES", 2)


@dataclass
class AgentTask:
    agent_kind: str
    project_path: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    task_issue_id: Optional[str] = None
    attempt: int = 0
    max_retries: int = 0

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AgentTask":
        if not payload:
            raise ValueError("Payload de agente vacío")
        agent_kind = payload.get("agent_kind")
        project_path = payload.get("project_path")
        if not agent_kind or not project_path:
            raise ValueError("agent_kind y project_path son requeridos")
        artifacts = cls._normalize_artifacts(payload.get("artifacts"))
        spec_md_content = payload.get("spec_md_content")
        if spec_md_content is not None and "spec.md" not in artifacts:
            artifacts["spec.md"] = spec_md_content
        params = payload.get("params") or {}
        max_retries = payload.get("max_retries")
        if max_retries is None:
            max_retries = DEFAULT_MAX_RETRIES
        return cls(
            agent_kind=agent_kind,
            project_path=project_path,
            artifacts=artifacts,
            params=params,
            task_issue_id=payload.get("task_issue_id"),
            attempt=int(payload.get("attempt", 0)),
            max_retries=int(max_retries),
        )

    def to_payload(self) -> Dict[str, Any]:
        return {
            "agent_kind": self.agent_kind,
            "project_path": self.project_path,
            "artifacts": self.artifacts,
            "params": self.params,
            "task_issue_id": self.task_issue_id,
            "attempt": self.attempt,
            "max_retries": self.max_retries,
        }

    @staticmethod
    def _normalize_artifacts(raw_artifacts: Any) -> Dict[str, str]:
        if not raw_artifacts:
            return {}
        normalized: Dict[str, str] = {}
        if isinstance(raw_artifacts, list):
            for item in raw_artifacts:
                if not isinstance(item, dict):
                    continue
                name = item.get("path") or item.get("name")
                if not name:
                    continue
                content = item.get("content", "")
                normalized[name] = str(content)
            return normalized
        if isinstance(raw_artifacts, dict):
            for name, content in raw_artifacts.items():
                if isinstance(content, dict) and "content" in content:
                    content = content.get("content", "")
                normalized[name] = str(content)
            return normalized
        return normalized


class AgentWorker:
    def __init__(self, redis_service):
        self.redis_service = redis_service
        self.adapters = {
            "gemini": GeminiAdapter,
            "claude": ClaudeAdapter,
            "codex": CodexAdapter,
            "copilot": CopilotAdapter,
        }

    def process_agent_job(self, job_payload: Dict[str, Any]) -> None:
        try:
            task = AgentTask.from_dict(job_payload)
        except Exception as exc:
            self.redis_service.push_agent_result(
                {
                    "status": "failed",
                    "error": str(exc),
                    "raw_payload": job_payload,
                }
            )
            return
        try:
            self._validate_task(task)
            self._write_artifacts(task.project_path, task.artifacts)
            spec_path = self._resolve_spec_path(task)
            adapter = self._get_adapter(task.agent_kind)
            run_result = self._run_action(adapter, task, spec_path)
            git_info = self._collect_git_info(task.project_path)
            plan_content = self._read_optional_file(
                task.project_path, task.params.get("plan_filename", "plan.md")
            )
            result_payload = {
                "task_issue_id": task.task_issue_id,
                "agent_kind": task.agent_kind,
                "project_path": task.project_path,
                "status": "success" if run_result.returncode == 0 else "failed",
                "stdout": run_result.stdout,
                "stderr": run_result.stderr,
                "returncode": run_result.returncode,
                "command": run_result.command,
                "git_diff": git_info.get("diff"),
                "git_status": git_info.get("status"),
                "git_log": git_info.get("log"),
                "plan_md": plan_content,
                "artifacts": list(task.artifacts.keys()),
                "attempt": task.attempt,
                "max_retries": task.max_retries,
            }
            if run_result.returncode == 0:
                self.redis_service.push_agent_result(result_payload)
            else:
                self._handle_failure(task, result_payload, run_result.stderr)
        except Exception as exc:
            error_payload = {
                "task_issue_id": task.task_issue_id,
                "agent_kind": task.agent_kind,
                "project_path": task.project_path,
                "status": "failed",
                "error": str(exc),
                "attempt": task.attempt,
                "max_retries": task.max_retries,
            }
            self._handle_failure(task, error_payload, str(exc))

    def _validate_task(self, task: AgentTask) -> None:
        if not os.path.isdir(task.project_path):
            raise FileNotFoundError(
                "project_path no existe: {}".format(task.project_path)
            )

    def _get_adapter(self, agent_kind: str) -> AgentAdapter:
        adapter_cls = self.adapters.get(agent_kind)
        if not adapter_cls:
            raise ValueError("Agente no soportado: {}".format(agent_kind))
        return adapter_cls()

    def _run_action(self, adapter: AgentAdapter, task: AgentTask, spec_path: Optional[str]):
        action = (task.params.get("action") or "implement").lower()
        if action == "setup":
            return adapter.setup(task.project_path, spec_path, task.params)
        if action in {"new_track", "newtrack"}:
            return adapter.new_track(task.project_path, spec_path, task.params)
        if action == "implement":
            return adapter.implement(task.project_path, spec_path, task.params)
        return adapter.run_custom(task.project_path, spec_path, task.params)

    def _write_artifacts(self, project_path: str, artifacts: Dict[str, str]) -> None:
        for relative_path, content in artifacts.items():
            target_path = self._safe_join(project_path, relative_path)
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as artifact_file:
                artifact_file.write(content)

    def _resolve_spec_path(self, task: AgentTask) -> Optional[str]:
        spec_filename = task.params.get("spec_filename", "spec.md")
        candidate_path = os.path.join(task.project_path, spec_filename)
        if os.path.exists(candidate_path):
            return spec_filename
        for artifact_name in task.artifacts:
            if artifact_name.endswith("spec.md"):
                return artifact_name
        return None

    def _collect_git_info(self, project_path: str) -> Dict[str, Optional[str]]:
        return {
            "diff": self._run_git_command(project_path, ["diff"]),
            "status": self._run_git_command(project_path, ["status", "--porcelain"]),
            "log": self._run_git_command(project_path, ["log", "-n", "5", "--oneline"]),
        }

    def _run_git_command(self, project_path: str, args: list) -> Optional[str]:
        result = subprocess.run(
            ["git"] + args,
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def _read_optional_file(self, project_path: str, filename: Optional[str]) -> Optional[str]:
        if not filename:
            return None
        target_path = self._safe_join(project_path, filename)
        if not os.path.exists(target_path):
            return None
        with open(target_path, "r", encoding="utf-8") as source_file:
            return source_file.read()

    def _handle_failure(self, task: AgentTask, payload: Dict[str, Any], error: str) -> None:
        if task.attempt < task.max_retries:
            task.attempt += 1
            retry_payload = task.to_payload()
            retry_payload["last_error"] = error
            self.redis_service.enqueue_agent_task_payload(retry_payload)
            payload["retrying"] = True
        else:
            payload["retrying"] = False
        self.redis_service.push_agent_result(payload)

    @staticmethod
    def _safe_join(root: str, relative_path: str) -> str:
        normalized = os.path.normpath(relative_path).lstrip(os.sep)
        full_path = os.path.abspath(os.path.join(root, normalized))
        root_path = os.path.abspath(root)
        if full_path == root_path:
            raise ValueError("Ruta de artefacto inválida: {}".format(relative_path))
        try:
            common_path = os.path.commonpath([root_path, full_path])
        except ValueError as exc:
            raise ValueError("Ruta de artefacto inválida: {}".format(relative_path)) from exc
        if common_path != root_path:
            raise ValueError("Ruta de artefacto inválida: {}".format(relative_path))
        return full_path
