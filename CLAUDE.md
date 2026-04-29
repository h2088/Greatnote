# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GreatNote is a minimal personal notes app. A single user creates, edits, and deletes notes. No auth, no sharing, no collaboration.

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
python manage.py test notes.tests.test_services.NoteServiceTests.test_create_note
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

- `frontend/src/App.jsx` — root component, holds global note list state
- `frontend/src/components/` — presentational components (`NoteList`, `NoteEditor`, `NoteCard`)
- `frontend/src/api.js` — thin fetch wrapper around `/api/notes/`

State is kept simple: `App` fetches notes on mount and passes callbacks down. No external state library.

### Backend

- `backend/notes/` — the only app besides Django admin
  - `models.py` — `Note` model: `title`, `content`, `created_at`, `updated_at`
  - `serializers.py` — DRF serializer for `Note`
  - `views.py` — `NoteViewSet` (ModelViewSet)
  - `services.py` — **business logic lives here**. Views are thin and delegate to service functions. This is the layer that is unit-tested.
  - `tests/test_services.py` — unit tests for `services.py`
  - `tests/test_views.py` — integration tests for the API endpoints

- `backend/greatnote/urls.py` — routes `/api/notes/` to the `NoteViewSet` via DRF router

### API Contract

The frontend expects a REST API at `/api/notes/` with standard DRF ModelViewSet behavior:

- `GET /api/notes/` — list all notes (newest first)
- `POST /api/notes/` — create a note
- `GET /api/notes/<id>/` — retrieve a note
- `PUT /api/notes/<id>/` — update a note
- `DELETE /api/notes/<id>/` — delete a note

Response shape:
```json
{
  "id": 1,
  "title": "...",
  "content": "...",
  "created_at": "2026-04-29T12:00:00Z",
  "updated_at": "2026-04-29T12:00:00Z"
}
```

## CORS

Django CORS headers is installed. In dev, `CORS_ALLOW_ALL_ORIGINS = True`. The frontend Vite proxy is **not** used — CORS is enabled instead so the frontend talks directly to `:8000`.
