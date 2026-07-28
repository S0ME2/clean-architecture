# Clean Architecture Library API

A small FastAPI project that teaches **how to design a Clean Architecture project**, not only how to copy one folder structure.

The application is a library API where books can be created, read, updated, deleted, borrowed and returned. It uses:

- FastAPI for HTTP;
- PostgreSQL with direct SQL through Psycopg;
- a simple Unit of Work for transactions;
- Redis for caching;
- Docker Compose for running everything together.

The architecture is intentionally small. It avoids advanced patterns until they solve a visible problem.

> **First study session:** read sections 1–8. They explain how the requirements became classes and how one request moves through the application. The remaining sections teach how to design your own project and provide reference material.

## Choose your path

You do not need to read all 31 sections in order.

| Your goal | Read |
|---|---|
| Understand this repository | Sections 1–8 |
| Learn to design your own project | Sections 9–16 |
| Understand why each file exists | Sections 17–22 |
| Run and debug the project | Sections 23–27 |
| Review terms, limits and exercises | Sections 28–31 |

The README is long because it is both a tutorial and a reference. Treat only your current path as required reading.

---

# Part I — Understand this project

## 1. Run it before studying it

You only need Docker and Docker Compose.

```bash
make build
```

Open:

```text
http://localhost:8888/docs
```

Try these actions in order:

1. Create a book with `POST /books`.
2. Borrow it with `POST /books/{book_id}/borrow`.
3. Try borrowing it again.
4. Return it with `POST /books/{book_id}/return`.
5. Update it with `PUT /books/{book_id}`.
6. Delete it with `DELETE /books/{book_id}`.

Borrowing the same book twice should return an error similar to:

```json
{
  "detail": "The book 'Clean Architecture' is already borrowed"
}
```

That error proves that the project contains a business rule, not only CRUD and SQL.

Check the containers:

```bash
make ps
```

Expected services:

```text
library_api
library_postgres
library_redis
```

> `make reset` deletes all PostgreSQL and Redis data. Do not use it unless you want a fresh database.

---

## 2. Start from requirements, not folders

A common mistake is to begin Clean Architecture by creating folders named `domain`, `application` and `infrastructure` before knowing what belongs in them.

Start with plain requirements instead.

This project began with these actions:

```text
Create a book
Get one book
Get all books
Update a book
Delete a book
Borrow a book
Return a book
```

It also began with these rules:

```text
A book must have a title.
A book must have an author.
A borrowed book cannot be borrowed again.
An available book cannot be returned.
A borrowed book cannot be updated.
A borrowed book cannot be deleted.
```

Now separate the words into three groups.

### Business things

These are things people in the real problem understand:

```text
Book
Title
Author
Availability
```

### Business actions

These are meaningful actions in the problem:

```text
Create
Update
Delete
Borrow
Return
```

### Technical tools

These exist because of the chosen technology:

```text
FastAPI
PostgreSQL
Psycopg
Redis
Docker
HTTP
JSON
```

This separation gives us the first architecture decision:

> Business things and rules belong near the center. Technical tools stay outside them.

The folders come **after** this decision.

### How one requirement creates code in several layers

One requirement does not always belong to one file. Each layer handles a different part of it.

| Requirement | Domain | Application | Infrastructure | Presentation |
|---|---|---|---|---|
| Create a book | Validate `Book` | Coordinate creation and commit | Run `INSERT` | Accept `POST /books` JSON |
| Get a book | No new business behavior | Choose cache or database | Run `SELECT`, read/write Redis | Return `GET /books/{id}` JSON |
| Borrow a book | `Book.borrow_book()` decides if allowed | Load, call rule, save, commit, clear cache | Run `SELECT` and `UPDATE` | Expose `POST /books/{id}/borrow` |
| Delete a book | `ensure_can_be_deleted()` decides if allowed | Coordinate delete and commit | Run `DELETE` | Expose `DELETE /books/{id}` |

This table prevents a common misunderstanding:

> A feature is not placed in one layer. A feature travels through layers, while each layer keeps only its own responsibility.

---

## 3. How the classes were chosen

Do not create a class for every noun. Create a class when related data and behavior need to stay together or when several operations share the same dependency.

This project contains these main classes:

| Class | Why it is a class | What its methods share |
|---|---|---|
| `Book` | A book has state and business behavior | `id`, `title`, `author`, `is_available` |
| `BookService` | Book operations share the same Unit of Work and cache | `self.uow`, `self.cache` |
| `BookRepository` | SQL operations share one database connection | `self.connection` |
| `UnitOfWork` | Transaction operations and repositories share one connection | `self.connection`, `self.books` |
| `BookCache` | Cache operations share one Redis client and TTL | `self.redis`, `self.ttl` |

