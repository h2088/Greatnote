import client from './client'

export const getTopicFolders = (notebookId) => client.get('/topic-folders/', { params: { notebook: notebookId } })
export const createTopicFolder = (data) => client.post('/topic-folders/', data)
export const updateTopicFolder = (id, data) => client.patch(`/topic-folders/${id}/`, data)
export const deleteTopicFolder = (id) => client.delete(`/topic-folders/${id}/`)
