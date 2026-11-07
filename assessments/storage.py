from django.conf import settings
from django.core.files.storage import default_storage


def get_audio_storage():
    """
    Returns the appropriate storage engine for audio files.

    In production with Cloudinary configured, VideoMediaCloudinaryStorage must be used
    because Cloudinary requires audio to be stored under resource_type='video'
    (MediaCloudinaryStorage defaults to resource_type='image' and fails on audio).

    In local development / test environments without Cloudinary credentials,
    falls back to default_storage.
    """
    cloudinary_conf = getattr(settings, 'CLOUDINARY_STORAGE', {})
    has_cloudinary_creds = bool(
        cloudinary_conf.get('CLOUD_NAME') and
        cloudinary_conf.get('API_KEY') and
        cloudinary_conf.get('API_SECRET')
    )
    if not settings.DEBUG and has_cloudinary_creds:
        try:
            from cloudinary_storage.storage import VideoMediaCloudinaryStorage
            return VideoMediaCloudinaryStorage()
        except Exception:
            pass
    return default_storage
