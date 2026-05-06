import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createShare, revokeShare, getSharedUsers, addSharedUser, removeSharedUser } from '../api/pages'

export default function ShareModal({ page, notebookId, onClose }) {
  const queryClient = useQueryClient()
  const [copied, setCopied] = useState(false)
  const [username, setUsername] = useState('')
  const [addError, setAddError] = useState('')

  const shareUrl = page.share_token
    ? `${window.location.origin}/shared/${page.share_token}`
    : null

  const shareMutation = useMutation({
    mutationFn: () => createShare(page.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notebook', notebookId] })
      queryClient.invalidateQueries({ queryKey: ['page', page.id] })
    },
  })

  const revokeMutation = useMutation({
    mutationFn: () => revokeShare(page.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notebook', notebookId] })
      queryClient.invalidateQueries({ queryKey: ['page', page.id] })
    },
  })

  const { data: sharedUsers = [] } = useQuery({
    queryKey: ['page-shared-users', page.id],
    queryFn: () => getSharedUsers(page.id).then((r) => r.data),
  })

  const addUserMutation = useMutation({
    mutationFn: (username) => addSharedUser(page.id, username),
    onSuccess: () => {
      setUsername('')
      setAddError('')
      queryClient.invalidateQueries({ queryKey: ['page-shared-users', page.id] })
      queryClient.invalidateQueries({ queryKey: ['page', page.id] })
    },
    onError: (err) => {
      setAddError(err.response?.data?.detail || 'Failed to add user')
    },
  })

  const removeUserMutation = useMutation({
    mutationFn: (userId) => removeSharedUser(page.id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['page-shared-users', page.id] })
      queryClient.invalidateQueries({ queryKey: ['page', page.id] })
    },
  })

  const copyLink = () => {
    navigator.clipboard.writeText(shareUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleAddUser = (e) => {
    e.preventDefault()
    setAddError('')
    if (!username.trim()) return
    addUserMutation.mutate(username.trim())
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Share page</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        {/* Public Link Section */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Public link</h3>
          <p className="text-sm text-gray-500 mb-3">
            Anyone with the link can view this page without signing in.
          </p>

          {shareUrl ? (
            <>
              <div className="flex gap-2 mb-3">
                <input
                  readOnly
                  value={shareUrl}
                  className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-700"
                />
                <button
                  onClick={copyLink}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg px-3 py-2 text-sm font-medium transition-colors whitespace-nowrap"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <button
                onClick={() => revokeMutation.mutate()}
                disabled={revokeMutation.isPending}
                className="text-sm text-red-500 hover:text-red-700 disabled:opacity-50"
              >
                {revokeMutation.isPending ? 'Revoking...' : 'Revoke link'}
              </button>
            </>
          ) : (
            <button
              onClick={() => shareMutation.mutate()}
              disabled={shareMutation.isPending}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
            >
              {shareMutation.isPending ? 'Generating...' : 'Generate share link'}
            </button>
          )}
        </div>

        <hr className="border-gray-200 mb-6" />

        {/* Specific Users Section */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Share with specific users</h3>
          <p className="text-sm text-gray-500 mb-3">
            Invite registered users to view this page.
          </p>

          <form onSubmit={handleAddUser} className="flex gap-2 mb-4">
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="submit"
              disabled={addUserMutation.isPending || !username.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            >
              {addUserMutation.isPending ? 'Adding...' : 'Add'}
            </button>
          </form>

          {addError && (
            <p className="text-sm text-red-500 mb-3">{addError}</p>
          )}

          {sharedUsers.length > 0 ? (
            <ul className="space-y-2">
              {sharedUsers.map((share) => (
                <li
                  key={share.id}
                  className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">
                      {share.user.username}
                    </span>
                    <span className="text-xs text-gray-400">{share.user.email}</span>
                  </div>
                  <button
                    onClick={() => removeUserMutation.mutate(share.user.id)}
                    disabled={removeUserMutation.isPending}
                    className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400 italic">No users invited yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}