Other pieces are classes for different reasons:

| Class type | Why it exists |
|---|---|
| `CreateBookRequest` | Pydantic class describing accepted JSON |
| `BookResponse` | Pydantic class describing returned JSON |
| `BookAlreadyBorrowedError` | Exception type identifying one specific failure |

Routes are functions because they do not own shared state. FastAPI gives them the objects they need.

`book_to_dict()` is a function because it performs one stateless conversion. It does not need an object or stored dependencies.

### A practical class-or-function rule

Use a class when at least one of these is true:

1. It represents a business thing with state and behavior.
2. Several methods need the same dependency, such as a database connection.
3. The object must live for a period of time and keep that shared state.
4. The framework requires a class, as Pydantic does for schemas.

Use a function when:

1. It performs one small stateless operation.
2. It does not need to remember anything between calls.
3. Creating an object would add no meaning.

Do not ask, “Can this be a class?” Almost anything can be a class.

Ask:

> What useful state or responsibility would this object own?

If there is no clear answer, prefer a function.

---

## 4. The four main roles

Ignore Docker, Redis, schemas and configuration for a moment.

The core request flow has four roles:

| Part | Simple meaning | Question it answers |
|---|---|---|
| `Book` entity | The rules | “Is this action allowed?” |
| `BookService` | The coordinator | “What steps must happen?” |
| `BookRepository` | The SQL worker | “How do we load or store it?” |
| FastAPI route | The HTTP entrance | “Which operation should this request call?” |

The first mental model is:

```text
Route receives the request
    ↓
Service coordinates the operation
    ↓
Entity checks the business rule
    ↓
Repository runs SQL
```

Two supporting roles appear later:

```text
UnitOfWork → commits or rolls back PostgreSQL changes
BookCache  → stores temporary Redis copies for faster reads
```

### Why these roles are separate

Imagine one route doing everything:

```python
def borrow_book(book_id: int):
    # Read the URL
    # Open PostgreSQL
    # Run SELECT
    # Check whether the book exists
    # Check whether it is already borrowed
    # Run UPDATE
    # Commit
    # Clear Redis
    # Build HTTP response
```

This function knows about HTTP, business rules, SQL, transactions, caching and response formatting.

The problem is not its number of lines. The problem is that it has many unrelated reasons to change:

- an HTTP change modifies it;
- a business-rule change modifies it;
- a database change modifies it;
- a cache change modifies it.

The separate roles make each kind of change easier to find.

---

## 5. Follow one complete request: borrow a book

Call:

```http
POST /books/1/borrow
```

### Step 1: FastAPI creates the request dependency

File:

```text
app/presentation/dependencies.py
```

For this request, FastAPI calls:

```python
get_book_service()
```

That function creates:

```text
one UnitOfWork
    ↓
one PostgreSQL connection
    ↓
one BookRepository using that connection
```

It then creates:

```python
BookService(uow=uow, cache=book_cache)
```

The result is passed into the route.

The Redis client and `BookCache` are created once when the module loads. The Unit of Work is created once per HTTP request and closed when that request finishes.

This file is sometimes called the **composition root** or **wiring layer**. In plain English, it is where real objects are assembled.

### Step 2: the route receives HTTP

File:

```text
app/presentation/book_routes.py
```

The route receives `book_id` from the URL:

```python
@router.post("/{book_id}/borrow", response_model=BookResponse)
def borrow_book(
    book_id: int,
    service: BookService = Depends(get_book_service),
):
    book = service.borrow_book(book_id)
    return book_to_dict(book)
```

The route has three HTTP responsibilities:

1. define the URL and HTTP method;
2. receive HTTP input;
3. return HTTP output.

It does not contain SQL and does not decide whether borrowing is allowed.

### Step 3: the service describes the operation

File:

```text
app/application/book_service.py
```

```python
def borrow_book(self, book_id: int) -> Book:
    book = self.get_book_from_database(book_id)

    book.borrow_book()

    updated_book = self.uow.books.update_book(book)
    self.uow.commit()

    self.cache.delete_book(book_id)
    self.cache.delete_all_books()

    return updated_book
```

Read it as plain English:

```text
Load fresh book data
→ ask the book to apply its rule
→ save the changed book
→ commit the transaction
→ clear stale cache entries
→ return the result
```

This complete operation is a **use case**. In this small project, use cases are methods of `BookService` rather than separate classes.

### Step 4: the repository loads the book

The service calls:

```python
self.uow.books.get_book_by_id(book_id)
```

`self.uow.books` is a `BookRepository` created by `UnitOfWork`.

