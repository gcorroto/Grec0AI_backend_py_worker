import os
import shutil
import socket
import subprocess
import tempfile
from typing import Optional


class FrontendService:
    def __init__(self, redis_service):
        self.redis_service = redis_service

    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def deploy_frontend(self, image: str, deployment_id: str, port: Optional[int] = None) -> str:
        """Run the given image exposing it on a host port and return the URL."""
        host_port = port or self._get_free_port()
        container_name = f"frontend_{deployment_id}"
        self.redis_service.update_status(deployment_id, "in_progress")
        try:
            subprocess.run([
                "docker", "run", "-d", "--rm",
                "--name", container_name,
                "-p", f"{host_port}:80",
                image
            ], check=True)
            url = f"http://localhost:{host_port}"
            self.redis_service.push_result(deployment_id, url)
            self.redis_service.update_status(deployment_id, "completed")
            return url
        except subprocess.CalledProcessError as exc:
            err = f"Error deploying frontend: {exc}"
            self.redis_service.push_result(deployment_id, err)
            self.redis_service.update_status(deployment_id, "failed")
            raise

    def build_and_deploy(self, code: str, deployment_id: str, port: Optional[int] = None) -> str:
        """Build a simple nginx image from HTML code and deploy it."""
        temp_dir = tempfile.mkdtemp(prefix=f"frontend_{deployment_id}_")
        try:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(code)

            dockerfile_path = os.path.join(temp_dir, "Dockerfile")
            with open(dockerfile_path, "w", encoding="utf-8") as f:
                f.write("FROM nginx:alpine\nCOPY index.html /usr/share/nginx/html/index.html\n")

            image_tag = f"frontend:{deployment_id}"
            subprocess.run(["docker", "build", "-t", image_tag, temp_dir], check=True)
            return self.deploy_frontend(image_tag, deployment_id, port)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
