from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from skills.models import SkillCategory, SkillTest
from assessments.models import TestAttempt

User = get_user_model()

class AssessmentSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="candidate_assess",
            email="candidate_assess@example.com",
            password="Password123!",
            role="candidate"
        )
        self.category = SkillCategory.objects.create(name="Python", description="Python test", icon="Code")
        self.test = SkillTest.objects.create(
            category=self.category,
            title="Python Assessment",
            difficulty="medium",
            duration_minutes=30,
            test_type="communication"
        )
        self.attempt = TestAttempt.objects.create(
            user=self.user,
            test=self.test,
            status="in_progress"
        )
        self.client.force_authenticate(user=self.user)

    def test_recording_url_cannot_be_injected_via_payload(self):
        # Attacker tries to inject an arbitrary server path via recording_url
        payload = {
            "recording_url": "/etc/passwd",
            "code_submission": "print('hello')"
        }
        res = self.client.post(f"/api/assessments/{self.attempt.id}/submit/", payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.attempt.refresh_from_db()
        # Ensure recording_url was NOT set to the arbitrary file path
        self.assertNotEqual(self.attempt.recording_url, "/etc/passwd")
        self.assertIsNone(self.attempt.recording_url)

    def test_audio_upload_rejects_invalid_extension(self):
        invalid_file = SimpleUploadedFile("evil.exe", b"fake binary content", content_type="application/octet-stream")
        res = self.client.post(f"/api/assessments/{self.attempt.id}/submit/", {"audio_file": invalid_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid audio format", res.data.get("error", ""))

    def test_audio_upload_accepts_valid_audio_via_storage(self):
        valid_file = SimpleUploadedFile("speech.wav", b"RIFF....WAVEfmt ....data....", content_type="audio/wav")
        res = self.client.post(f"/api/assessments/{self.attempt.id}/submit/", {"audio_file": valid_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.attempt.refresh_from_db()
        self.assertIsNotNone(self.attempt.recording_url)
        self.assertTrue(self.attempt.recording_url.startswith("recordings/attempt_"))

    def test_audio_storage_resolution(self):
        from assessments.storage import get_audio_storage
        from django.core.files.storage import default_storage

        # In dev/test without credentials, get_audio_storage returns default_storage
        storage = get_audio_storage()
        self.assertEqual(storage, default_storage)

        # In production (DEBUG=False) with Cloudinary credentials configured, VideoMediaCloudinaryStorage is returned
        with self.settings(
            DEBUG=False,
            CLOUDINARY_STORAGE={
                'CLOUD_NAME': 'mock_cloud',
                'API_KEY': '1234567890',
                'API_SECRET': 'mock_secret_abcdefg'
            }
        ):
            prod_storage = get_audio_storage()
            from cloudinary_storage.storage import VideoMediaCloudinaryStorage
            self.assertIsInstance(prod_storage, VideoMediaCloudinaryStorage)
