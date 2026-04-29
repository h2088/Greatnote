from rest_framework import serializers

from .models import Book, Page


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ["id", "book", "title", "content", "created_at", "updated_at"]


class BookSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "pages", "created_at", "updated_at"]
