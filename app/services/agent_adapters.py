# -*- coding: utf-8 -*-
import os
import shlex
from typing import Dict, List, Optional

from app.utils import docker_utils


class AgentAdapter:
    agent_kind = "base"
    default_cli_cmd = ""
    default_docker_image = ""

    def __init__(self):
        self.cli_cmd = self._get_env_value("CLI_CMD", self.default_cli_cmd)
        self.spec_args = self._get_spec_args()
        self.use_docker = self._get_env_value("USE_DOCKER", "true").lower() != "false"
        self.docker_image = self._get_env_value("DOCKER_IMAGE", self.default_docker_image)
        self.workspace_dir = self._get_env_value("WORKDIR", "/workspace")

    def setup(self, project_path: str, spec_path: Optional[str], params: Optional[Dict]) -> docker_utils.CommandRunResult:
        return self._run_action("setup", project_path, spec_path, params, "setup_args")

    def new_track(self, project_path: str, spec_path: Optional[str], params: Optional[Dict]) -> docker_utils.CommandRunResult:
        return self._run_action("new_track", project_path, spec_path, params, "new_track_args")

    def implement(self, project_path: str, spec_path: Optional[str], params: Optional[Dict]) -> docker_utils.CommandRunResult:
        return self._run_action("implement", project_path, spec_path, params, "implement_args")

    def run_custom(self, project_path: str, spec_path: Optional[str], params: Optional[Dict]) -> docker_utils.CommandRunResult:
        params = params or {}
        command_override = params.get("command")
        if command_override:
            command = self._parse_command(command_override)
        else:
            action = params.get("action")
            extra_args = self._normalize_args(params.get("args"))
            command = self._build_command(action, spec_path, extra_args)
        return self._run_command(command, project_path, params.get("env"), params.get("timeout"))

    def _get_env_value(self, suffix: str, default: str) -> str:
        kind_key = "AGENT_{}_{}".format(self.agent_kind.upper(), suffix)
        return os.getenv(kind_key, os.getenv("AGENT_{}".format(suffix), default))

    def _get_spec_args(self) -> List[str]:
        spec_args_env = os.getenv("AGENT_SPEC_ARGS")
        if spec_args_env is None:
            return ["--spec"]
        if spec_args_env.strip() == "":
            return []
        return shlex.split(spec_args_env)

    def _run_action(
        self,
        action: str,
        project_path: str,
        spec_path: Optional[str],
        params: Optional[Dict],
        args_key: str,
    ) -> docker_utils.CommandRunResult:
        params = params or {}
        extra_args = self._normalize_args(params.get(args_key))
        command = self._build_command(action, spec_path, extra_args)
        return self._run_command(command, project_path, params.get("env"), params.get("timeout"))

    def _build_command(
        self,
        action: Optional[str],
        spec_path: Optional[str],
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        if not self.cli_cmd:
            raise ValueError("CLI command no configurado para el agente {}".format(self.agent_kind))
        command = self._parse_command(self.cli_cmd)
        if action:
            command.append(action)
        if extra_args:
            command.extend(extra_args)
        if spec_path:
            command.extend(self.spec_args)
            command.append(spec_path)
        return command

    def _run_command(
        self,
        command: List[str],
        project_path: str,
        env_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> docker_utils.CommandRunResult:
        env_payload = {"AGENT_KIND": self.agent_kind}
        if env_vars:
            env_payload.update(env_vars)
        if self.use_docker:
            return docker_utils.run_container(
                self.docker_image,
                command,
                env_vars=env_payload,
                volumes={project_path: self.workspace_dir},
                workdir=self.workspace_dir,
                timeout=timeout,
            )
        return docker_utils.run_local(
            command,
            env_vars=env_payload,
            workdir=project_path,
            timeout=timeout,
        )

    @staticmethod
    def _parse_command(command: str) -> List[str]:
        if isinstance(command, list):
            return list(command)
        return shlex.split(command)

    @staticmethod
    def _normalize_args(args: Optional[List[str]]) -> Optional[List[str]]:
        if args is None:
            return None
        if isinstance(args, str):
            return shlex.split(args)
        return list(args)


class GeminiAdapter(AgentAdapter):
    agent_kind = "gemini"
    default_cli_cmd = "gemini"
    default_docker_image = "gemini-cli:latest"


class ClaudeAdapter(AgentAdapter):
    agent_kind = "claude"
    default_cli_cmd = "claude"
    default_docker_image = "claude-cli:latest"


class CodexAdapter(AgentAdapter):
    agent_kind = "codex"
    default_cli_cmd = "codex"
    default_docker_image = "codex-cli:latest"


class CopilotAdapter(AgentAdapter):
    agent_kind = "copilot"
    default_cli_cmd = "copilot"
    default_docker_image = "copilot-cli:latest"