The repository executes:

```sql
SELECT id, title, author, is_available
FROM books
WHERE id = %s
```

PostgreSQL returns a row. The repository converts it into:

```python
Book(
    id=row["id"],
    title=row["title"],
    author=row["author"],
    is_available=row["is_available"],
)
```

The service now works with a business object instead of a database row.

### Step 5: the entity protects the rule

File:

```text
app/domain/entities.py
```

```python
def borrow_book(self) -> None:
    if not self.is_available:
        raise BookAlreadyBorrowedError(f"The book '{self.title}' is already borrowed")

    self.is_available = False
```

The entity checks:

```text
Is this action allowed for this book's current state?
```

If it is allowed, the in-memory object changes:

```text
is_available: true → false
```

No SQL has run yet for this change. The Python object has changed in memory.

### Step 6: the repository saves the changed state

The service passes the changed `Book` back to the repository:

```python
self.uow.books.update_book(book)
```

The repository executes:

```sql
UPDATE books
SET title = %s,
    author = %s,
    is_available = %s
WHERE id = %s
RETURNING id, title, author, is_available
```

### Step 7: Unit of Work commits

The service calls:

```python
self.uow.commit()
```

The Unit of Work delegates to the shared PostgreSQL connection:

```python
self.connection.commit()
```

The database change is now final.

### Step 8: stale Redis values are deleted

Redis may still contain:

```text
book:1     → is_available: true
books:all  → list containing the old book
```

The service deletes both cached values. The next GET request rebuilds them from PostgreSQL.

### Step 9: the result travels back to HTTP

The return path is:

```text
BookRepository returns Book
→ BookService returns Book
→ route converts Book to dictionary
→ FastAPI validates BookResponse
→ client receives JSON
```

The complete round trip is:

```text
HTTP request
→ dependency wiring
→ route
→ service
→ repository SELECT
→ Book entity
→ business method
→ repository UPDATE
→ Unit of Work commit
→ cache invalidation
→ response mapping
→ HTTP response
```

If you can explain this flow without looking, you understand the center of the project.

---

## 6. What happens when an error occurs?

Suppose the loaded book has:

```text
is_available = false
```

The entity raises:

```python
BookAlreadyBorrowedError
```

Nothing catches it inside the entity, repository, service or route. It travels upward:

```text
Book entity
→ BookService
→ FastAPI route
→ FastAPI exception handler
```

`app/main.py` catches every `DomainError`:

```python
@app.exception_handler(DomainError)
def handle_domain_error(request: Request, error: DomainError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(error)},
    )
```

Meanwhile, `get_book_service()` receives the failure and runs:

```python
uow.rollback()
```

Then its `finally` block closes the connection:

```python
uow.close()
```

There are therefore two separate responses to the same failure:

```text
Database concern → rollback and close connection
HTTP concern     → convert exception into status 400 JSON
```

The domain exception itself knows nothing about either PostgreSQL rollback or HTTP status codes.

---

## 7. How data changes shape while moving through the app

One concept may have several representations because each boundary needs different information.

### Incoming HTTP JSON

```json
{
  "title": "Clean Architecture",
  "author": "Robert C. Martin"
}
```

### Pydantic request schema

```python
CreateBookRequest(
    title="Clean Architecture",
    author="Robert C. Martin",
)
```

This object exists to validate the HTTP request.

### Domain entity

```python
Book(
    id=None,
    title="Clean Architecture",
    author="Robert C. Martin",
    is_available=True,
)
```

This object exists to hold business state and behavior.

### PostgreSQL row

```text
id | title              | author              | is_available
1  | Clean Architecture | Robert C. Martin    | true
```

This representation exists for storage.

### HTTP response

```json
{
  "id": 1,
  "title": "Clean Architecture",
  "author": "Robert C. Martin",
  "is_available": true
}
```

These are not four unrelated books. They are four shapes used at different boundaries.

### Why not use one class everywhere?

Because the responsibilities differ:

- a create request has no database ID yet;
- the entity has business methods;
- a PostgreSQL row is storage data;
- a response should expose only API fields.

For this small project, manual mapping keeps those changes visible.

---

## 8. The one Clean Architecture rule to remember

> Business rules should not depend on technical tools.

In Python, a source-code dependency usually appears as an import or direct knowledge of another concrete object.

This is allowed:

```python
# infrastructure/book_repository.py
from app.domain.entities import Book
```

Outer database code may know the inner business object.

This would be wrong:

```python
# domain/entities.py
import psycopg
from fastapi import HTTPException
```

Now the business object depends on PostgreSQL and FastAPI.

The source dependencies point inward:

