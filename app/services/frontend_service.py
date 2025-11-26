# -*- coding: utf-8 -*-
import os
import subprocess
import tempfile
import shutil
import base64
import io
import tarfile
import socket

class FrontendService:
    def __init__(self, redis_service):
        self.redis_service = redis_service

    def _get_free_port(self):
        """Encuentra un puerto libre en el sistema"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def deploy_frontend(self, image, deployment_id, port=None):
        """Despliega un contenedor frontend"""
        try:
            if port is None:
                port = self._get_free_port()
            
            host_port = port
            container_name = "frontend_{}".format(deployment_id)
            
            subprocess.run([
                "docker", "run", "-d",
                "--name", container_name,
                "-p", "{}:80".format(host_port),
                image
            ], check=True)
            
            url = "http://localhost:{}".format(host_port)
            self.redis_service.push_result(deployment_id, url)
            self.redis_service.update_status(deployment_id, "completed")
            return url
        except subprocess.CalledProcessError as exc:
            err = "Error deploying frontend: {}".format(str(exc))
            self.redis_service.push_result(deployment_id, err)
            self.redis_service.update_status(deployment_id, "failed")
            raise

    def build_and_deploy(self, code, deployment_id, port=None, npm=False):
        """Construye y despliega un frontend"""
        temp_dir = tempfile.mkdtemp(prefix="frontend_{}_".format(deployment_id))
        try:
            if npm:
                # Proyecto npm empaquetado en base64
                tar_bytes = base64.b64decode(code)
                with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r") as tar:
                    tar.extractall(temp_dir)

                dockerfile_contents = (
                    "FROM node:14\n"
                    "WORKDIR /app\n"
                    "COPY . .\n"
                    "RUN npm install\n"
                    "RUN npm run build\n"
                    "RUN npm install -g serve\n"
                    "CMD ['serve', '-s', 'build', '-l', '80']\n"
                )
            else:
                # HTML simple
                index_path = os.path.join(temp_dir, "index.html")
                with open(index_path, "w", encoding="utf-8") as f:
                    f.write(code)

                dockerfile_contents = (
                    "FROM nginx:alpine\n"
                    "COPY index.html /usr/share/nginx/html/\n"
                )

            dockerfile_path = os.path.join(temp_dir, "Dockerfile")
            with open(dockerfile_path, "w", encoding="utf-8") as f:
                f.write(dockerfile_contents)

            image_tag = "frontend:{}".format(deployment_id)
            subprocess.run(["docker", "build", "-t", image_tag, temp_dir], check=True)
            return self.deploy_frontend(image_tag, deployment_id, port)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

