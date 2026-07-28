class DomainError(Exception):
    """Base exception for business-rule violations."""


class BookAlreadyBorrowedError(DomainError):
    """Raised when someone tries to borrow an unavailable book."""


class BookAlreadyReturnedError(DomainError):
    """Raised when someone tries to return a book that is not borrowed."""


class InvalidBookTitleError(DomainError):
    """Raised when a book title is empty."""


class InvalidBookAuthorError(DomainError):
    """Raised when a book author is empty."""


class BorrowedBookDeletionError(DomainError):
    """Raised when someone tries to delete a borrowed book."""


class BorrowedBookUpdateError(DomainError):
    """Raised when someone tries to update a borrowed book."""


class BookNotFoundError(DomainError):
    """Raised when a requested book does not exist."""
