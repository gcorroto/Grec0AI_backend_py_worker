# -*- coding: utf-8 -*-
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CommandRunResult:
    stdout: str
    stderr: str
    returncode: int
    command: List[str]


def _build_env_args(env_vars: Optional[Dict[str, str]]) -> List[str]:
    args: List[str] = []
    if not env_vars:
        return args
    for key, value in env_vars.items():
        if value is None:
            continue
        args.extend(["-e", "{}={}".format(key, value)])
    return args


def _build_volume_args(volumes: Optional[Dict[str, str]]) -> List[str]:
    args: List[str] = []
    if not volumes:
        return args
    for host_path, container_path in volumes.items():
        args.extend(["-v", "{}:{}".format(host_path, container_path)])
    return args


def run_container(
    image: str,
    command: List[str],
    env_vars: Optional[Dict[str, str]] = None,
    volumes: Optional[Dict[str, str]] = None,
    workdir: Optional[str] = None,
    timeout: Optional[int] = None,
) -> CommandRunResult:
    docker_command = ["docker", "run", "--rm"]
    docker_command.extend(_build_env_args(env_vars))
    docker_command.extend(_build_volume_args(volumes))
    if workdir:
        docker_command.extend(["-w", workdir])
    docker_command.append(image)
    docker_command.extend(command)
    result = subprocess.run(
        docker_command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CommandRunResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
        command=docker_command,
    )


def run_local(
    command: List[str],
    env_vars: Optional[Dict[str, str]] = None,
    workdir: Optional[str] = None,
    timeout: Optional[int] = None,
) -> CommandRunResult:
    env = os.environ.copy()
    if env_vars:
        env.update({key: str(value) for key, value in env_vars.items() if value is not None})
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=workdir,
        env=env,
    )
    return CommandRunResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
        command=command,
    )
