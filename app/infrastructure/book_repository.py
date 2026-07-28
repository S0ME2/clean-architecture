from psycopg.rows import dict_row

from app.domain.entities import Book


class BookRepository:
    def __init__(self, connection):
        self.connection = connection

    def create_book(self, book: Book) -> Book:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO books (title, author, is_available)
                VALUES (%s, %s, %s)
                RETURNING id, title, author, is_available
                """,
                (book.title, book.author, book.is_available),
            )

            row = cursor.fetchone()

        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            is_available=row["is_available"],
        )

    def get_book_by_id(self, book_id: int) -> Book | None:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, title, author, is_available
                FROM books
                WHERE id = %s
                """,
                (book_id,),
            )

            row = cursor.fetchone()

        if row is None:
            return None

        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            is_available=row["is_available"],
        )

    def get_all_books(self) -> list[Book]:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, title, author, is_available
                FROM books
                ORDER BY id
                """
            )

            rows = cursor.fetchall()

        books = []

        for row in rows:
            books.append(
                Book(
                    id=row["id"],
                    title=row["title"],
                    author=row["author"],
                    is_available=row["is_available"],
                )
            )

        return books

    def update_book(self, book: Book) -> Book:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE books
                SET title = %s,
                    author = %s,
                    is_available = %s
                WHERE id = %s
                RETURNING id, title, author, is_available
                """,
                (
                    book.title,
                    book.author,
                    book.is_available,
                    book.id,
                ),
            )

            row = cursor.fetchone()

        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            is_available=row["is_available"],
        )

    def delete_book(self, book_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM books
                WHERE id = %s
                """,
                (book_id,),
            )
