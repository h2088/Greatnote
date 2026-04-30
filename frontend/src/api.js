const API_BASE = 'http://127.0.0.1:8000/api'

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
    },
    cache: 'no-store',
    ...options,
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  if (response.status === 204) {
    return null
  }
  return response.json()
}

export function getBooks(search = '') {
  const query = search ? `?search=${encodeURIComponent(search)}` : ''
  return request(`/books/${query}`)
}

export function createBook(title = 'Untitled Book') {
  return request('/books/', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
}

export function updateBook(id, title) {
  return request(`/books/${id}/`, {
    method: 'PUT',
    body: JSON.stringify({ title }),
  })
}

export function deleteBook(id) {
  return request(`/books/${id}/`, {
    method: 'DELETE',
  })
}

export function getPages(bookId, search = '') {
  let query = `?book_id=${bookId}`
  if (search) query += `&search=${encodeURIComponent(search)}`
  return request(`/pages/${query}`)
}

export function createPage(bookId, title = 'Untitled', content = '', is_favorite = false) {
  return request('/pages/', {
    method: 'POST',
    body: JSON.stringify({ book: bookId, title, content, is_favorite }),
  })
}

export function updatePage(id, { title, content, is_favorite }) {
  return request(`/pages/${id}/`, {
    method: 'PUT',
    body: JSON.stringify({ title, content, is_favorite }),
  })
}

export function deletePage(id) {
  return request(`/pages/${id}/`, {
    method: 'DELETE',
  })
}
