import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createNotebook, deleteNotebook, getNotebook, getNotebooks, updateNotebook } from '../api/notebooks'
import { createPage, deletePage, getFavoritePages, toggleFavoritePage, updatePage } from '../api/pages'
import { createTopicFolder, deleteTopicFolder, getTopicFolders, updateTopicFolder } from '../api/folders'
import { useAuth } from '../contexts/AuthContext'

export default function Sidebar({ activeNotebookId, activePageId, onSelectPage }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeNotebookNumber = Number(activeNotebookId)

  const [editingNotebook, setEditingNotebook] = useState(null)
  const [newNotebookTitle, setNewNotebookTitle] = useState('')
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [folderError, setFolderError] = useState('')
  const [editingFolder, setEditingFolder] = useState(null)
  const [editingFolderName, setEditingFolderName] = useState('')

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

  const { data: notebookDetail } = useQuery({
    queryKey: ['notebook', activeNotebookId],
    queryFn: () => getNotebook(activeNotebookId).then((r) => r.data),
    enabled: !!activeNotebookId,
  })

  const { data: folders = [] } = useQuery({
    queryKey: ['topic-folders', activeNotebookId],
    queryFn: () => getTopicFolders(activeNotebookId).then((r) => r.data),
    enabled: !!activeNotebookId,
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
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['notebooks'] })
      queryClient.invalidateQueries({ queryKey: ['notebook', String(variables.id)] })
    },
  })

  const renamePageMutation = useMutation({
    mutationFn: ({ id, title }) => updatePage(id, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notebook', activeNotebookId] })
      queryClient.invalidateQueries({ queryKey: ['page', activePageId] })
    },
  })

  const createPageMutation = useMutation({
    mutationFn: (notebookId) => createPage(notebookId, { title: 'Untitled' }),
    onSuccess: ({ data }, notebookId) => {
      queryClient.invalidateQueries({ queryKey: ['notebook', String(notebookId)] })
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

  const createFolderMutation = useMutation({
    mutationFn: (name) => createTopicFolder({ notebook: activeNotebookNumber, name }),
    onSuccess: () => {
      setNewFolderName('')
      setFolderError('')
      queryClient.invalidateQueries({ queryKey: ['topic-folders', activeNotebookId] })
      queryClient.invalidateQueries({ queryKey: ['notebook', activeNotebookId] })
    },
    onError: (err) => {
      const detail =
        err.response?.data?.name?.[0]
        || err.response?.data?.notebook?.[0]
        || err.response?.data?.detail
        || 'Failed to create folder'
      setFolderError(detail)
    },
  })

  const renameFolderMutation = useMutation({
    mutationFn: ({ id, name }) => updateTopicFolder(id, { name }),
    onSuccess: () => {
      setEditingFolder(null)
      setEditingFolderName('')
      queryClient.invalidateQueries({ queryKey: ['topic-folders', activeNotebookId] })
      queryClient.invalidateQueries({ queryKey: ['notebook', activeNotebookId] })
    },
  })

  const deleteFolderMutation = useMutation({
    mutationFn: (id) => deleteTopicFolder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topic-folders', activeNotebookId] })
      queryClient.invalidateQueries({ queryKey: ['notebook', activeNotebookId] })
      queryClient.invalidateQueries({ queryKey: ['page', activePageId] })
    },
  })

  const pages = useMemo(() => (
    notebookDetail?.pages?.filter(
      (page) => !debouncedQuery || page.title.toLowerCase().includes(debouncedQuery.toLowerCase())
    ) ?? []
  ), [notebookDetail?.pages, debouncedQuery])

  const pageGroups = useMemo(() => {
    const groups = folders.map((folder) => ({ id: folder.id, name: folder.name, pages: [] }))
    const byId = new Map(groups.map((group) => [group.id, group]))
    const unsorted = { id: 'none', name: 'Unsorted', pages: [] }

    pages.forEach((page) => {
      if (page.topic_folder && byId.has(page.topic_folder)) {
        byId.get(page.topic_folder).pages.push(page)
      } else {
        unsorted.pages.push(page)
      }
    })

    return [...groups, unsorted]
  }, [folders, pages])

  const handleRenameNotebook = (notebook) => {
    const title = newNotebookTitle.trim()
    if (title && title !== notebook.title) {
      renameNotebookMutation.mutate({ id: notebook.id, title })
    }
    setEditingNotebook(null)
  }

  const handleFavoriteClick = (page) => {
    if (page.notebook === activeNotebookNumber) {
      onSelectPage(page.id)
    } else {
      navigate(`/notebooks/${page.notebook}?page=${page.id}`)
    }
  }

  const handleCreateFolder = (e) => {
    e.preventDefault()
    setFolderError('')
    const name = newFolderName.trim()
    if (!name) {
      setFolderError('Folder name is required')
      return
    }
    createFolderMutation.mutate(name)
  }

  const submitFolderRename = (group) => {
    const name = editingFolderName.trim()
    if (!name || name === group.name) {
      setEditingFolder(null)
      setEditingFolderName('')
      return
    }
    renameFolderMutation.mutate({ id: group.id, name })
  }

  return (
    <aside className="flex h-screen w-72 flex-shrink-0 flex-col bg-gray-900 text-gray-200">
      <div className="border-b border-gray-700 px-4 py-4">
        <span className="text-lg font-semibold text-white">Greatnotes</span>
        <p className="mt-0.5 truncate text-xs text-gray-400">{user?.username}</p>
      </div>

      {favorites.length > 0 && (
        <div className="border-b border-gray-700 px-3 py-2">
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500">Favorites</h3>
          {favorites.map((page) => (
            <div
              key={page.id}
              onClick={() => handleFavoriteClick(page)}
              className={`flex cursor-pointer items-center rounded px-2 py-1 text-sm ${
                page.id === activePageId && page.notebook === activeNotebookNumber
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`}
            >
              <svg className="mr-1.5 h-3.5 w-3.5 flex-shrink-0 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
              <span className="truncate">{page.title || 'Untitled'}</span>
            </div>
          ))}
        </div>
      )}

      <div className="border-b border-gray-700 px-3 py-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search notebooks..."
          className="w-full rounded-lg bg-gray-800 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-3 pb-1 pt-3">
          <button
            onClick={() => createNotebookMutation.mutate()}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
          >
            <span className="text-lg leading-none">+</span> New notebook
          </button>
        </div>

        <div className="px-3 pb-1">
          <Link
            to="/shared-with-me"
            className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5V4H2v16h5m10-8h-4m0 0H9m4 0V8m0 4v4" />
            </svg>
            Shared with me
          </Link>
        </div>

        {notebooks.length === 0 && debouncedQuery && (
          <p className="px-4 py-3 text-xs text-gray-500">No notebooks found.</p>
        )}

        {notebooks.map((notebook) => (
          <div key={notebook.id}>
            <div
              className={`group mx-1 flex cursor-pointer items-center rounded-lg px-3 py-0.5 ${
                notebook.id === activeNotebookNumber
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              {editingNotebook === notebook.id ? (
                <input
                  autoFocus
                  value={newNotebookTitle}
                  onChange={(e) => setNewNotebookTitle(e.target.value)}
                  onBlur={() => handleRenameNotebook(notebook)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRenameNotebook(notebook)
                    if (e.key === 'Escape') setEditingNotebook(null)
                  }}
                  className="flex-1 bg-transparent py-1.5 text-sm outline-none"
                />
              ) : (
                <Link to={`/notebooks/${notebook.id}`} className="flex-1 truncate py-1.5 text-sm">
                  {notebook.title}
                </Link>
              )}

              <div className="ml-1 hidden items-center gap-1 group-hover:flex">
                <button
                  title="Rename"
                  onClick={() => {
                    setEditingNotebook(notebook.id)
                    setNewNotebookTitle(notebook.title)
                  }}
                  className="p-1 text-gray-500 hover:text-gray-200"
                >
                  R
                </button>
                <button
                  title="Delete"
                  onClick={() => {
                    if (confirm(`Delete "${notebook.title}"?`)) deleteNotebookMutation.mutate(notebook.id)
                  }}
                  className="p-1 text-gray-500 hover:text-red-400"
                >
                  D
                </button>
              </div>
            </div>

            {notebook.id === activeNotebookNumber && (
              <div className="mb-2 ml-4 mt-1 border-l border-gray-700 pl-3">
                <div className="pb-2 pr-2">
                  <form onSubmit={handleCreateFolder} className="flex gap-2">
                    <input
                      type="text"
                      value={newFolderName}
                      onChange={(e) => setNewFolderName(e.target.value)}
                      placeholder="New topic folder"
                      className="flex-1 rounded bg-gray-800 px-2 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                    <button
                      type="submit"
                      disabled={createFolderMutation.isPending}
                      className="rounded bg-indigo-600 px-2.5 py-1.5 text-xs text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      Add
                    </button>
                  </form>
                  {folderError && <p className="mt-1 text-[11px] text-red-400">{folderError}</p>}
                </div>

                {pageGroups.map((group) => (
                  <div key={group.id} className="mb-2 pr-2">
                    <div className="flex items-center justify-between px-2 py-1 text-[11px] uppercase tracking-wider text-gray-500">
                      {editingFolder === group.id ? (
                        <input
                          autoFocus
                          value={editingFolderName}
                          onChange={(e) => setEditingFolderName(e.target.value)}
                          onBlur={() => submitFolderRename(group)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              e.preventDefault()
                              submitFolderRename(group)
                            }
                            if (e.key === 'Escape') {
                              setEditingFolder(null)
                              setEditingFolderName('')
                            }
                          }}
                          className="w-36 rounded bg-gray-800 px-2 py-0.5 text-[11px] text-gray-200"
                        />
                      ) : (
                        <span>{group.name}</span>
                      )}

                      {group.id !== 'none' && (
                        <div className="flex items-center gap-1 text-gray-500">
                          <button
                            onClick={() => {
                              setEditingFolder(group.id)
                              setEditingFolderName(group.name)
                            }}
                            className="hover:text-gray-300"
                            title="Rename folder"
                          >
                            R
                          </button>
                          <button
                            onClick={() => {
                              if (confirm(`Delete folder "${group.name}"? Pages will be moved to Unsorted.`)) {
                                deleteFolderMutation.mutate(group.id)
                              }
                            }}
                            className="hover:text-red-400"
                            title="Delete folder"
                          >
                            D
                          </button>
                        </div>
                      )}
                    </div>

                    {group.pages.map((page) => (
                      <PageItem
                        key={page.id}
                        page={page}
                        active={page.id === activePageId}
                        onSelect={() => onSelectPage(page.id)}
                        onRename={(title) => renamePageMutation.mutate({ id: page.id, title })}
                        onDelete={() => {
                          if (confirm(`Delete "${page.title}"?`)) deletePageMutation.mutate(page.id)
                        }}
                        onToggleFavorite={() => toggleFavoriteMutation.mutate({ id: page.id, isFavorite: !page.is_favorite })}
                      />
                    ))}
                  </div>
                ))}

                <button
                  onClick={() => createPageMutation.mutate(notebook.id)}
                  className="mt-1 flex items-center gap-1 py-1 text-xs text-gray-500 hover:text-gray-300"
                >
                  <span>+</span> New page
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="border-t border-gray-700 px-4 py-3">
        <button onClick={logout} title="Sign out" className="text-gray-500 hover:text-gray-300">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </aside>
  )
}

function PageItem({ page, active, onSelect, onDelete, onToggleFavorite, onRename }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(page.title || 'Untitled')

  useEffect(() => {
    setValue(page.title || 'Untitled')
  }, [page.id, page.title])

  return (
    <div
      className={`group flex cursor-pointer items-center rounded px-2 py-1 text-sm ${
        active ? 'bg-gray-700 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
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
          <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ) : (
          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
        )}
      </button>

      <div className="min-w-0 flex-1">
        {editing ? (
          <input
            autoFocus
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onBlur={() => {
              const title = value.trim() || 'Untitled'
              if (title !== page.title) onRename(title)
              setEditing(false)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const title = value.trim() || 'Untitled'
                if (title !== page.title) onRename(title)
                setEditing(false)
              }
              if (e.key === 'Escape') {
                setValue(page.title || 'Untitled')
                setEditing(false)
              }
            }}
            className="w-full rounded bg-gray-800 px-2 py-0.5 text-xs text-gray-100"
          />
        ) : (
          <div className="truncate">{page.title || 'Untitled'}</div>
        )}
      </div>

      <button
        onClick={(e) => { e.stopPropagation(); setEditing(true) }}
        className="hidden p-0.5 text-gray-600 hover:text-gray-300 group-hover:block"
        title="Rename page"
      >
        R
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete() }}
        className="hidden p-0.5 text-gray-600 hover:text-red-400 group-hover:block"
        title="Delete page"
      >
        D
      </button>
    </div>
  )
}
