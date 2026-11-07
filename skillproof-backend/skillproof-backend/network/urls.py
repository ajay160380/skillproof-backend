from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SearchNetworkView, FollowUserView, UnfollowUserView, 
    MyFollowingView, MyFollowersView, PostViewSet, CommentViewSet
)

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

# We need a nested router or simple path for comments
# e.g., /api/feed/posts/<id>/comments/
# DRF doesn't have nested routers built-in natively without drf-nested-routers
# So we'll register comments specifically or just use standard paths.

from marketplace.views import FollowersListView

urlpatterns = [
    path('search/', SearchNetworkView.as_view(), name='search_network'),
    path('follow-user/', FollowUserView.as_view(), name='follow_user'),
    path('unfollow-user/<int:user_id>/', UnfollowUserView.as_view(), name='unfollow_user'),
    path('my-following/', MyFollowingView.as_view(), name='my_following'),
    path('my-followers/', MyFollowersView.as_view(), name='my_followers'),
    path('followers/', FollowersListView.as_view(), name='network_followers'),
    
    path('feed/', include(router.urls)),
    path('feed/posts/<int:post_pk>/comments/', CommentViewSet.as_view({'get': 'list', 'post': 'create'}), name='post-comments'),
    path('feed/posts/<int:post_pk>/comments/<int:pk>/', CommentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='post-comment-detail'),
]
