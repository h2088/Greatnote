import uuid
from django.db import models
from django.contrib.auth.models import User


class TopicFolder(models.Model):
    notebook = models.ForeignKey("Notebook", on_delete=models.CASCADE, related_name="topic_folders")
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        unique_together = ["notebook", "name"]

    def __str__(self):
        return self.name


class Notebook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notebooks")
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Page(models.Model):
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, related_name="pages")
    topic_folder = models.ForeignKey(
        TopicFolder,
        on_delete=models.SET_NULL,
        related_name="pages",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255, default="Untitled")
    content = models.JSONField(default=dict)
    order = models.PositiveIntegerField(default=0)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return self.title


class PageUserShare(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="user_shares")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shared_pages")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['page', 'user']

    def __str__(self):
        return f"PageShare({self.page.title}, {self.user.username})"


class ShareLink(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="share_links")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Share({self.page.title}, {self.token})"
