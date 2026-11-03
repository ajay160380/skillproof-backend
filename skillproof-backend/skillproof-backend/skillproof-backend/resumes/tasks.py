from celery import shared_task
from .models import Resume
from .ai_utils import extract_text_from_file, extract_skills_via_ai

@shared_task
def process_resume_skills(resume_id: int):
    try:
        resume = Resume.objects.get(id=resume_id)
        resume.parsing_status = 'processing'
        resume.save(update_fields=['parsing_status'])
        
        # Extract text from file using a temporary file
        import tempfile
        import os
        import requests
        from django.conf import settings
        
        ext = resume.file.name.split('.')[-1] if '.' in resume.file.name else 'pdf'
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            success = False
            if hasattr(resume.file, 'url'):
                try:
                    response = requests.get(resume.file.url, timeout=5)
                    if response.status_code == 200:
                        tmp.write(response.content)
                        success = True
                except Exception:
                    pass
            
            if not success:
                # Fallback to local disk
                local_path = os.path.join(settings.MEDIA_ROOT, resume.file.name)
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        tmp.write(f.read())
                else:
                    tmp.write(resume.file.read())  # Last resort
            tmp.flush()
            tmp_path = tmp.name
            
        try:
            text = extract_text_from_file(tmp_path)
        finally:
            os.remove(tmp_path)
            
        resume.extracted_text = text
        resume.save(update_fields=['extracted_text'])
        
        # Extract skills using Groq / fallback
        skills = extract_skills_via_ai(text)
        resume.extracted_skills = skills
        resume.parsing_status = 'completed'
        
        resume.save(update_fields=['extracted_skills', 'parsing_status'])
        
    except Exception as e:
        if 'resume' in locals():
            resume.parsing_status = 'failed'
            resume.save(update_fields=['parsing_status'])
        print(f"Failed to process resume {resume_id}: {e}")
