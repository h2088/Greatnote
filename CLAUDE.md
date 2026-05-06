# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (Django)
```bash
cd backend
python manage.py runserver        # dev server on http://localhost:8000
python manage.py migrate          # apply migrations (first-time setup)
python manage.py makemigrations   # after changing models
python manage.py test             # run tests
python manage.py createsuperuser  # create admin user
python manage.py shell            # Django REPL
```

### Frontend (React + Vite)
```bash
cd frontend
npm run dev      # dev server on http://localhost:5173
npm run build    # production build
npm run preview  # preview production build
npm run lint     # ESLint
```

## Architecture

Full-stack notebook app: Django REST Framework backend + React 19 SPA frontend.

### Backend (`backend/`)

Single Django app `notebooks` handles all logic. Key files:

- `config/settings.py` — JWT config (60-min access, 7-day refresh with rotation), CORS allowed for `localhost:5173`, SQLite by default
- `config/urls.py` — mounts `notebooks/urls.py` at root
- `notebooks/models.py` — three models: `Notebook` (FK→User), `Page` (FK→Notebook, content stored as JSONField for TipTap state), `ShareLink` (UUID token, FK→Page)
- `notebooks/views.py` — function-based auth views (register, me) + DRF generic class-based views for resources
- `notebooks/serializers.py` — separate list vs. detail serializers (list excludes page content); `share_token` is a computed `SerializerMethodField`
- `notebooks/permissions.py` — `IsNotebookOwner` and `IsPageOwner` enforce object-level ownership

**URL structure:**
```
/api/auth/register/
/api/auth/login/
/api/auth/token/refresh/
/api/auth/me/
/api/notebooks/                        # list/create
/api/notebooks/<id>/                   # retrieve/update/delete
/api/notebooks/<notebook_pk>/pages/    # list/create pages
/api/pages/<id>/                       # retrieve/update/delete page
/api/pages/<id>/share/                 # POST create / DELETE revoke share link
/api/shared/<token>/                   # public read-only (AllowAny)
```

### Frontend (`frontend/src/`)

- `main.jsx` — wraps app in `AuthProvider`, `QueryClientProvider`, `BrowserRouter`
- `App.jsx` — route definitions; `ProtectedRoute` redirects to `/login` if unauthenticated
- `contexts/AuthContext.jsx` — global auth state; stores JWT access/refresh tokens in `localStorage`
- `api/client.js` — Axios instance with interceptors: adds `Authorization: Bearer` header on every request; on 401, queues requests and attempts token refresh; on refresh failure, clears storage and redirects to `/login`
- `api/auth.js`, `api/notebooks.js`, `api/pages.js` — thin API method modules
- `components/PageEditor.jsx` — TipTap rich text editor with debounced auto-save via React Query mutation
- `components/ShareModal.jsx` — creates/revokes `ShareLink`; parent invalidates queries on close

**Data flow:** Vite proxies `/api/*` → `http://localhost:8000` in dev. React Query manages server state with keys like `['notebook', id]` and `['page', id]`; mutations invalidate relevant queries on success.

### Ownership & Permissions

Object-level ownership is enforced on every mutating endpoint. There is no concept of shared write access — a user can only modify their own notebooks and pages.

| Permission class | Check | Applied to |
|---|---|---|
| `IsNotebookOwner` | `obj.user == request.user` | `NotebookDetailView` (retrieve/update/delete a notebook) |
| `IsPageOwner` | `obj.notebook.user == request.user` | `PageDetailView` (retrieve/update/delete a page) |

List endpoints (`NotebookListCreateView`, `PageListCreateView`) do not use object-level permissions; instead they filter `queryset` to `request.user` so a user never sees another user's notebooks or pages. The share endpoint (`/api/shared/<token>/`) bypasses auth entirely with `AllowAny`.

When adding new models or views, follow the same pattern: either attach an object-level permission class that traverses FKs back to `User`, or filter the queryset in `get_queryset`.

### Auto-Save

The editor auto-saves on a **1-second debounce** while the user types.

Flow in `PageEditor.jsx`:
1. TipTap `onUpdate` fires on every keystroke → `clearTimeout` + `setTimeout(..., 1000)`
2. After 1s of idle input, `save()` callback reads `editor.getJSON()` and calls `updatePage(page.id, { content })`
3. `updatePage` sends a `PATCH /api/pages/<id>/` with the JSON content object
4. `AutoSaveIndicator` renders transient status: `saving` → `saved` (green, 2s) → `null`

**Important conventions:**
- Content is stored as **TipTap JSON**, not HTML or plain text. Do not change the storage format without updating the serializer and model.
- The debounce timer is cleared on unmount (`useEffect` cleanup) to prevent state updates after the component is gone.
- When the active `page.id` changes, `PageEditor` uses `editor.commands.setContent(newContent, false)` to swap the editor document without triggering a new save cycle.
- Save failures show `error` state in the indicator but do not block editing.

### Auth Flow

1. Login/register → backend returns `{access, refresh, user}`; stored in `localStorage`
2. All requests include `Authorization: Bearer {access}` via Axios request interceptor
3. On 401: interceptor POSTs to `/api/auth/token/refresh/`; backend rotates both tokens (`ROTATE_REFRESH_TOKENS=True`); queued requests retry with new token
4. On refresh failure: logout, redirect to `/login`
