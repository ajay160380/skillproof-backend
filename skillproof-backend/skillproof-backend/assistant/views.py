import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings
from badges.models import Badge
from assessments.models import TestAttempt
from django.db.models import Avg

logger = logging.getLogger(__name__)

try:
    from groq import Groq
except ImportError:
    Groq = None

class AssistantChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        message = request.data.get('message')
        history = request.data.get('history', [])

        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Build context about the user
        badges = Badge.objects.filter(user=user)
        badge_count = badges.count()
        attempts = TestAttempt.objects.filter(user=user, status='completed')
        test_count = attempts.count()
        
        avg_score = attempts.aggregate(avg=Avg('score__overall_score'))['avg']
        avg_score_str = f"{avg_score:.1f}" if avg_score else "N/A"

        recent_attempts = attempts.order_by('-completed_at')[:3]
        recent_feedback = []
        for att in recent_attempts:
            feedback = att.score.ai_feedback_text if att.score else "No feedback."
            recent_feedback.append(f"Test: {att.test.title} (Score: {att.score.overall_score if att.score else 'N/A'})\nFeedback: {feedback}")

        context_str = f"""
You are the SkillProof AI Assistant. You help candidates navigate the platform, understand their scores, and pick their next assessments.
User Profile context:
- Completed Tests: {test_count}
- Badges Earned: {badge_count}
- Average Verification Score: {avg_score_str}

Recent Test Feedback:
{chr(10).join(recent_feedback)}

Rules:
1. Be concise, professional, and encouraging.
2. If the user asks about scoring, explain that it uses a cryptographically verified AI proctoring system.
3. If they ask what to do next and have 0 tests, suggest they upload a resume or take a Core Skills test.
"""

        messages = [{"role": "system", "content": context_str}]
        
        # Add history
        for msg in history:
            role = 'user' if msg.get('is_user') else 'assistant'
            messages.append({"role": role, "content": msg.get('text')})

        messages.append({"role": "user", "content": message})

        # Fallback if Groq is not configured or fails
        fallback_response = "I'm currently operating in offline mode. To get started, I suggest uploading your resume or taking one of the Core Skills assessments on your dashboard!"
        
        if not getattr(settings, 'GROQ_API_KEY', None) or not Groq:
            return Response({'response': fallback_response})

        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="openai/gpt-oss-120b",
                temperature=0.7,
                max_tokens=256,
            )
            ai_response = chat_completion.choices[0].message.content
            return Response({'response': ai_response})
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return Response({'response': fallback_response})
