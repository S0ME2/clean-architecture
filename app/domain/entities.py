from dataclasses import dataclass

from app.domain.exceptions import (
    BookAlreadyBorrowedError,
    BookAlreadyReturnedError,
    BorrowedBookDeletionError,
    BorrowedBookUpdateError,
    InvalidBookAuthorError,
    InvalidBookTitleError,
)


@dataclass
class Book:
    id: int | None
    title: str
    author: str
    is_available: bool = True

    def validate(self) -> None:
        self.title = self.title.strip()
        self.author = self.author.strip()

        if not self.title:
            raise InvalidBookTitleError("Book title cannot be empty")

        if not self.author:
            raise InvalidBookAuthorError("Book author cannot be empty")

    def borrow_book(self) -> None:
        if not self.is_available:
            raise BookAlreadyBorrowedError(
                f"The book '{self.title}' is already borrowed"
            )
        self.is_available = False

    def return_book(self) -> None:
        if self.is_available:
            raise BookAlreadyReturnedError(f"The book '{self.title}' is not borrowed")
        self.is_available = True

    def update_book(self, title: str, author: str) -> None:
        if not self.is_available:
            raise BorrowedBookUpdateError("A borrowed book cannot be updated")

        title = title.strip()
        author = author.strip()

        if not title:
            raise InvalidBookTitleError("Book title cannot be empty")

        if not author:
            raise InvalidBookAuthorError("Book author cannot be empty")

        self.title = title
        self.author = author

    def ensure_can_be_deleted(self) -> None:
        if not self.is_available:
            raise BorrowedBookDeletionError("A borrowed book cannot be deleted")
