from pydantic import BaseModel


class CreateBookRequest(BaseModel):
    title: str
    author: str


class UpdateBookRequest(BaseModel):
    title: str
    author: str


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    is_available: bool
