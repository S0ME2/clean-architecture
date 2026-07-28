from app.domain.entities import Book
from app.domain.exceptions import BookNotFoundError


class BookService:
    def __init__(self, uow, cache):
        self.uow = uow
        self.cache = cache

    def create_book(self, title: str, author: str) -> Book:
        book = Book(id=None, title=title, author=author)

        book.validate()

        created_book = self.uow.books.create_book(book)
        self.uow.commit()

        self.cache.delete_all_books()

        return created_book

    def get_book_from_database(self, book_id: int) -> Book:
        book = self.uow.books.get_book_by_id(book_id)

        if book is None:
            raise BookNotFoundError(f"Book with ID {book_id} not found")

        return book

    def get_book(self, book_id: int) -> Book:
        cached_book = self.cache.get_book_by_id(book_id)
        if cached_book is not None:
            return cached_book

        book = self.get_book_from_database(book_id)

        self.cache.set_book(book)

        return book

    def get_all_books(self) -> list[Book] | None:
        cached_books = self.cache.get_all_books()
        if cached_books is not None:
            return cached_books

        books = self.uow.books.get_all_books()
        self.cache.set_all_books(books)

        return books

    def update_book(self, book_id: int, title: str, author: str) -> Book:
        book = self.get_book_from_database(book_id)

        book.update_book(title, author)

        updated_book = self.uow.books.update_book(book)
        self.uow.commit()

        self.cache.delete_book(book_id)
        self.cache.delete_all_books()

        return updated_book

    def delete_book(self, book_id: int) -> None:
        book = self.get_book_from_database(book_id)

        book.ensure_can_be_deleted()

        self.uow.books.delete_book(book_id)
        self.uow.commit()

        self.cache.delete_book(book_id)
        self.cache.delete_all_books()

    def borrow_book(self, book_id: int) -> Book:
        book = self.get_book_from_database(book_id)

        book.borrow_book()

        updated_book = self.uow.books.update_book(book)
        self.uow.commit()

        self.cache.delete_book(book_id)
        self.cache.delete_all_books()

        return updated_book

    def return_book(self, book_id: int) -> Book:
        book = self.get_book_from_database(book_id)

        book.return_book()

        updated_book = self.uow.books.update_book(book)
        self.uow.commit()

        self.cache.delete_book(book_id)
        self.cache.delete_all_books()

        return updated_book
