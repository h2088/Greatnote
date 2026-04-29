from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from notes.models import Book, Page
from notes.services import create_book, create_page


class BookViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_books_empty(self):
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_create_book(self):
        data = {"title": "My Journal"}
        response = self.client.post("/api/books/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "My Journal")
        self.assertEqual(Book.objects.count(), 1)

    def test_create_book_defaults(self):
        response = self.client.post("/api/books/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Untitled Book")

    def test_retrieve_book_with_pages(self):
        book = Book.objects.create(title="Retrieve")
        Page.objects.create(book=book, title="Page 1", content="content")
        response = self.client.get(f"/api/books/{book.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Retrieve")
        self.assertEqual(len(response.data["pages"]), 1)

    def test_update_book(self):
        book = Book.objects.create(title="Old")
        data = {"title": "New"}
        response = self.client.put(f"/api/books/{book.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(book.title, "New")

    def test_delete_book(self):
        book = Book.objects.create(title="Delete")
        response = self.client.delete(f"/api/books/{book.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Book.objects.count(), 0)

    def test_search_books(self):
        Book.objects.create(title="Apple Notes")
        Book.objects.create(title="Carrot Diary")
        response = self.client.get("/api/books/?search=Notes")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Apple Notes")


class PageViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.book = create_book(title="Test Book")

    def test_list_pages_empty(self):
        response = self.client.get("/api/pages/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_page(self):
        data = {"book": self.book.id, "title": "Intro", "content": "Hello"}
        response = self.client.post("/api/pages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Intro")
        self.assertEqual(Page.objects.count(), 1)

    def test_create_page_defaults(self):
        data = {"book": self.book.id}
        response = self.client.post("/api/pages/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Untitled")
        self.assertEqual(response.data["content"], "")

    def test_retrieve_page(self):
        page = Page.objects.create(book=self.book, title="Retrieve", content="me")
        response = self.client.get(f"/api/pages/{page.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Retrieve")

    def test_update_page(self):
        page = Page.objects.create(book=self.book, title="Old", content="Old")
        data = {"title": "New", "content": "New"}
        response = self.client.put(f"/api/pages/{page.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        page.refresh_from_db()
        self.assertEqual(page.title, "New")

    def test_delete_page(self):
        page = Page.objects.create(book=self.book, title="Delete", content="me")
        response = self.client.delete(f"/api/pages/{page.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Page.objects.count(), 0)

    def test_list_pages_by_book(self):
        book2 = create_book(title="Other Book")
        Page.objects.create(book=self.book, title="Page 1", content="a")
        Page.objects.create(book=book2, title="Page 2", content="b")
        response = self.client.get(f"/api/pages/?book_id={self.book.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Page 1")

    def test_search_pages(self):
        Page.objects.create(book=self.book, title="Apple", content="Red fruit")
        Page.objects.create(book=self.book, title="Carrot", content="Orange veggie")
        response = self.client.get("/api/pages/?search=fruit")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Apple")
