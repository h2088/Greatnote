from django.conf import settings
from django.db import models
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from openai import OpenAI
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


AI_EDIT_PROMPTS = {
    "improve": "Improve the writing quality of the following text. Keep the meaning and tone. Return only the improved text, no explanations.",
    "shorter": "Make the following text shorter and more concise. Preserve the key meaning. Return only the shortened text, no explanations.",
    "longer": "Expand the following text with more detail and depth. Keep the same style. Return only the expanded text, no explanations.",
    "grammar": "Fix grammar and spelling in the following text. Do not change the meaning or style. Return only the corrected text, no explanations.",
    "professional": "Rewrite the following text in a professional, formal tone. Return only the rewritten text, no explanations.",
    "casual": "Rewrite the following text in a casual, conversational tone. Return only the rewritten text, no explanations.",
}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_edit(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if page.notebook.user != request.user and not page.user_shares.filter(user=request.user).exists():
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    text = request.data.get("text", "").strip()
    action = request.data.get("action", "").strip()

    if not text:
        return Response({"detail": "text is required"}, status=status.HTTP_400_BAD_REQUEST)
    if action not in AI_EDIT_PROMPTS:
        return Response(
            {"detail": f"action must be one of: {', '.join(AI_EDIT_PROMPTS.keys())}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not settings.OPENAI_API_KEY:
        return Response(
            {"detail": "AI editing is not configured"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or None,
    )
    try:
        response = client.chat.completions.create(
            model="kimi-latest",
            messages=[
                {"role": "system", "content": AI_EDIT_PROMPTS[action]},
                {"role": "user", "content": text},
            ],
            temperature=0.7,
        )
        transformed = response.choices[0].message.content.strip()
    except Exception:
        return Response(
            {"detail": "AI transformation failed"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({"text": transformed})
