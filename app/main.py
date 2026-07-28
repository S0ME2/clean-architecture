from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import BookNotFoundError, DomainError
from app.presentation.book_routes import router as book_router

app = FastAPI(title="Library API")


@app.exception_handler(BookNotFoundError)
def handle_book_not_found(request: Request, error: BookNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(DomainError)
def handle_domain_error(request: Request, error: DomainError):
    return JSONResponse(status_code=400, content={"detail": str(error)})


app.include_router(book_router)


@app.get("/")
def root():
    return {"message": "Welcome to the Library API!"}
