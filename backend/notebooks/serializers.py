from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Notebook, Page, PageUserShare, ShareLink, TopicFolder


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


class TopicFolderSerializer(serializers.ModelSerializer):
    page_count = serializers.IntegerField(source="pages.count", read_only=True)

    class Meta:
        model = TopicFolder
        fields = ["id", "notebook", "name", "created_at", "updated_at", "page_count"]
        read_only_fields = ["id", "created_at", "updated_at", "page_count"]

    def validate_name(self, value):
        clean = value.strip()
        if not clean:
            raise serializers.ValidationError("Folder name cannot be empty.")
        return clean

    def validate_notebook(self, value):
        request = self.context.get("request")
        if request and request.user and value.user != request.user:
            raise serializers.ValidationError("Notebook not found.")
        return value


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
    topic_folder = serializers.PrimaryKeyRelatedField(
        queryset=TopicFolder.objects.none(), required=False, allow_null=True
    )
    topic_folder_name = serializers.CharField(source="topic_folder.name", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "notebook",
            "title",
            "content",
            "order",
            "is_favorite",
            "topic_folder",
            "topic_folder_name",
            "created_at",
            "updated_at",
            "share_token",
            "notebook_title",
            "shared_users",
        ]
        read_only_fields = [
            "id",
            "notebook",
            "created_at",
            "updated_at",
            "share_token",
            "notebook_title",
            "shared_users",
            "topic_folder_name",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        notebook_id = self.context.get("notebook_id")
        if request and request.user and request.user.is_authenticated:
            qs = TopicFolder.objects.filter(notebook__user=request.user)
            if notebook_id:
                qs = qs.filter(notebook_id=notebook_id)
            self.fields["topic_folder"].queryset = qs

    def validate_topic_folder(self, folder):
        request = self.context.get("request")
        notebook_id = self.context.get("notebook_id")
        if folder and request and folder.notebook.user != request.user:
            raise serializers.ValidationError("Folder does not belong to current user.")
        if folder and notebook_id and folder.notebook_id != notebook_id:
            raise serializers.ValidationError("Folder does not belong to current notebook.")
        return folder

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
    topic_folder_name = serializers.CharField(source="topic_folder.name", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "notebook",
            "title",
            "order",
            "is_favorite",
            "topic_folder",
            "topic_folder_name",
            "updated_at",
            "share_token",
        ]
        read_only_fields = ["notebook"]

    def get_share_token(self, obj):
        link = obj.share_links.filter(is_active=True).first()
        return str(link.token) if link else None


class NotebookSerializer(serializers.ModelSerializer):
    pages = PageListSerializer(many=True, read_only=True)

    class Meta:
        model = Notebook
        fields = ["id", "title", "created_at", "updated_at", "pages"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value):
        clean = value.strip()
        if not clean:
            raise serializers.ValidationError("Notebook title cannot be empty.")
        return clean


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