```text
presentation → application → domain
infrastructure ────────────→ domain
```

The arrows mean:

```text
imports, uses or knows about
```

They do not describe runtime order.

### Runtime flow

```text
route → service → repository → PostgreSQL
```

### Source-code dependency direction

```text
outer technical code → inner business code
```

This seems contradictory at first: the service calls the repository at runtime, but the application file does not import `BookRepository` directly. It receives `uow` from the wiring layer and uses the operations it provides.

This project uses Python's simple duck typing instead of explicit repository interfaces. A stricter version could define interfaces in the application layer, but that additional code is deliberately postponed.

> **First-session stopping point:** if sections 2–8 make sense, stop reading and trace the code yourself. The next part teaches how to design another project.

---

# Part II — Design your own Clean Architecture project

## 9. The repeatable design process

Use this process for a small new application.

### Step 1: write actions and rules in plain language

Do not begin with files or classes.

Example for a task application:

```text
Create a task
Get tasks
Rename a task
Complete a task
Delete a task

A task must have a title.
A completed task cannot be renamed.
A completed task cannot be completed again.
```

### Step 2: identify the main business object

Ask:

1. What thing has an identity?
2. What state changes over time?
3. What rules belong to that state?

For the task app:

```text
Thing: Task
Identity: id
State: title, is_completed
Behavior: rename, complete, delete permission
```

That suggests one entity:

```python
@dataclass
class Task:
    id: int | None
    title: str
    is_completed: bool = False
```

Do not create classes for every property. `TaskTitle` and `CompletionStatus` are unnecessary unless they later contain important rules of their own.

### Step 3: put state-based rules on the entity

Ask:

> Can this rule be decided using only this object's current data?

If yes, it usually belongs on the entity.

```python
def complete(self) -> None:
    if self.is_completed:
        raise TaskAlreadyCompletedError()

    self.is_completed = True
```

```python
def rename(self, title: str) -> None:
    if self.is_completed:
        raise CompletedTaskUpdateError()

    if not title.strip():
        raise InvalidTaskTitleError()

    self.title = title.strip()
```

The entity should not load itself from PostgreSQL or return HTTP responses.

### Step 4: turn user actions into service methods

Each complete user goal usually becomes one service method:

```text
Create a task   → create_task()
Get one task    → get_task()
Get all tasks   → get_all_tasks()
Rename a task   → update_task()
Complete task   → complete_task()
Delete task     → delete_task()
```

The service method coordinates steps that cross boundaries:

```text
load object
→ call business behavior
→ save object
→ commit
→ update cache if needed
```

The service should not contain SQL or FastAPI response creation.

### Step 5: derive repository methods from service needs

Do not invent repository methods first.

Look at what the service needs from storage:

```text
create task
get task by ID
get all tasks
update task
delete task
```

That produces:

```python
class TaskRepository:
    def create_task(...):
        ...

    def get_task_by_id(...):
        ...

    def get_all_tasks(...):
        ...

    def update_task(...):
        ...

    def delete_task(...):
        ...
```

The repository methods are chosen because the application needs them, not because every repository must always have exactly five CRUD methods.

### Step 6: decide the transaction boundary

Ask:

> Which database changes must succeed or fail together?

For a simple task update, one repository call and one commit may be enough.

For a money transfer:

```text
subtract from account A
add to account B
record transfer
commit all three
```

That operation clearly needs one Unit of Work.

This project introduces Unit of Work early because it is one of the concepts being taught. In your own tiny CRUD project, you may begin with a repository and add Unit of Work when transaction ownership becomes unclear or multiple changes must be committed together.

### Step 7: define HTTP schemas and routes

Schemas come from the API contract, not from the database table.

For creating a task:

```python
class CreateTaskRequest(BaseModel):
    title: str
```

For returning a task:

```python
class TaskResponse(BaseModel):
    id: int
    title: str
    is_completed: bool
```

Then create routes that translate HTTP into service calls:

```text
POST /tasks               → service.create_task(...)
GET /tasks/{task_id}      → service.get_task(...)
POST /tasks/{id}/complete → service.complete_task(...)
```

Routes should know URL paths, status codes, schemas and dependency injection. They should not know SQL or contain business rules.

### Step 8: wire concrete objects together

Create one place that knows the implementations:

```text
PostgreSQL URL
→ UnitOfWork
→ TaskRepository

Redis URL
→ TaskCache

UnitOfWork + TaskCache
→ TaskService

TaskService
→ FastAPI route
```

This is the composition root. It is where technical choices are allowed to meet.

### The task application's resulting structure

After making the decisions above, a small task project could look like this:

