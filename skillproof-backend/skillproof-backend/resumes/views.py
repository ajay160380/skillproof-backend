import os
import tempfile
from django.http import HttpResponseRedirect, Http404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Resume
from .serializers import ResumeSerializer, ResumeUploadSerializer
from .tasks import process_resume_skills
from .ai_utils import extract_text_from_file
from .utils import get_resume_download_url
from skills.models import SkillTest
from skills.utils import match_skills_to_tests

class ResumeUploadView(generics.CreateAPIView):
    serializer_class = ResumeUploadSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        extracted_text = ""
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            try:
                ext = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else 'pdf'
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                    for chunk in uploaded_file.chunks():
                        tmp.write(chunk)
                    tmp.flush()
                    tmp_path = tmp.name
                try:
                    extracted_text = extract_text_from_file(tmp_path)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            except Exception as e:
                print(f"Direct text extraction error during upload: {e}")
            finally:
                try:
                    uploaded_file.seek(0)
                except Exception:
                    pass
                
        # Clean up any old resumes for this user so they don't linger
        Resume.objects.filter(user=request.user).delete()

        resume = serializer.save(user=request.user, extracted_text=extracted_text)
        
        # Dispatch task to extract skills
        try:
            process_resume_skills.delay(resume.id)
        except Exception as e:
            print(f"Celery task dispatch warning: {e}, running synchronously...")
            try:
                process_resume_skills(resume.id)
            except Exception as sync_err:
                print(f"Synchronous resume processing error: {sync_err}")
        
        resume.refresh_from_db()
        return Response(ResumeSerializer(resume).data, status=status.HTTP_201_CREATED)

class ResumeViewFileView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        resume = Resume.objects.filter(user=request.user).order_by('-uploaded_at').first()
        if not resume or not resume.file:
            raise Http404("Resume not found")
        signed_url = get_resume_download_url(resume.file)
        return HttpResponseRedirect(signed_url)

class ResumeReparseView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        resume = Resume.objects.filter(user=request.user).order_by('-uploaded_at').first()
        if not resume:
            return Response({"detail": "No resume found."}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            process_resume_skills(resume.id)
            resume.refresh_from_db()
        except Exception as e:
            print(f"Reparse error: {e}")
            
        serializer = ResumeSerializer(resume)
        return Response(serializer.data)

class MyResumeView(generics.RetrieveAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Resume.objects.filter(user=self.request.user).order_by('-uploaded_at').first()

    def get(self, request, *args, **kwargs):
        resume = self.get_object()
        if not resume:
            return Response({"detail": "No resume found."}, status=status.HTTP_404_NOT_FOUND)
            
        # Self-healing: if resume is failed or pending or has no skills, parse it now!
        if resume.parsing_status != 'completed' or not resume.extracted_skills:
            try:
                process_resume_skills(resume.id)
                resume.refresh_from_db()
            except Exception as e:
                print(f"Self-healing parse error: {e}")
                
        serializer = self.get_serializer(resume)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        resume = self.get_object()
        if resume:
            resume.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class SuggestedTestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        resume = Resume.objects.filter(user=request.user).order_by('-uploaded_at').first()
        if not resume or not resume.extracted_skills:
            return Response([])
            
        matched_tests = match_skills_to_tests(resume.extracted_skills)
        
        # We need a serializer for SkillTest, let's just return basic info
        tests_data = []
        for test in matched_tests:
            tests_data.append({
                'id': test.id,
                'title': test.title,
                'category': test.category.name,
                'category_slug': test.category.slug,
                'difficulty': test.difficulty,
                'duration_minutes': test.duration_minutes,
                'test_type': test.test_type
            })
            
        return Response(tests_data)
