# -*- coding= RedisService()
script_service = ScriptService(redis_service)
video_audio_service = VideoAudioService(redis_service)
frames_storage_service = FramesStorageService(redis_service)
metadata_storage_service = MetadataStorageService(redis_service)
frontend_service = FrontendService(redis_service)


def process_script_task(script_id, script_content):
    """Process a script using the ScriptService."""
    script_service.process_script(script_content, script_id)


def process_video_task(script_id, script_content, video_id):
    """Process a video conversion using the VideoAudioService."""
    video_audio_service.process_video_conversion(script_content, script_id, video_id)


def process_frames_task(script_id, script_content, video_id):
    """Process frame extraction using the FramesStorageService."""
    frames_storage_service.process_video_to_frames(script_content, script_id, video_id)


def process_metadata_task(script_id, script_content, video_id):
    """Process metadata extraction using the MetadataStorageService."""
    metadata_storage_service.process_video_metadata(script_content, script_id, video_id)


def deploy_frontend_from_code_task(code, deployment_id, port=None, npm=False):
    """Build and deploy a frontend from HTML or an npm project."""
    frontend_service.build_and_deploy(code, deployment_id, port, npm)
