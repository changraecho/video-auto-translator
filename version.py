"""
Version information and build details
"""
from datetime import datetime
import os

VERSION = "1.3.0"
BUILD_DATE = "2025-01-06 22:30:00"
GIT_COMMIT = "version-tracking"  # 마지막 커밋 해시
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# 배포 상태 확인용
FEATURES = {
    'whisper_audio_extraction': True,
    'claude_text_improvement': True,
    'multi_language_translation': True,
    'dynamic_subtitle_boxes': True,
    'srt_timing_sync': True,
    'title_font_rendering': True,
    'cloud_deployment_ready': True
}

def get_version_info():
    """배포 상태와 버전 정보 반환"""
    return {
        'version': VERSION,
        'build_date': BUILD_DATE,
        'git_commit': GIT_COMMIT,
        'environment': ENVIRONMENT,
        'features': FEATURES,
        'deployment_time': datetime.now().isoformat(),
        'status': 'active'
    }

def get_version_string():
    """간단한 버전 문자열 반환"""
    return f"v{VERSION} (Build: {GIT_COMMIT[:7]})"