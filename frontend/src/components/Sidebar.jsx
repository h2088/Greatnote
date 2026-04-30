import { useMemo, useState } from 'react'

function BookSection({ book, isExpanded, onToggle, selectedPageId, onSelectPage, onDeletePage, onDeleteBook, onUpdateBook, onToggleFavorite }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(book.title)

  const handleDoubleClick = () => {
    setIsEditing(true)
    setEditTitle(book.title)
  }

  const handleSave = () => {
    setIsEditing(false)
    if (editTitle.trim() && editTitle !== book.title) {
      onUpdateBook(book.id, editTitle.trim())
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      setIsEditing(false)
      setEditTitle(book.title)
    }
  }

  return (
    <div className="book-section">
      <div className="book-header" onClick={onToggle}>
        <span className={`book-chevron ${isExpanded ? 'expanded' : ''}`}>▶</span>
        {isEditing ? (
          <input
            className="book-title-input-inline"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleKeyDown}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="book-title" onDoubleClick={handleDoubleClick}>{book.title}</span>
        )}
        <button
          className="book-delete"
          onClick={(e) => {
            e.stopPropagation()
            if (window.confirm('Delete this book and all its pages?')) {
              onDeleteBook(book.id)
            }
          }}
        >
          ×
        </button>
      </div>
      {isExpanded && (
        <div className="page-list">
          {book.pages?.map(page => (
            <div
              key={page.id}
              className={`page-item ${page.id === selectedPageId ? 'selected' : ''}`}
              onClick={() => onSelectPage(page.id)}
            >
              <button
                className={`page-star ${page.is_favorite ? 'favorited' : ''}`}
                onClick={(e) => {
                  e.stopPropagation()
                  onToggleFavorite(page.id)
                }}
              >
                {page.is_favorite ? '★' : '☆'}
              </button>
              <span className="page-title">{page.title || 'Untitled'}</span>
              <button
                className="page-delete"
                onClick={(e) => {
                  e.stopPropagation()
                  if (window.confirm('Delete this page?')) {
                    onDeletePage(page.id)
                  }
                }}
              >
                ×
              </button>
            </div>
          ))}
          {(!book.pages || book.pages.length === 0) && (
            <div className="empty-pages">No pages yet</div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Sidebar({ books, selectedPageId, selectedBookId, onSelectPage, onDeletePage, onDeleteBook, onUpdateBook, onCreateBook, onCreatePage, onToggleBook, onToggleFavorite }) {
  const [search, setSearch] = useState('')

  const filteredBooks = useMemo(() => {
    if (!search.trim()) return books
    const term = search.toLowerCase()
    return books
      .map(book => {
        const matchingPages = (book.pages || []).filter(p =>
          p.title.toLowerCase().includes(term) ||
          p.content.toLowerCase().includes(term)
        )
        const titleMatches = book.title.toLowerCase().includes(term)
        return {
          ...book,
          pages: matchingPages,
          _matchesSearch: matchingPages.length > 0 || titleMatches,
        }
      })
      .filter(book => book._matchesSearch)
  }, [books, search])

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <input
          type="text"
          className="search-input"
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="sidebar-actions">
        <button className="action-btn" onClick={onCreateBook}>+ New Book</button>
        <button className="action-btn" onClick={onCreatePage} disabled={!selectedBookId}>
          + New Page
        </button>
      </div>
      <div className="sidebar-content">
        {filteredBooks.map(book => (
          <BookSection
            key={book.id}
            book={book}
            isExpanded={selectedBookId === book.id}
            onToggle={() => onToggleBook(book.id)}
            selectedPageId={selectedPageId}
            onSelectPage={onSelectPage}
            onDeletePage={onDeletePage}
            onDeleteBook={onDeleteBook}
            onUpdateBook={onUpdateBook}
            onToggleFavorite={onToggleFavorite}
          />
        ))}
        {filteredBooks.length === 0 && (
          <div className="empty-state">No books found</div>
        )}
      </div>
    </div>
  )
}