```text
app/
├── domain/
│   ├── entities.py         # Task and its rules
│   └── exceptions.py       # Task business failures
├── application/
│   └── task_service.py     # Complete task operations
├── infrastructure/
│   ├── task_repository.py  # Direct task SQL
│   └── unit_of_work.py     # Connection, commit, rollback
├── presentation/
│   ├── task_routes.py      # HTTP endpoints
│   ├── schemas.py          # Request and response shapes
│   └── dependencies.py     # Construct TaskService
├── config.py
└── main.py
```

The structure was not chosen from memory. It was derived:

```text
Task state and rules          → domain/entities.py
Task failures                 → domain/exceptions.py
Complete user operations      → application/task_service.py
Required SQL operations       → infrastructure/task_repository.py
Transaction ownership         → infrastructure/unit_of_work.py
HTTP contract                 → presentation/schemas.py and task_routes.py
Object construction           → presentation/dependencies.py
Application startup           → main.py
```

A complete request would then be:

```text
POST /tasks/5/complete
→ task route
→ TaskService.complete_task()
→ TaskRepository.get_task_by_id()
→ Task.complete()
→ TaskRepository.update_task()
→ UnitOfWork.commit()
→ HTTP response
```

This is the missing bridge between a list of architecture rules and a real folder tree.

### Step 9: add optional infrastructure last

Add Redis, email, file storage, queues or external APIs only after the core request works.

The core should still be understandable without them:

```text
route → service → entity → repository
```

---

## 10. A placement decision tree

When writing new code, ask these questions in order.

### Question 1: is this a business rule or business behavior?

Examples:

```text
A borrowed book cannot be deleted.
A completed task cannot be renamed.
An order cannot be paid twice.
```

Place it in:

```text
domain entity
```

### Question 2: is this the sequence of a complete user operation?

Examples:

```text
load book → borrow → save → commit
load order → charge payment → mark paid → save
```

Place it in:

```text
application service or use-case class
```

### Question 3: does it communicate with a technical system?

Examples:

```text
SQL
Redis commands
email provider
filesystem
external HTTP API
```

Place it in:

```text
infrastructure
```

### Question 4: does it deal with HTTP input or output?

Examples:

```text
route path
HTTP method
status code
request schema
response schema
```

Place it in:

```text
presentation
```

### Question 5: does it construct and connect objects?

Examples:

```text
create UnitOfWork
create repository
create cache
create service
```

Place it in:

```text
dependency wiring / composition root
```

### Question 6: is it only configuration?

Examples:

```text
database URL
Redis URL
cache TTL
```

Place it in:

```text
configuration module or environment
```

If code appears to belong in two places, separate the two responsibilities rather than choosing a random folder.

### How large should each file be?

Clean Architecture does not require one class per file. File size is a secondary decision.

For a small project, related small definitions can stay together:

```text
domain/exceptions.py  → all book business exceptions
presentation/schemas.py → all book request and response schemas
```

Split a file when:

- it contains unrelated concepts;
- finding one responsibility becomes difficult;
- several developers repeatedly edit unrelated parts of the same file;
- one feature grows enough to deserve its own module.

Do not split files only to make the folder tree look more architectural.

---

## 11. How to decide where a rule belongs

Not every validation is automatically a domain rule.

Use this test:

> Would the rule still matter if the application used no FastAPI, no PostgreSQL and no Redis?

### Domain rule

```text
A borrowed book cannot be deleted.
```

It remains true in a command-line app or paper-based library. Put it in `Book`.

### Application workflow rule

```text
After borrowing, save the book and clear its cache.
```

This describes the operation across several components. Put it in `BookService`.

### Database rule

```text
The books table primary key must be unique.
```

PostgreSQL enforces this storage guarantee.

### HTTP validation

```text
book_id must be an integer path parameter.
```

FastAPI handles this at the presentation boundary.

### Rules can be protected in more than one place

A required title is protected by the entity because it is a business requirement. PostgreSQL also uses `NOT NULL` as a final storage safety net.

Duplicating a critical rule across the appropriate boundaries is different from scattering its business meaning everywhere.

---

## 12. How many classes should you create?

There is no required number.

### Begin with one entity per main stateful business concept

For this project:

```text
Book
```

If loans become real records with their own ID, dates and state, then add:

```text
Loan
```

Do not create `Loan` only because the word appears in conversation. Create it when the system must store and reason about a loan independently.

### Begin with one service per small feature area

For this project:

```text
BookService
```

For a larger library:

```text
BookService
LoanService
MemberService
```

Split a service when it starts coordinating unrelated business areas, not merely because it has several methods.

### Begin with one repository per main persisted business object

For this project:

