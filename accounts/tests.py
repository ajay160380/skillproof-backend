from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from operations.models import Organization, Department, OperationTask

User = get_user_model()

class SecurityPrivilegeEscalationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.candidate = User.objects.create_user(
            username="candidate1",
            email="candidate1@example.com",
            password="Password123!",
            role="candidate"
        )
        self.admin_user = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password="Password123!",
            role="admin"
        )
        self.superadmin_user = User.objects.create_user(
            username="super1",
            email="super1@example.com",
            password="Password123!",
            role="superadmin",
            is_superuser=True
        )

    def test_cannot_register_with_superadmin_role(self):
        payload = {
            "username": "hacker1",
            "email": "hacker1@example.com",
            "password": "Password123!",
            "role": "superadmin"
        }
        res = self.client.post("/api/auth/register/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="hacker1").exists())

    def test_patch_me_cannot_change_role_or_privileges(self):
        self.client.force_authenticate(user=self.candidate)
        res = self.client.patch("/api/auth/me/", {
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
            "is_verified": True
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.role, "candidate")
        self.assertFalse(self.candidate.is_staff)
        self.assertFalse(self.candidate.is_superuser)
        self.assertFalse(self.candidate.is_verified)

    def test_non_admin_cannot_access_operations_users(self):
        self.client.force_authenticate(user=self.candidate)
        res = self.client.get("/api/operations/users/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_profile_does_not_leak_email(self):
        res = self.client.get(f"/api/auth/profile/{self.candidate.username}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], self.candidate.username)
        self.assertNotIn("email", res.data)

    def test_public_profile_lookup_strictly_by_username(self):
        # Numeric ID lookup should fail
        res = self.client.get(f"/api/auth/profile/{self.candidate.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        # Email lookup should fail
        res = self.client.get(f"/api/auth/profile/{self.candidate.email}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_register_normalizes_email_case_insensitively(self):
        payload1 = {
            "username": "usercase1",
            "email": "CaseUser@Example.COM",
            "password": "Password123!",
            "role": "candidate"
        }
        res1 = self.client.post("/api/auth/register/", payload1)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res1.data["user"]["email"], "caseuser@example.com")

        # Duplicate check with different case
        payload2 = {
            "username": "usercase2",
            "email": "caseuser@example.com",
            "password": "Password123!",
            "role": "candidate"
        }
        res2 = self.client.post("/api/auth/register/", payload2)
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_blacklists_refresh_token(self):
        login_res = self.client.post("/api/auth/login/", {
            "email": self.candidate.email,
            "password": "Password123!"
        })
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        refresh = login_res.data["refresh"]
        access = login_res.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_res = self.client.post("/api/auth/logout/", {"refresh": refresh})
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Refreshing blacklisted token should fail
        refresh_res = self.client.post("/api/auth/refresh/", {"refresh": refresh})
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_role_permissions_and_restrictions(self):
        # Non-admin cannot call change-role
        self.client.force_authenticate(user=self.candidate)
        res = self.client.post(f"/api/operations/users/{self.candidate.id}/change-role/", {"role": "admin"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Admin cannot change own role
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post(f"/api/operations/users/{self.admin_user.id}/change-role/", {"role": "superadmin"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Admin cannot grant superadmin
        res = self.client.post(f"/api/operations/users/{self.candidate.id}/change-role/", {"role": "superadmin"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Superadmin CAN grant superadmin
        self.client.force_authenticate(user=self.superadmin_user)
        res = self.client.post(f"/api/operations/users/{self.candidate.id}/change-role/", {"role": "superadmin"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.role, "superadmin")

    def test_operations_task_permission_enforcement(self):
        org = Organization.objects.create(name="Test Org", code="TORG")
        dept = Department.objects.create(organization=org, name="Eng", code="ENG")
        task = OperationTask.objects.create(
            organization=org,
            department=dept,
            title="Clean Database",
            assigned_to=self.candidate,
            created_by=self.admin_user,
            mis_score=0
        )

        # Normal candidate cannot delete or update tasks
        self.client.force_authenticate(user=self.candidate)
        res_del = self.client.delete(f"/api/operations/tasks/{task.id}/")
        self.assertEqual(res_del.status_code, status.HTTP_403_FORBIDDEN)

        res_patch = self.client.patch(f"/api/operations/tasks/{task.id}/", {"mis_score": 100})
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)

        # Normal candidate CAN submit proof for their assigned task
        res_proof = self.client.post(f"/api/operations/tasks/{task.id}/submit-proof/", {
            "proof_submission": "Database cleaned."
        })
        self.assertEqual(res_proof.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
