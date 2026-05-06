from django.db import models
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Notebook, Page, PageUserShare, ShareLink
from .permissions import IsNotebookOwner, IsPageOwner, CanAccessPage
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    NotebookSerializer,
    NotebookListSerializer,
    PageSerializer,
    PageListSerializer,
    PageUserShareSerializer,
    SharedPageSerializer,
    SharedWithMeSerializer,
)


# ── Auth ─────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


# ── Notebooks ─────────────────────────────────────────────────────────────────

class NotebookListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['title', 'pages__title']

    def get_serializer_class(self):
        if self.request.method == "GET":
            return NotebookListSerializer
        return NotebookSerializer

    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotebookDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NotebookSerializer
    permission_classes = [IsAuthenticated, IsNotebookOwner]

    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)


# ── Pages ─────────────────────────────────────────────────────────────────────

class PageListCreateView(generics.ListCreateAPIView):
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        notebook = get_object_or_404(Notebook, pk=self.kwargs["notebook_pk"], user=self.request.user)
        return notebook.pages.all()

    def perform_create(self, serializer):
        notebook = get_object_or_404(Notebook, pk=self.kwargs["notebook_pk"], user=self.request.user)
        max_order = notebook.pages.count()
        serializer.save(notebook=notebook, order=max_order)


class PageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated, CanAccessPage]

    def get_queryset(self):
        return Page.objects.filter(
            models.Q(notebook__user=self.request.user) |
            models.Q(user_shares__user=self.request.user)
        ).distinct()


class FavoritePageListView(generics.ListAPIView):
    serializer_class = PageListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Page.objects.filter(notebook__user=self.request.user, is_favorite=True).order_by("-updated_at")


# ── Share ─────────────────────────────────────────────────────────────────────

@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def page_share(request, pk):
    page = get_object_or_404(Page, pk=pk, notebook__user=request.user)

    if request.method == "POST":
        link, _ = ShareLink.objects.get_or_create(page=page, is_active=True)
        return Response({"token": str(link.token)}, status=status.HTTP_200_OK)

    # DELETE — revoke all active links
    ShareLink.objects.filter(page=page, is_active=True).update(is_active=False)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def page_share_users(request, pk):
    page = get_object_or_404(Page, pk=pk, notebook__user=request.user)

    if request.method == "GET":
        shares = page.user_shares.select_related('user').all()
        serializer = PageUserShareSerializer(shares, many=True)
        return Response(serializer.data)

    # POST — share with a user by username
    username = request.data.get('username')
    if not username:
        return Response({"detail": "username is required"}, status=status.HTTP_400_BAD_REQUEST)

    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return Response({"detail": "Cannot share with yourself"}, status=status.HTTP_400_BAD_REQUEST)

    share, created = PageUserShare.objects.get_or_create(page=page, user=target_user)
    serializer = PageUserShareSerializer(share)
    return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def page_share_user_revoke(request, pk, user_id):
    page = get_object_or_404(Page, pk=pk, notebook__user=request.user)
    share = get_object_or_404(PageUserShare, page=page, user_id=user_id)
    share.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shared_with_me(request):
    pages = Page.objects.filter(user_shares__user=request.user).distinct()
    serializer = SharedWithMeSerializer(pages, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def shared_page(request, token):
    link = get_object_or_404(ShareLink, token=token, is_active=True)
    serializer = SharedPageSerializer(link.page)
    return Response(serializer.data)