```text
BookRepository
```

If `Loan` becomes a persisted entity:

```text
LoanRepository
```

Do not automatically create one repository per database table. Join tables and technical tables may not represent separate business concepts.

### Create infrastructure classes around shared clients

Examples:

```text
BookRepository owns a PostgreSQL connection
BookCache owns a Redis client
EmailSender owns an email-provider client
```

The shared client gives the class a clear reason to exist.

---

## 13. How components communicate without becoming coupled

There are two different questions:

1. Who calls whom at runtime?
2. Who imports whose concrete implementation?

### Runtime call

`BookService` calls:

```python
self.uow.books.get_book_by_id(book_id)
```

### Source import

`book_service.py` does not import:

```python
BookRepository
UnitOfWork
BookCache
Redis
Psycopg
```

It receives objects from `dependencies.py`.

That means the service knows what operations it needs, but not how the concrete objects were constructed.

This is simple dependency inversion through duck typing.

### Why dependency wiring is important

Without one wiring place, routes might create their own database and cache objects:

```python
def borrow_book(...):
    connection = psycopg.connect(...)
    repository = BookRepository(connection)
    cache = BookCache(...)
    service = BookService(...)
```

That construction would be repeated and mixed with HTTP code.

`dependencies.py` centralizes that knowledge.

---

## 14. When to use explicit interfaces

This beginner project does not define abstract repository or Unit of Work classes.

The service simply expects an object with:

```text
uow.books.get_book_by_id()
uow.books.update_book()
uow.commit()
```

This is enough to learn the architecture.

Add explicit interfaces or `Protocol` classes when:

- several implementations must follow the same contract;
- developers keep guessing which methods are required;
- tests need clear fake implementations;
- a team benefits from stricter type checking;
- infrastructure is replaced often.

Do not add interfaces only because a diagram says Clean Architecture must contain them.

The rule is dependency direction, not a mandatory number of files.

---

## 15. A worksheet for designing a new project

Before writing code, complete this table.

### A. Business requirements

```text
What can the user do?
1.
2.
3.

What must never happen?
1.
2.
3.
```

### B. Main business objects

```text
Object:
Identity:
State:
Behavior:
Rules:
```

### C. Use cases

```text
Use case:
Input:
Steps:
Output:
Possible business errors:
```

### D. Persistence needs

```text
What must be loaded?
What must be inserted?
What must be updated?
What must be deleted?
Which changes must commit together?
```

### E. HTTP boundary

```text
Method and path:
Request fields:
Response fields:
Status code:
```

### F. Technical dependencies

```text
Database:
Cache:
External services:
Configuration:
```

Only after filling this out should you choose files and classes.

---

## 16. Graduation check: can you design another project?

Consider an equipment-rental API.

Requirements:

```text
Create equipment
List equipment
Rent equipment
Return equipment
Delete equipment

Equipment must have a name.
Rented equipment cannot be rented again.
Available equipment cannot be returned.
Rented equipment cannot be deleted.
```

Before reading the answer, decide:

1. What is the entity?
2. What fields does it have?
3. Which methods belong on it?
4. What service methods are needed?
5. What repository methods are needed?
6. What belongs in presentation?
7. What belongs in infrastructure?

<details>
<summary>One reasonable design</summary>

### Entity

```python
@dataclass
class Equipment:
    id: int | None
    name: str
    is_available: bool = True

    def validate(self): ...
    def rent(self): ...
    def return_equipment(self): ...
    def ensure_can_be_deleted(self): ...
```

### Service

```text
EquipmentService
- create_equipment()
- get_equipment()
- get_all_equipment()
- rent_equipment()
- return_equipment()
- delete_equipment()
```

### Repository

```text
EquipmentRepository
- create_equipment()
- get_equipment_by_id()
- get_all_equipment()
- update_equipment()
- delete_equipment()
```

### Presentation

```text
CreateEquipmentRequest
EquipmentResponse
Equipment routes
```

### Infrastructure

```text
PostgreSQL repository
Unit of Work
optional Redis cache
```

The class names changed, but the decision process stayed the same.

</details>

If you can produce a similar design and explain every placement, you are no longer copying this repository. You are applying the architecture.

---

# Part III — File-by-file reference

## 17. `Book`: business state and behavior

File:

```text
app/domain/entities.py
```

Why it exists:

```text
A book has identity, state and rules that must stay together.
```

Fields:

```text
id            → identity assigned by PostgreSQL
 title         → required business data
 author        → required business data
 is_available  → state used by borrow, return, update and delete rules
```

Methods are chosen from business behavior:

