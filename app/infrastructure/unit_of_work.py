import psycopg

from app.infrastructure.book_repository import BookRepository


class UnitOfWork:
    def __init__(self, database_url: str):
        self.connection = psycopg.connect(database_url)
        self.books = BookRepository(self.connection)

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()
