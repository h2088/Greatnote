from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path("auth/register/", views.register, name="register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", views.me, name="me"),

    # Topic folders
    path("topic-folders/", views.TopicFolderListCreateView.as_view(), name="topic-folder-list"),
    path("topic-folders/<int:pk>/", views.TopicFolderDetailView.as_view(), name="topic-folder-detail"),

    # Notebooks
    path("notebooks/", views.NotebookListCreateView.as_view(), name="notebook-list"),
    path("notebooks/<int:pk>/", views.NotebookDetailView.as_view(), name="notebook-detail"),

    # Pages (nested under notebook)
    path("notebooks/<int:notebook_pk>/pages/", views.PageListCreateView.as_view(), name="page-list"),
    path("notebooks/<int:notebook_pk>/import-webpage/", views.import_webpage, name="import-webpage"),

    # Pages (standalone)
    path("pages/favorites/", views.FavoritePageListView.as_view(), name="favorite-pages"),
    path("pages/<int:pk>/", views.PageDetailView.as_view(), name="page-detail"),
    path("pages/<int:pk>/share/", views.page_share, name="page-share"),
    path("pages/<int:pk>/share/users/", views.page_share_users, name="page-share-users"),
    path("pages/<int:pk>/share/users/<int:user_id>/", views.page_share_user_revoke, name="page-share-user-revoke"),
    path("pages/<int:pk>/ai-edit/", views.ai_edit, name="page-ai-edit"),

    # Shared pages
    path("shared/<uuid:token>/", views.shared_page, name="shared-page"),
    path("shared-with-me/", views.shared_with_me, name="shared-with-me"),
]