```text
validate()               → title and author rules
borrow_book()            → borrowing transition
return_book()            → returning transition
update_book()            → update rule and state change
ensure_can_be_deleted()  → deletion permission
```

It does not contain `save()`, `SELECT`, Redis or HTTP status codes because those are not book behavior.

`@dataclass` only generates ordinary data-class helpers such as the constructor and readable representation. It does not create database or architecture behavior.

---

## 18. `BookService`: complete operations

File:

```text
app/application/book_service.py
```

Why it exists:

```text
A complete user action crosses several components and needs one coordinator.
```

Why it is one class:

```text
All book use cases share the same uow and cache dependencies.
```

How methods were chosen:

```text
Each public user action became one public method.
```

The private supporting idea:

```python
get_book_from_database()
```

exists because writes must use fresh PostgreSQL state rather than possibly stale Redis state.

The service may coordinate technical actions, but it should not contain direct SQL, Redis commands or FastAPI objects.

---

## 19. `BookRepository`: persistence adapter

File:

```text
app/infrastructure/book_repository.py
```

Why it exists:

```text
The application needs books, but SQL details should have one home.
```

Why it is a class:

```text
Every repository method uses the same PostgreSQL connection.
```

Its two jobs are:

1. execute parameterized SQL;
2. map between PostgreSQL rows and `Book` entities.

It does not decide whether update, borrow or delete is allowed.

---

## 20. `UnitOfWork`: transaction owner

File:

```text
app/infrastructure/unit_of_work.py
```

Why it exists:

```text
The complete use case, not an individual SQL method, should decide when to commit.
```

It owns:

```text
one PostgreSQL connection
one BookRepository using that connection
```

It provides:

```text
commit
rollback
close
```

With several repositories, all can use the same transaction.

---

## 21. `BookCache`: Redis adapter

File:

```text
app/infrastructure/book_cache.py
```

Why it exists:

```text
Redis commands and JSON serialization are technical concerns.
```

Why it is a class:

```text
All methods share the Redis client and cache TTL.
```

It maps between:

```text
Book entity ↔ JSON string stored in Redis
```

It does not decide when a book may be borrowed. The service decides when cache entries should be read or invalidated.

---

## 22. Schemas, routes, wiring, configuration and startup

### `schemas.py`

Defines HTTP request and response shapes.

### `book_routes.py`

Defines URLs, HTTP methods, status codes, input extraction and returned response data.

### `dependencies.py`

Constructs and connects concrete runtime objects.

### `config.py`

Loads environment values such as database URL, Redis URL and cache TTL.

### `main.py`

Creates the FastAPI application, registers exception handlers and includes routers.

---

# Part IV — Operations and reference

## 23. Project structure

```text
.
├── app/
│   ├── domain/                 # Business entities and business errors
│   ├── application/            # Complete user operations
│   ├── infrastructure/         # PostgreSQL, Redis and transactions
│   ├── presentation/           # FastAPI routes and schemas
│   ├── config.py               # Environment configuration
│   └── main.py                 # FastAPI setup
├── sql/
│   └── schema.sql              # Creates the books table
├── compose.yaml                # API + PostgreSQL + Redis
├── Dockerfile                  # Builds the API container
├── Makefile                    # Short commands
├── pyproject.toml              # Python dependencies
└── uv.lock                     # Locked dependency versions
```

Folder names do not make the architecture clean. Responsibilities and dependency direction do.

---

## 24. API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/books` | Create a book |
| `GET` | `/books` | List books |
| `GET` | `/books/{book_id}` | Get one book |
| `PUT` | `/books/{book_id}` | Replace title and author |
| `DELETE` | `/books/{book_id}` | Delete an available book |
| `POST` | `/books/{book_id}/borrow` | Borrow an available book |
| `POST` | `/books/{book_id}/return` | Return a borrowed book |

### Create a book

```bash
curl -X POST http://localhost:8888/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Architecture",
    "author": "Robert C. Martin"
  }'
```

### Borrow it

```bash
curl -X POST http://localhost:8888/books/1/borrow
```

### Return it

```bash
curl -X POST http://localhost:8888/books/1/return
```

---

## 25. Run commands

### Docker

Build and start:

```bash
make build
```

Check status:

```bash
make ps
```

Follow API logs:

```bash
make logs
```

Stop containers:

```bash
make down
```

Delete PostgreSQL and Redis data:

```bash
make reset
```

### Local Python with `uv`

Local execution requires PostgreSQL and Redis to be running.

```bash
cp .env.example .env
make setup
make dev
```

Run `sql/schema.sql` against PostgreSQL before starting the API.

---

## 26. Inspect the running system

### PostgreSQL rows

