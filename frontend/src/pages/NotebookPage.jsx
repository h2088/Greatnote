import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getTopicFolders } from '../api/folders'
import { getNotebook, updateNotebook } from '../api/notebooks'
import { getPage, toggleFavoritePage, updatePage } from '../api/pages'
import ImportWebpageModal from '../components/ImportWebpageModal'
import PageEditor from '../components/PageEditor'
import ShareModal from '../components/ShareModal'
import Sidebar from '../components/Sidebar'

export default function NotebookPage() {
  const { id: notebookId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [activePageId, setActivePageId] = useState(() => {
    const pageParam = searchParams.get('page')
    return pageParam ? Number(pageParam) : null
  })
  const [showShare, setShowShare] = useState(false)
  const [showImportWebpage, setShowImportWebpage] = useState(false)
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleInput, setTitleInput] = useState('')

  const { data: notebook } = useQuery({
    queryKey: ['notebook', notebookId],
    queryFn: () => getNotebook(notebookId).then((r) => r.data),
  })

  const { data: activePage } = useQuery({
    queryKey: ['page', activePageId],
    queryFn: () => getPage(activePageId).then((r) => r.data),
    enabled: !!activePageId,
  })

  const { data: folders = [] } = useQuery({
    queryKey: ['topic-folders', notebookId],
    queryFn: () => getTopicFolders(notebookId).then((r) => r.data),
    enabled: !!notebookId,
  })

  useEffect(() => {
    if (searchParams.get('page')) {
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    if (notebook?.pages?.length > 0 && !activePageId) {
      setActivePageId(notebook.pages[0].id)
    }
  }, [notebook, activePageId])

  useEffect(() => {
    setActivePageId(null)
  }, [notebookId])

  const renameMutation = useMutation({
    mutationFn: (title) => updateNotebook(notebookId, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notebooks'] })
      queryClient.invalidateQueries({ queryKey: ['notebook', notebookId] })
    },
  })

  const renamePageMutation = useMutation({
    mutationFn: ({ id, title }) => updatePage(id, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notebook', notebookId] })
      queryClient.invalidateQueries({ queryKey: ['page', activePageId] })
    },
  })

  const toggleFavoriteMutation = useMutation({
    mutationFn: ({ id, isFavorite }) => toggleFavoritePage(id, isFavorite),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorite-pages'] })
      queryClient.invalidateQueries({ queryKey: ['page', activePageId] })
      queryClient.invalidateQueries({ queryKey: ['notebook', notebookId] })
    },
  })

  const movePageFolderMutation = useMutation({
    mutationFn: ({ id, topicFolder }) => updatePage(id, { topic_folder: topicFolder }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notebook', notebookId] })
      queryClient.invalidateQueries({ queryKey: ['page', activePageId] })
      queryClient.invalidateQueries({ queryKey: ['favorite-pages'] })
    },
  })

  const handleRenameNotebook = () => {
    if (titleInput.trim() && titleInput !== notebook?.title) {
      renameMutation.mutate(titleInput.trim())
    }
    setEditingTitle(false)
  }

  const handlePageTitleKeyDown = (e, page) => {
    if (e.key === 'Enter') {
      renamePageMutation.mutate({ id: page.id, title: e.target.value })
      e.target.blur()
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        activeNotebookId={notebookId}
        activePageId={activePageId}
        onSelectPage={setActivePageId}
      />

      <main className="flex min-w-0 flex-1 flex-col bg-white">
        {notebook && (
          <header className="flex items-center gap-3 border-b border-gray-100 px-6 py-3">
            {editingTitle ? (
              <input
                autoFocus
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                onBlur={handleRenameNotebook}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRenameNotebook()
                  if (e.key === 'Escape') setEditingTitle(false)
                }}
                className="border-b border-indigo-400 px-1 text-sm font-medium text-gray-700 outline-none"
              />
            ) : (
              <button
                onClick={() => {
                  setEditingTitle(true)
                  setTitleInput(notebook?.title ?? '')
                }}
                className="text-sm text-gray-500 hover:text-gray-800"
                title="Rename notebook"
              >
                {notebook?.title}
              </button>
            )}

            {activePage && (
              <>
                <span className="text-gray-300">/</span>
                <input
                  key={activePage.id}
                  defaultValue={activePage.title}
                  onKeyDown={(e) => handlePageTitleKeyDown(e, activePage)}
                  onBlur={(e) => renamePageMutation.mutate({ id: activePage.id, title: e.target.value })}
                  className="border-b border-transparent px-1 text-sm font-semibold text-gray-800 outline-none focus:border-indigo-400"
                />
                <select
                  value={activePage.topic_folder || ''}
                  onChange={(e) => movePageFolderMutation.mutate({ id: activePage.id, topicFolder: e.target.value || null })}
                  className="rounded border border-gray-200 bg-gray-100 px-2 py-1 text-xs text-gray-600"
                  title="Move page to topic folder"
                >
                  <option value="">Unsorted</option>
                  {folders.map((folder) => (
                    <option key={folder.id} value={folder.id}>{folder.name}</option>
                  ))}
                </select>
              </>
            )}

            <div className="ml-auto flex items-center gap-2">
              <button
                onClick={() => setShowImportWebpage(true)}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-gray-500 transition-colors hover:bg-indigo-50 hover:text-indigo-600"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 015.656 5.656l-4.243 4.243a4 4 0 01-5.656-5.656m-1.414-1.414a4 4 0 00-5.656 5.656l4.243 4.243a4 4 0 005.656-5.656" />
                </svg>
                Import webpage
              </button>

              {activePage && (
                <>
                  <button
                    onClick={() => toggleFavoriteMutation.mutate({ id: activePage.id, isFavorite: !activePage.is_favorite })}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                      activePage.is_favorite
                        ? 'text-yellow-500 hover:bg-yellow-50 hover:text-yellow-600'
                        : 'text-gray-400 hover:bg-gray-50 hover:text-yellow-500'
                    }`}
                    title={activePage.is_favorite ? 'Unfavorite' : 'Favorite'}
                  >
                    {activePage.is_favorite ? (
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                      </svg>
                    ) : (
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                      </svg>
                    )}
                  </button>
                  <button
                    onClick={() => setShowShare(true)}
                    className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-gray-500 transition-colors hover:bg-indigo-50 hover:text-indigo-600"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
                      />
                    </svg>
                    {activePage.share_token ? 'Shared' : 'Share'}
                  </button>
                </>
              )}
            </div>
          </header>
        )}

        {activePage ? (
          <>
            <div className="flex-1 overflow-hidden">
              <PageEditor key={activePage.id} page={activePage} />
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center text-gray-400">
            <div className="text-center">
              <div className="mb-3 text-4xl">Page</div>
              <p className="text-sm">Select a page or create one in the sidebar</p>
              {notebook && (
                <div className="mt-6 flex flex-col items-center gap-2">
                  <button
                    onClick={() => setShowImportWebpage(true)}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                  >
                    Import webpage
                  </button>
                  <p className="text-xs text-gray-400">
                    Topic folders are available in the left sidebar under this notebook.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {showShare && activePage && (
        <ShareModal
          page={activePage}
          notebookId={notebookId}
          onClose={() => {
            setShowShare(false)
            queryClient.invalidateQueries({ queryKey: ['page', activePageId] })
          }}
        />
      )}

      {showImportWebpage && (
        <ImportWebpageModal
          notebookId={notebookId}
          folders={folders}
          defaultFolderId={activePage?.topic_folder || ''}
          onClose={() => setShowImportWebpage(false)}
          onImported={(page) => setActivePageId(page.id)}
        />
      )}
    </div>
  )
}
