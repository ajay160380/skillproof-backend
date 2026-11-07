from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, LogoutView, UserProfileView, CheckUsernameView, PublicProfileView

# URLs for user accounts (registration, login, profile management)
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('me/', UserProfileView.as_view(), name='user_profile'),
    path('check-username/', CheckUsernameView.as_view(), name='check_username'),
    path('profile/<str:username>/', PublicProfileView.as_view(), name='public_profile'),
]
