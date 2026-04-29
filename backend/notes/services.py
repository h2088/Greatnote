from django.db.models import Q

from .models import Book, Page


def create_book(title="Untitled Book"):
    return Book.objects.create(title=title)


def get_book(book_id):
    return Book.objects.get(id=book_id)


def update_book(book_id, title=None):
    book = Book.objects.get(id=book_id)
    if title is not None:
        book.title = title
    book.save()
    return book


def delete_book(book_id):
    book = Book.objects.get(id=book_id)
    book.delete()


def list_books(search_query=None):
    queryset = Book.objects.all()
    if search_query:
        queryset = queryset.filter(title__icontains=search_query)
    return queryset


def create_page(book_id, title="Untitled", content=""):
    book = Book.objects.get(id=book_id)
    return Page.objects.create(book=book, title=title, content=content)


def get_page(page_id):
    return Page.objects.get(id=page_id)


def update_page(page_id, title=None, content=None):
    page = Page.objects.get(id=page_id)
    if title is not None:
        page.title = title
    if content is not None:
        page.content = content
    page.save()
    return page


def delete_page(page_id):
    page = Page.objects.get(id=page_id)
    page.delete()


def list_pages(book_id=None, search_query=None):
    queryset = Page.objects.all()
    if book_id:
        queryset = queryset.filter(book_id=book_id)
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) | Q(content__icontains=search_query)
        )
    return queryset
