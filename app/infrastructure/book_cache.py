import json

from app.domain.entities import Book


class BookCache:
    def __init__(self, redis_client, ttl: int):
        self.redis = redis_client
        self.ttl = ttl

    def get_book_by_id(self, book_id: int) -> Book | None:
        data = self.redis.get(f"book:{book_id}")

        if data is None:
            return None

        book_data = json.loads(data)
        return Book(
            id=book_data["id"],
            title=book_data["title"],
            author=book_data["author"],
            is_available=book_data["is_available"],
        )

    def set_book(self, book: Book):
        data = {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "is_available": book.is_available,
        }

        self.redis.set(f"book:{book.id}", json.dumps(data), ex=self.ttl)

    def get_all_books(self) -> list[Book]:
        data = self.redis.get("books:all")

        if data is None:
            return None

        books_data = json.loads(data)
        books = []

        for book_data in books_data:
            books.append(
                Book(
                    id=book_data["id"],
                    title=book_data["title"],
                    author=book_data["author"],
                    is_available=book_data["is_available"],
                )
            )

        return books

    def set_all_books(self, books: list[Book]):
        books_data = []

        for book in books:
            books_data.append(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "is_available": book.is_available,
                }
            )

        self.redis.set(
            "books:all",
            json.dumps(books_data),
            ex=self.ttl,
        )

    def delete_book(self, book_id: int):
        self.redis.delete(f"book:{book_id}")

    def delete_all_books(self):
        self.redis.delete("books:all")
