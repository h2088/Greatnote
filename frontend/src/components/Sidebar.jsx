import { useState } from 'react'

function BookSection({ book, isExpanded, onToggle, selectedPageId, onSelectPage, onDeletePage, onDeleteBook }) {
  return (
    <div className="book-section">
      <div className="book-header" onClick={onToggle}>
        <span className={`book-chevron ${isExpanded ? 'expanded' : ''}`}>▶</span>
        <span className="book-title">{book.title}</span>
        <button
          className="book-delete"
          onClick={(e) => {
            e.stopPropagation()
            onDeleteBook(book.id)
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
              <span className="page-title">{page.title || 'Untitled'}</span>
              <button
                className="page-delete"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeletePage(page.id)
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

export default function Sidebar({ books, selectedPageId, selectedBookId, onSelectPage, onDeletePage, onDeleteBook, onCreateBook, onCreatePage, onToggleBook }) {
  const [search, setSearch] = useState('')

  const filteredBooks = search
    ? books.map(book => ({
        ...book,
        pages: (book.pages || []).filter(p =>
          p.title.toLowerCase().includes(search.toLowerCase()) ||
          p.content.toLowerCase().includes(search.toLowerCase())
        )
      })).filter(book => book.pages.length > 0 || book.title.toLowerCase().includes(search.toLowerCase()))
    : books

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
          />
        ))}
        {filteredBooks.length === 0 && (
          <div className="empty-state">No books found</div>
        )}
      </div>
    </div>
  )
}
