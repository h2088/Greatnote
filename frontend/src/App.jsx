import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import PageEditor from './components/PageEditor.jsx'
import { getBooks, createBook, deleteBook, getPages, createPage, updatePage, deletePage } from './api.js'
import './App.css'

export default function App() {
  const [books, setBooks] = useState([])
  const [selectedBookId, setSelectedBookId] = useState(null)
  const [selectedPageId, setSelectedPageId] = useState(null)

  const fetchBooks = async () => {
    const data = await getBooks()
    setBooks(data)
    return data
  }

  useEffect(() => {
    fetchBooks()
  }, [])

  const handleToggleBook = async (bookId) => {
    if (selectedBookId === bookId) {
      setSelectedBookId(null)
      return
    }
    setSelectedBookId(bookId)
    const pages = await getPages(bookId)
    setBooks(prev => prev.map(b => b.id === bookId ? { ...b, pages } : b))
    if (pages.length > 0) {
      setSelectedPageId(pages[0].id)
    } else {
      setSelectedPageId(null)
    }
  }

  const handleCreateBook = async () => {
    const newBook = await createBook('Untitled Book')
    const updated = await getBooks()
    setBooks(updated)
    setSelectedBookId(newBook.id)
    setSelectedPageId(null)
  }

  const handleCreatePage = async () => {
    if (!selectedBookId) return
    const newPage = await createPage(selectedBookId, 'Untitled', '')
    const pages = await getPages(selectedBookId)
    setBooks(prev => prev.map(b => b.id === selectedBookId ? { ...b, pages } : b))
    setSelectedPageId(newPage.id)
  }

  const handleDeleteBook = async (bookId) => {
    await deleteBook(bookId)
    const updated = await getBooks()
    setBooks(updated)
    if (selectedBookId === bookId) {
      setSelectedBookId(null)
      setSelectedPageId(null)
    }
  }

  const handleSelectPage = (pageId) => {
    setSelectedPageId(pageId)
  }

  const handleUpdatePage = async (id, { title, content }) => {
    const book = books.find(b => b.id === selectedBookId)
    if (!book) return
    const page = book.pages?.find(p => p.id === id)
    if (!page) return
    if (page.title === title && page.content === content) return
    await updatePage(id, { title, content })
    const pages = await getPages(selectedBookId)
    setBooks(prev => prev.map(b => b.id === selectedBookId ? { ...b, pages } : b))
  }

  const handleDeletePage = async (pageId) => {
    await deletePage(pageId)
    const pages = await getPages(selectedBookId)
    setBooks(prev => prev.map(b => b.id === selectedBookId ? { ...b, pages } : b))
    if (selectedPageId === pageId) {
      setSelectedPageId(pages.length > 0 ? pages[0].id : null)
    }
  }

  const selectedBook = books.find(b => b.id === selectedBookId)
  const selectedPage = selectedBook?.pages?.find(p => p.id === selectedPageId)

  return (
    <div className="app">
      <Sidebar
        books={books}
        selectedPageId={selectedPageId}
        selectedBookId={selectedBookId}
        onSelectPage={handleSelectPage}
        onDeletePage={handleDeletePage}
        onDeleteBook={handleDeleteBook}
        onCreateBook={handleCreateBook}
        onCreatePage={handleCreatePage}
        onToggleBook={handleToggleBook}
      />
      {selectedPage ? (
        <PageEditor
          key={selectedPage.id}
          page={selectedPage}
          onChange={handleUpdatePage}
        />
      ) : (
        <div className="empty-editor">
          <p>Select a book and page to start writing</p>
        </div>
      )}
    </div>
  )
}
