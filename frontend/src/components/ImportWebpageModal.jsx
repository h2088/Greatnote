import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { importWebpage } from '../api/pages'

export default function ImportWebpageModal({ notebookId, folders, defaultFolderId, onClose, onImported }) {
  const queryClient = useQueryClient()
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [topicFolder, setTopicFolder] = useState(defaultFolderId ? String(defaultFolderId) : '')
  const [error, setError] = useState('')

  const importMutation = useMutation({
    mutationFn: () => {
      const payload = { url: url.trim() }
      if (title.trim()) payload.title = title.trim()
      payload.topic_folder = topicFolder || null
      return importWebpage(notebookId, payload)
    },
    onSuccess: ({ data }) => {
      queryClient.invalidateQueries({ queryKey: ['notebook', String(notebookId)] })
      queryClient.invalidateQueries({ queryKey: ['notebooks'] })
      onImported?.(data)
      onClose()
    },
    onError: (err) => {
      setError(err.response?.data?.detail || 'Failed to import webpage')
    },
  })

  const submit = (e) => {
    e.preventDefault()
    setError('')
    if (!url.trim()) {
      setError('URL is required')
      return
    }
    importMutation.mutate()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Import webpage</h2>
          <button onClick={onClose} className="text-xl leading-none text-gray-400 hover:text-gray-600">&times;</button>
        </div>

        <p className="mb-4 text-sm text-gray-500">
          Pull webpage text and images into a new note page, then let AI organize it into a title, summary, key points, and notes.
        </p>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Webpage URL</label>
            <input
              type="url"
              placeholder="https://example.com/article"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Page title (optional)</label>
            <input
              type="text"
              placeholder="Leave empty to use webpage title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Topic folder</label>
            <select
              value={topicFolder}
              onChange={(e) => setTopicFolder(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">No folder</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>{folder.name}</option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100">
              Cancel
            </button>
            <button
              type="submit"
              disabled={importMutation.isPending}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {importMutation.isPending ? 'Importing...' : 'Import'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
