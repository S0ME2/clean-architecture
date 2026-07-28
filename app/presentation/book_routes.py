from fastapi import APIRouter, Depends, Response, status

from app.application.book_service import BookService
from app.domain.entities import Book
from app.presentation.dependencies import get_book_service
from app.presentation.schemas import (
    BookResponse,
    CreateBookRequest,
    UpdateBookRequest,
)

router = APIRouter(
    prefix="/books",
    tags=["Books"],
)


def book_to_dict(book: Book) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "is_available": book.is_available,
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BookResponse)
def create_book(
    request: CreateBookRequest, service: BookService = Depends(get_book_service)
):
    book = service.create_book(title=request.title, author=request.author)

    return book_to_dict(book)


@router.get("", response_model=list[BookResponse])
def get_all_books(service: BookService = Depends(get_book_service)):
    books = service.get_all_books()

    return [book_to_dict(book) for book in books]


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, service: BookService = Depends(get_book_service)):
    book = service.get_book(book_id)

    return book_to_dict(book)


@router.put("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    request: UpdateBookRequest,
    service: BookService = Depends(get_book_service),
):
    book = service.update_book(
        book_id=book_id, title=request.title, author=request.author
    )

    return book_to_dict(book)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, service: BookService = Depends(get_book_service)):
    service.delete_book(book_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{book_id}/borrow", response_model=BookResponse)
def borrow_book(book_id: int, service: BookService = Depends(get_book_service)):
    book = service.borrow_book(book_id)

    return book_to_dict(book)


@router.post("/{book_id}/return", response_model=BookResponse)
def return_book(book_id: int, service: BookService = Depends(get_book_service)):
    book = service.return_book(book_id)

    return book_to_dict(book)