```bash
docker compose exec postgres \
  psql -U postgres -d library \
  -c "SELECT * FROM books ORDER BY id;"
```

### PostgreSQL structure

```bash
docker compose exec postgres \
  psql -U postgres -d library \
  -c "\d books"
```

### Redis keys

```bash
docker compose exec redis redis-cli KEYS "*"
```

### Clear only Redis

```bash
docker compose exec redis redis-cli FLUSHDB
```

---

## 27. Common problems

### API container exits

Read the real error first:

```bash
docker compose logs --tail=200 api
```

### `relation "books" does not exist`

Run `sql/schema.sql` or recreate the study database when losing its data is acceptable:

```bash
make reset
make build
```

### Old `is_borrowed` column

This project uses the opposite meaning:

```text
is_available = true  → may be borrowed
is_available = false → currently borrowed
```

Renaming `is_borrowed` without inverting values changes their meaning. For a study database, recreating it is usually easiest.

### Old Redis values

```bash
docker compose exec redis redis-cli FLUSHDB
```

### BuildKit reports a missing snapshot

Clear executable cache mounts first:

```bash
docker builder prune -a --filter type=exec.cachemount
```

Then rebuild.

---

## 28. Terms in plain English

| Term | Meaning here |
|---|---|
| Domain | The business concepts and rules |
| Entity | A business object with identity, state and behavior |
| Business rule | A condition deciding whether an action is allowed |
| Use case | One complete user goal, such as borrowing a book |
| Application service | A class coordinating several use cases |
| Repository | Code loading and saving entities through SQL |
| Unit of Work | One owner for commit and rollback |
| Presentation | HTTP routes, request data and response data |
| Infrastructure | Technical implementations such as PostgreSQL and Redis |
| Dependency | One part importing, using or knowing another |
| Composition root | The place where concrete objects are constructed and connected |
| Cache | A temporary faster copy of data |
| Source of truth | The authoritative data store, PostgreSQL in this project |

---

## 29. Deliberate limitations

This is a learning project, not a production template.

It intentionally excludes:

- migrations;
- automated tests;
- authentication;
- asynchronous database access;
- connection pooling;
- pagination;
- generic repositories;
- explicit abstract repository interfaces;
- one class per use case;
- CQRS;
- event buses;
- advanced cache failure recovery;
- protection against simultaneous borrow requests.

These can be learned after the current design process feels natural.

Two limitations are especially important to understand:

1. If PostgreSQL commits successfully and Redis cache deletion then fails, the API may return an error even though the database change succeeded. PostgreSQL remains the source of truth.
2. Two simultaneous borrow requests could both read an available book before either commits. Production code would need concurrency protection.

They are not fixed here because the required solutions would distract from the beginner architecture lesson.

---

## 30. Recommended exercises

### Exercise 1: explain before changing

Without opening the README, explain:

```text
Why Book is a class
Why BookService is a class
Why BookRepository is a class
Why routes are functions
Where objects are constructed
How a borrow error reaches HTTP
```

### Exercise 2: trace the request

Add temporary prints in:

```text
dependencies
route
service
entity
repository
```

Borrow a book, observe the order, then remove the prints.

### Exercise 3: add one business rule

Reject titles longer than 255 characters.

Decide which boundaries should protect the limit and explain why.

### Exercise 4: add PATCH

Create partial book updates while preserving the borrowed-book update rule.

### Exercise 5: make Unit of Work visibly necessary

Add a `Loan` entity, table and repository.

Borrowing should:

```text
mark book unavailable
create loan record
commit both together
```

### Exercise 6: design before coding

Use the worksheet in section 15 for a new domain such as appointments, inventory or courses. Draw the request flow before creating folders.

### Exercise 7: add interfaces later

After the current flow feels obvious, add repository and Unit of Work protocols. Then judge whether they made responsibilities clearer or only added code.

---

## 31. What “clean” means here

Clean does not mean using the maximum number of patterns.

In this project, clean means:

- business rules are easy to find;
- complete user operations are easy to trace;
- HTTP code stays in presentation;
- SQL stays in repositories;
- transaction control has one owner;
- Redis stays outside the domain;
- concrete objects are assembled in one wiring place;
- every class has a clear reason to exist;
- new features can be placed by reasoning, not guessing.

The final test is not whether your folders match this repository.

The final test is:

> Given new requirements, can you explain what each piece is responsible for, where it belongs and what it is allowed to know?

---

## Further reading

Read the project first. Use these after the request flow and design process make sense:

- [The Clean Architecture — Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [FastAPI dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Psycopg transaction management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
- [Redis cache-aside caching](https://redis.io/solutions/caching/)
- [Using uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/)
- [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)