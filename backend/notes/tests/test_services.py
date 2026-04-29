from django.test import TestCase

from notes.models import Book, Page
from notes.services import (
    create_book, get_book, update_book, delete_book, list_books,
    create_page, get_page, update_page, delete_page, list_pages,
)


class BookServiceTests(TestCase):
    def test_create_book_with_default(self):
        book = create_book()
        self.assertEqual(book.title, "Untitled Book")

    def test_create_book_with_title(self):
        book = create_book(title="My Journal")
        self.assertEqual(book.title, "My Journal")

    def test_get_book(self):
        book = create_book(title="Target")
        fetched = get_book(book.id)
        self.assertEqual(fetched.id, book.id)

    def test_update_book(self):
        book = create_book(title="Old")
        updated = update_book(book.id, title="New")
        self.assertEqual(updated.title, "New")

    def test_delete_book(self):
        book = create_book(title="Delete me")
        delete_book(book.id)
        self.assertEqual(Book.objects.count(), 0)

    def test_delete_book_cascades_pages(self):
        book = create_book(title="Parent")
        create_page(book.id, title="Child")
        delete_book(book.id)
        self.assertEqual(Book.objects.count(), 0)
        self.assertEqual(Page.objects.count(), 0)

    def test_list_books(self):
        create_book(title="Alpha")
        create_book(title="Beta")
        books = list_books()
        self.assertEqual(books.count(), 2)

    def test_list_books_search(self):
        create_book(title="Apple")
        create_book(title="Banana")
        books = list_books(search_query="App")
        self.assertEqual(books.count(), 1)
        self.assertEqual(books.first().title, "Apple")


class PageServiceTests(TestCase):
    def setUp(self):
        self.book = create_book(title="Test Book")

    def test_create_page_with_defaults(self):
        page = create_page(self.book.id)
        self.assertEqual(page.title, "Untitled")
        self.assertEqual(page.content, "")
        self.assertEqual(page.book.id, self.book.id)

    def test_create_page_with_values(self):
        page = create_page(self.book.id, title="Intro", content="Hello")
        self.assertEqual(page.title, "Intro")
        self.assertEqual(page.content, "Hello")

    def test_get_page(self):
        page = create_page(self.book.id, title="Target", content="Find me")
        fetched = get_page(page.id)
        self.assertEqual(fetched.id, page.id)

    def test_update_page(self):
        page = create_page(self.book.id, title="Old", content="Old body")
        updated = update_page(page.id, title="New", content="New body")
        self.assertEqual(updated.title, "New")
        self.assertEqual(updated.content, "New body")

    def test_update_page_partial(self):
        page = create_page(self.book.id, title="Keep", content="Replace")
        updated = update_page(page.id, content="New")
        self.assertEqual(updated.title, "Keep")
        self.assertEqual(updated.content, "New")

    def test_delete_page(self):
        page = create_page(self.book.id, title="Delete me", content="Bye")
        delete_page(page.id)
        self.assertEqual(Page.objects.count(), 0)
        self.assertEqual(Book.objects.count(), 1)

    def test_list_pages(self):
        create_page(self.book.id, title="Page 1", content="")
        create_page(self.book.id, title="Page 2", content="")
        pages = list_pages(book_id=self.book.id)
        self.assertEqual(pages.count(), 2)

    def test_list_pages_search_by_title(self):
        create_page(self.book.id, title="Apple", content="Red")
        create_page(self.book.id, title="Banana", content="Yellow")
        pages = list_pages(book_id=self.book.id, search_query="App")
        self.assertEqual(pages.count(), 1)
        self.assertEqual(pages.first().title, "Apple")

    def test_list_pages_search_by_content(self):
        create_page(self.book.id, title="Fruit", content="Sweet")
        create_page(self.book.id, title="Veggie", content="Bitter")
        pages = list_pages(book_id=self.book.id, search_query="Sweet")
        self.assertEqual(pages.count(), 1)
        self.assertEqual(pages.first().title, "Fruit")

    def test_list_pages_ordered_by_updated(self):
        page1 = create_page(self.book.id, title="First", content="")
        page2 = create_page(self.book.id, title="Second", content="")
        pages = list_pages(book_id=self.book.id)
        self.assertEqual(pages[0].id, page2.id)
        self.assertEqual(pages[1].id, page1.id)
