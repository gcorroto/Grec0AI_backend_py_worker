import os
import subprocess
import uuid
import socket

class FrontendService:
    """Service to dynamically deploy simple front-end containers."""

    def __init__(self, redis_service=None):
        self.redis_service = redis_service

    @staticmethod
    def _find_free_port():
        """Find an available port on the host."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def deploy_frontend(self, image_name: str, port: int = None) -> dict:
        """Launch a container serving the front-end via nginx.

        Args:
            image_name: Name of the Docker image with the front-end.
            port: Optional host port. If not provided, one will be selected.

        Returns:
            Dictionary with container_id and port used.
        """
        if port is None:
            port = self._find_free_port()

        container_name = f"frontend_{uuid.uuid4().hex[:8]}"
        try:
            result = subprocess.run([
                'docker', 'run', '-d', '--rm',
                '-p', f'{port}:80',
                '--name', container_name,
                image_name
            ], capture_output=True, text=True, check=True)

            container_id = result.stdout.strip()
            if self.redis_service:
                self.redis_service.push_result(container_name, f"running_on:{port}")
            return {'container_id': container_id, 'port': port}
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to deploy front-end: {e.stderr}"
            if self.redis_service:
                self.redis_service.push_result(container_name, error_msg)
            raise RuntimeError(error_msg)

    def stop_frontend(self, container_id: str):
        """Stop a running front-end container."""
        subprocess.run(['docker', 'stop', container_id], check=False)
