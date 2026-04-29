# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GreatNote is a minimal personal notes app with a Book/Page hierarchy. A single user creates books, and each book contains pages. No auth, no sharing, no collaboration.

## Tech Stack

- **Frontend**: React (Vite), plain CSS (no component library)
- **Backend**: Django, Django REST Framework
- **Database**: SQLite (default for local dev)

## Running the App

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Django admin: http://127.0.0.1:8000/admin/
API root: http://127.0.0.1:8000/api/

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite dev server: http://localhost:5173

## Testing

### Backend (Django)

Run all tests:
```bash
cd backend
python manage.py test
```

Run a single test file:
```bash
python manage.py test notes.tests.test_services
```

Run a single test case:
```bash
python manage.py test notes.tests.test_services.BookServiceTests.test_create_book_with_title
```

### Frontend

```bash
cd frontend
npm test
```

## Linting

```bash
cd backend
ruff check .
```

```bash
cd frontend
npm run lint
```

## Architecture

### Frontend

- `frontend/src/App.jsx` — root component, holds global book list state
- `frontend/src/components/Sidebar.jsx` — left sidebar: search, book list (expandable), page list, create/delete actions
- `frontend/src/components/PageEditor.jsx` — right editor: title input + content textarea with auto-save
- `frontend/src/api.js` — thin fetch wrapper around `/api/books/` and `/api/pages/`

State is kept simple: `App` fetches books on mount. Each book can be expanded to show its pages. No external state library.

### Backend

- `backend/notes/` — the only app besides Django admin
  - `models.py` — `Book` and `Page` models with `title`, `content`, `created_at`, `updated_at`
  - `serializers.py` — DRF serializers; `BookSerializer` nests `PageSerializer` (read-only)
  - `views.py` — `BookViewSet` and `PageViewSet` (ModelViewSet)
  - `services.py` — **business logic lives here**. Views are thin and delegate to service functions. This is the layer that is unit-tested.
  - `tests/test_services.py` — unit tests for `services.py`
  - `tests/test_views.py` — integration tests for the API endpoints

- `backend/greatnote/urls.py` — routes `/api/` to `notes.urls`
- `backend/notes/urls.py` — DRF router for `/api/books/` and `/api/pages/`

### API Contract

The frontend expects a REST API with standard DRF ModelViewSet behavior:

**Books:**
- `GET /api/books/` — list all books (newest first)
- `POST /api/books/` — create a book
- `GET /api/books/<id>/` — retrieve a book (includes nested pages)
- `PUT /api/books/<id>/` — update a book title
- `DELETE /api/books/<id>/` — delete a book (cascades to pages)

**Pages:**
- `GET /api/pages/` — list all pages (supports `?book_id=` and `?search=`)
- `POST /api/pages/` — create a page
- `GET /api/pages/<id>/` — retrieve a page
- `PUT /api/pages/<id>/` — update a page title/content
- `DELETE /api/pages/<id>/` — delete a page

Response shapes:
```json
// Book
{
  "id": 1,
  "title": "My Journal",
  "pages": [...],
  "created_at": "2026-04-29T12:00:00Z",
  "updated_at": "2026-04-29T12:00:00Z"
}

// Page
{
  "id": 1,
  "book": 1,
  "title": "Untitled",
  "content": "",
  "created_at": "2026-04-29T12:00:00Z",
  "updated_at": "2026-04-29T12:00:00Z"
}
```

## CORS

Django CORS headers is installed. In dev, `CORS_ALLOW_ALL_ORIGINS = True`. The frontend Vite proxy is **not** used — CORS is enabled instead so the frontend talks directly to `:8000`.
