from celery import shared_task
from .models import Resume
from .ai_utils import extract_text_from_file, extract_skills_via_ai
from .utils import get_resume_download_url

@shared_task
def process_resume_skills(resume_id: int):
    try:
        resume = Resume.objects.get(id=resume_id)
        resume.parsing_status = 'processing'
        resume.save(update_fields=['parsing_status'])
        
        text = resume.extracted_text or ""
        
        # If text is not already extracted, download/read the file
        if not text:
            import tempfile
            import os
            import requests
            from django.conf import settings
            
            ext = resume.file.name.split('.')[-1] if '.' in resume.file.name else 'pdf'
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                success = False
                
                # Try signed Cloudinary download URL first
                urls_to_try = []
                if hasattr(resume.file, 'url'):
                    signed_url = get_resume_download_url(resume.file.url)
                    if signed_url:
                        urls_to_try.append(signed_url)
                    urls_to_try.append(resume.file.url)
                
                for u in urls_to_try:
                    try:
                        response = requests.get(u, timeout=10)
                        if response.status_code == 200 and len(response.content) > 0:
                            tmp.write(response.content)
                            success = True
                            break
                    except Exception as req_err:
                        print(f"Error fetching {u}: {req_err}")
                
                if not success:
                    # Fallback to local disk
                    local_path = os.path.join(settings.MEDIA_ROOT, resume.file.name)
                    if os.path.exists(local_path):
                        with open(local_path, 'rb') as f:
                            tmp.write(f.read())
                            success = True
                    else:
                        try:
                            content = resume.file.read()
                            if content:
                                tmp.write(content)
                                success = True
                        except Exception as read_err:
                            print(f"Direct file read error: {read_err}")
                            
                tmp.flush()
                tmp_path = tmp.name
                
            try:
                if success:
                    text = extract_text_from_file(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                
            resume.extracted_text = text
            resume.save(update_fields=['extracted_text'])
            
        # Extract skills using Groq / keyword fallback
        skills = extract_skills_via_ai(text)
        resume.extracted_skills = skills
        resume.parsing_status = 'completed'
        
        resume.save(update_fields=['extracted_skills', 'parsing_status'])
        print(f"Successfully processed resume {resume_id}: found {len(skills)} skills")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        if 'resume' in locals():
            resume.parsing_status = 'failed'
            resume.save(update_fields=['parsing_status'])
        print(f"Failed to process resume {resume_id}: {e}")

