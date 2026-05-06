import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getNotebooks, getNotebook, createNotebook, deleteNotebook, updateNotebook } from '../api/notebooks'
import { createPage, deletePage, getFavoritePages, toggleFavoritePage } from '../api/pages'
import { useAuth } from '../contexts/AuthContext'

export default function Sidebar({ activeNotebookId, activePageId, onSelectPage }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [editingNotebook, setEditingNotebook] = useState(null)
  const [newNotebookTitle, setNewNotebookTitle] = useState('')
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 250)
    return () => clearTimeout(timer)
  }, [query])

  const { data: notebooks = [] } = useQuery({
    queryKey: ['notebooks', debouncedQuery],
    queryFn: () => getNotebooks(debouncedQuery ? { search: debouncedQuery } : undefined).then((r) => r.data),
  })

  const { data: favorites = [] } = useQuery({
    queryKey: ['favorite-pages'],
    queryFn: () => getFavoritePages().then((r) => r.data),
  })

  const createNotebookMutation = useMutation({
    mutationFn: () => createNotebook({ title: 'New Notebook' }),
    onSuccess: ({ data }) => {
      queryClient.invalidateQueries({ queryKey: ['notebooks'] })
      navigate(`/notebooks/${data.id}`)
    },
  })

  const deleteNotebookMutation = useMutation({
    mutationFn: (id) => deleteNotebook(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notebooks'] })
      navigate('/')
    },
  })

  const renameNotebookMutation = useMutation({
    mutationFn: ({ id, title }) => updateNotebook(id, { title }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notebooks'] }),
  })

  const createPageMutation = useMutation({
    mutationFn: (notebookId) => createPage(notebookId, { title: 'Untitled' }),
    onSuccess: ({ data }, notebookId) => {
      queryClient.invalidateQueries({ queryKey: ['notebook', notebookId] })
      onSelectPage(data.id)
    },
  })

  const deletePageMutation = useMutation({
    mutationFn: (id) => deletePage(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notebook', activeNotebookId] })
      queryClient.invalidateQueries({ queryKey: ['favorite-pages'] })
      onSelectPage(null)
    },
  })

  const toggleFavoriteMutation = useMutation({
    mutationFn: ({ id, isFavorite }) => toggleFavoritePage(id, isFavorite),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorite-pages'] })
      queryClient.invalidateQueries({ queryKey: ['notebook', activeNotebookId] })
      queryClient.invalidateQueries({ queryKey: ['page', activePageId] })
    },
  })

  const activeNotebook = notebooks.find((n) => n.id === Number(activeNotebookId))

  const { data: notebookDetail } = useQuery({
    queryKey: ['notebook', activeNotebookId],
    queryFn: () => getNotebook(activeNotebookId).then((r) => r.data),
    enabled: !!activeNotebookId,
  })

  const pages = (notebookDetail?.pages ?? []).filter(
    (pg) => !debouncedQuery || pg.title.toLowerCase().includes(debouncedQuery.toLowerCase())
  )

  const handleRenameNotebook = (nb) => {
    if (newNotebookTitle.trim() && newNotebookTitle !== nb.title) {
      renameNotebookMutation.mutate({ id: nb.id, title: newNotebookTitle.trim() })
    }
    setEditingNotebook(null)
  }

  const handleFavoriteClick = (page) => {
    if (page.notebook === Number(activeNotebookId)) {
      onSelectPage(page.id)
    } else {
      navigate(`/notebooks/${page.notebook}?page=${page.id}`)
    }
  }

  return (
    <aside className="w-64 bg-gray-900 text-gray-200 flex flex-col h-screen flex-shrink-0">
      <div className="px-4 py-4 border-b border-gray-700">
        <span className="text-white font-semibold text-lg">Greatnotes</span>
        <p className="text-gray-400 text-xs mt-0.5 truncate">{user?.username}</p>
      </div>

      {favorites.length > 0 && (
        <div className="px-3 py-2 border-b border-gray-700">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Favorites</h3>
          {favorites.map((page) => (
            <div
              key={page.id}
              onClick={() => handleFavoriteClick(page)}
              className={`flex items-center rounded px-2 py-1 cursor-pointer text-sm ${
                page.id === activePageId && page.notebook === Number(activeNotebookId)
                  ? 'text-white bg-gray-700'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              <svg className="w-3.5 h-3.5 text-yellow-400 mr-1.5 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
              <span className="truncate">{page.title || 'Untitled'}</span>
            </div>
          ))}
        </div>
      )}

      <div className="px-3 py-2 border-b border-gray-700">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search notebooks..."
          className="w-full bg-gray-800 text-gray-200 text-sm rounded-lg px-3 py-1.5 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-3 pt-3 pb-1">
          <button
            onClick={() => createNotebookMutation.mutate()}
            className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
          >
            <span className="text-lg leading-none">+</span> New notebook
          </button>
        </div>

        {notebooks.length === 0 && debouncedQuery && (
          <p className="px-4 py-3 text-xs text-gray-500">No notebooks found.</p>
        )}

        {notebooks.map((nb) => (
          <div key={nb.id}>
            <div
              className={`flex items-center group px-3 py-0.5 mx-1 rounded-lg cursor-pointer ${
                nb.id === Number(activeNotebookId)
                  ? 'bg-gray-700 text-white'
                  : 'hover:bg-gray-800 text-gray-300'
              }`}
            >
              {editingNotebook === nb.id ? (
                <input
                  autoFocus
                  value={newNotebookTitle}
                  onChange={(e) => setNewNotebookTitle(e.target.value)}
                  onBlur={() => handleRenameNotebook(nb)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRenameNotebook(nb)
                    if (e.key === 'Escape') setEditingNotebook(null)
                  }}
                  className="flex-1 bg-transparent text-sm outline-none py-1.5"
                />
              ) : (
                <Link
                  to={`/notebooks/${nb.id}`}
                  className="flex-1 text-sm py-1.5 truncate"
                >
                  {nb.title}
                </Link>
              )}

              <div className="hidden group-hover:flex items-center gap-1 ml-1">
                <button
                  title="Rename"
                  onClick={() => { setEditingNotebook(nb.id); setNewNotebookTitle(nb.title) }}
                  className="p-1 text-gray-500 hover:text-gray-200"
                >
                  ✎
                </button>
                <button
                  title="Delete"
                  onClick={() => {
                    if (confirm(`Delete "${nb.title}"?`)) deleteNotebookMutation.mutate(nb.id)
                  }}
                  className="p-1 text-gray-500 hover:text-red-400"
                >
                  ✕
                </button>
              </div>
            </div>

            {nb.id === Number(activeNotebookId) && (
              <div className="ml-4 mt-1 mb-2 border-l border-gray-700 pl-3">
                {pages.map((pg) => (
                  <PageItem
                    key={pg.id}
                    page={pg}
                    active={pg.id === activePageId}
                    onSelect={() => onSelectPage(pg.id)}
                    onDelete={() => {
                      if (confirm(`Delete "${pg.title}"?`)) deletePageMutation.mutate(pg.id)
                    }}
                    onToggleFavorite={() => toggleFavoriteMutation.mutate({ id: pg.id, isFavorite: !pg.is_favorite })}
                  />
                ))}
                <button
                  onClick={() => createPageMutation.mutate(nb.id)}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 py-1 mt-1"
                >
                  <span>+</span> New page
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="px-4 py-3 border-t border-gray-700">
        <button
          onClick={logout}
          title="Sign out"
          className="text-gray-500 hover:text-gray-300"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </aside>
  )
}

function PageItem({ page, active, onSelect, onDelete, onToggleFavorite }) {
  return (
    <div
      className={`flex items-center group rounded px-2 py-1 cursor-pointer text-sm ${
        active ? 'text-white bg-gray-700' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
      }`}
      onClick={onSelect}
    >
      <button
        onClick={(e) => { e.stopPropagation(); onToggleFavorite() }}
        className={`mr-1.5 flex-shrink-0 ${
          page.is_favorite ? 'text-yellow-400' : 'text-gray-600 opacity-0 group-hover:opacity-100'
        }`}
        title={page.is_favorite ? 'Unfavorite' : 'Favorite'}
      >
        {page.is_favorite ? (
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
          </svg>
        )}
      </button>
      <span className="flex-1 truncate">{page.title || 'Untitled'}</span>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete() }}
        className="hidden group-hover:block p-0.5 text-gray-600 hover:text-red-400"
        title="Delete page"
      >
        ✕
      </button>
    </div>
  )
}
