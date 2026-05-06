from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Notebook, Page, PageUserShare, ShareLink


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class ShareLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareLink
        fields = ["token", "is_active", "created_at"]


class PageUserShareSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = PageUserShare
        fields = ["id", "user", "created_at"]


class PageSerializer(serializers.ModelSerializer):
    share_token = serializers.SerializerMethodField()
    notebook_title = serializers.CharField(source="notebook.title", read_only=True)
    shared_users = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["id", "notebook", "title", "content", "order", "created_at", "updated_at", "share_token", "notebook_title", "shared_users"]
        read_only_fields = ["id", "notebook", "created_at", "updated_at", "share_token", "notebook_title", "shared_users"]

    def get_share_token(self, obj):
        link = obj.share_links.filter(is_active=True).first()
        return str(link.token) if link else None

    def get_shared_users(self, obj):
        request = self.context.get('request')
        if request and obj.notebook.user == request.user:
            shares = obj.user_shares.select_related('user').all()
            return PageUserShareSerializer(shares, many=True).data
        return []


class PageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for page lists (no content)."""
    share_token = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["id", "title", "order", "updated_at", "share_token"]

    def get_share_token(self, obj):
        link = obj.share_links.filter(is_active=True).first()
        return str(link.token) if link else None


class NotebookSerializer(serializers.ModelSerializer):
    pages = PageListSerializer(many=True, read_only=True)

    class Meta:
        model = Notebook
        fields = ["id", "title", "created_at", "updated_at", "pages"]
        read_only_fields = ["id", "created_at", "updated_at"]


class NotebookListSerializer(serializers.ModelSerializer):
    page_count = serializers.IntegerField(source="pages.count", read_only=True)

    class Meta:
        model = Notebook
        fields = ["id", "title", "page_count", "updated_at"]


class SharedPageSerializer(serializers.ModelSerializer):
    notebook_title = serializers.CharField(source="notebook.title", read_only=True)

    class Meta:
        model = Page
        fields = ["id", "title", "content", "notebook_title", "updated_at"]


class SharedWithMeSerializer(serializers.ModelSerializer):
    notebook_title = serializers.CharField(source="notebook.title", read_only=True)
    owner = serializers.CharField(source="notebook.user.username", read_only=True)
    shared_at = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["id", "title", "notebook_title", "owner", "updated_at", "shared_at"]

    def get_shared_at(self, obj):
        request = self.context.get('request')
        if request:
            share = obj.user_shares.filter(user=request.user).first()
            if share:
                return share.created_at
        return None
