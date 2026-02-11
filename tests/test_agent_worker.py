# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from unittest import mock

from app.services.agent_worker import AgentTask, AgentWorker
from app.utils import docker_utils


class DummyAdapter:
    def setup(self, project_path, spec_path, params):
        return self._result("setup", spec_path)

    def new_track(self, project_path, spec_path, params):
        return self._result("new_track", spec_path)

    def implement(self, project_path, spec_path, params):
        return self._result("implement", spec_path)

    def run_custom(self, project_path, spec_path, params):
        return self._result("custom", spec_path)

    @staticmethod
    def _result(action, spec_path):
        return docker_utils.CommandRunResult(
            stdout="ok {}".format(action),
            stderr="",
            returncode=0,
            command=["dummy", action, spec_path or ""],
        )


class FakeRedisService:
    def __init__(self):
        self.results = []
        self.enqueued = []

    def push_agent_result(self, result_payload):
        self.results.append(result_payload)

    def enqueue_agent_task_payload(self, payload):
        self.enqueued.append(payload)


class AgentWorkerTests(unittest.TestCase):
    def test_task_from_dict_accepts_spec(self):
        task = AgentTask.from_dict(
            {
                "agent_kind": "gemini",
                "project_path": "/tmp/project",
                "spec_md_content": "content",
            }
        )
        self.assertEqual(task.artifacts["spec.md"], "content")

    def test_process_agent_job_writes_artifacts(self):
        redis_service = FakeRedisService()
        worker = AgentWorker(redis_service)
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_path = os.path.join(temp_dir, "plan.md")
            with open(plan_path, "w", encoding="utf-8") as plan_file:
                plan_file.write("plan updated")
            job = {
                "agent_kind": "gemini",
                "project_path": temp_dir,
                "spec_md_content": "spec content",
                "task_issue_id": "issue-1",
                "params": {"action": "implement"},
            }
            with mock.patch.object(AgentWorker, "_get_adapter", return_value=DummyAdapter()):
                with mock.patch.object(
                    AgentWorker,
                    "_collect_git_info",
                    return_value={"diff": "", "status": "", "log": ""},
                ):
                    worker.process_agent_job(job)
        self.assertEqual(len(redis_service.results), 1)
        result = redis_service.results[0]
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["stdout"], "ok implement")
        self.assertEqual(result["plan_md"], "plan updated")


if __name__ == "__main__":
    unittest.main()
