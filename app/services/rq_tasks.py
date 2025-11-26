# -*- coding: utf-8 -*-
from app.services.script_service import ScriptService
from app.services.video_audio_service import VideoAudioService
from app.services.frames_storage_service import FramesStorageService
from app.services.metadata_storage_service import MetadataStorageService
from app.services.frontend_service import FrontendService

def _get_services():
    """Lazy initialization to avoid circular imports"""
    from app.services.redis_service import RedisService
    redis_service = RedisService()
    return {
        'redis': redis_service,
        'script': ScriptService(redis_service),
        'video': VideoAudioService(redis_service),
        'frames': FramesStorageService(redis_service),
        'metadata': MetadataStorageService(redis_service),
        'frontend': FrontendService(redis_service)
    }


def process_script_task(script_id, script_content):
    """Process a script using the ScriptService."""
    services = _get_services()
    services['script'].process_script(script_content, script_id)


def process_video_task(script_id, script_content, video_id):
    """Process a video conversion using the VideoAudioService."""
    services = _get_services()
    services['video'].process_video_conversion(script_content, script_id, video_id)


def process_frames_task(script_id, script_content, video_id):
    """Process frame extraction using the FramesStorageService."""
    services = _get_services()
    services['frames'].process_video_to_frames(script_content, script_id, video_id)


def process_metadata_task(script_id, script_content, video_id):
    """Process metadata extraction using the MetadataStorageService."""
    services = _get_services()
    services['metadata'].process_video_metadata(script_content, script_id, video_id)


def deploy_frontend_from_code_task(code, deployment_id, port=None, npm=False):
    """Build and deploy a frontend from HTML or an npm project."""
    services = _get_services()
    services['frontend'].build_and_deploy(code, deployment_id, port, npm)
