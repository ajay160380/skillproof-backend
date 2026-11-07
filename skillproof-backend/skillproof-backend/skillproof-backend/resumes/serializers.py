from rest_framework import serializers
from .models import Resume
from .utils import get_resume_download_url

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ['id', 'user', 'file', 'extracted_skills', 'uploaded_at', 'parsing_status']
        read_only_fields = ['id', 'user', 'extracted_skills', 'uploaded_at', 'parsing_status']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get('file'):
            ret['file'] = get_resume_download_url(ret['file'])
        return ret

class ResumeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ['file']

