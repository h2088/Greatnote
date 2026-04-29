from rest_framework import viewsets, status
from rest_framework.response import Response

from .serializers import BookSerializer, PageSerializer
from .services import (
    create_book, update_book, delete_book, list_books,
    create_page, update_page, delete_page, list_pages,
)


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search")
        return list_books(search_query=search)

    def create(self, request):
        title = request.data.get("title", "Untitled Book")
        book = create_book(title=title)
        serializer = self.get_serializer(book)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        title = request.data.get("title")
        book = update_book(pk, title=title)
        serializer = self.get_serializer(book)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        delete_book(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PageViewSet(viewsets.ModelViewSet):
    serializer_class = PageSerializer

    def get_queryset(self):
        book_id = self.request.query_params.get("book_id")
        search = self.request.query_params.get("search")
        return list_pages(book_id=book_id, search_query=search)

    def create(self, request):
        book_id = request.data.get("book")
        title = request.data.get("title", "Untitled")
        content = request.data.get("content", "")
        page = create_page(book_id=book_id, title=title, content=content)
        serializer = self.get_serializer(page)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        title = request.data.get("title")
        content = request.data.get("content")
        page = update_page(pk, title=title, content=content)
        serializer = self.get_serializer(page)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        delete_page(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
