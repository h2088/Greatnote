from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import BookViewSet, PageViewSet

router = DefaultRouter()
router.register(r"books", BookViewSet, basename="book")
router.register(r"pages", PageViewSet, basename="page")

urlpatterns = [
    path("", include(router.urls)),
]
