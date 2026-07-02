// Discussion-forum API calls. All requests go through the shared apiFetch, so
// they automatically carry the Bearer token and use the same relative paths /
// error handling as the rest of the app. Image uploads are sent as FormData.
import { apiFetch, wsUrl } from '../api/client';

export const FORUM_WS_PATH = '/api/v1/forum/ws';

export function forumWsUrl() {
  return wsUrl(FORUM_WS_PATH);
}

export function listCategories() {
  return apiFetch('/api/v1/forum/categories');
}

export function listPosts(threadId) {
  return apiFetch(`/api/v1/forum/threads/${threadId}/posts`);
}

// Reply to a thread. Open to any authenticated user (the backend only blocks
// locked threads). Sent as FormData so optional images ride along.
export function createForumPost(threadId, content, files = []) {
  const formData = new FormData();
  formData.append('content', content);
  files.forEach((file) => formData.append('files', file));

  return apiFetch(`/api/v1/forum/threads/${threadId}/posts`, {
    method: 'POST',
    body: formData,
  });
}

export function deleteForumPost(postId) {
  return apiFetch(`/api/v1/forum/posts/${postId}`, { method: 'DELETE' });
}

export function createForumThread(categoryId, title, content, files = []) {
  const formData = new FormData();
  formData.append('title', title);
  formData.append('content', content);
  files.forEach((file) => formData.append('files', file));

  return apiFetch(`/api/v1/forum/categories/${categoryId}/threads`, {
    method: 'POST',
    body: formData,
  });
}

export function updateForumThread(threadId, title, content) {
  return apiFetch(`/api/v1/forum/threads/${threadId}`, {
    method: 'PUT',
    body: { title, content },
  });
}

export function deleteForumThread(threadId) {
  return apiFetch(`/api/v1/forum/threads/${threadId}`, { method: 'DELETE' });
}

export function addPostAttachments(postId, files = []) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  return apiFetch(`/api/v1/forum/posts/${postId}/attachments`, {
    method: 'POST',
    body: formData,
  });
}

export function deletePostAttachment(attachmentId) {
  return apiFetch(`/api/v1/forum/attachments/${attachmentId}`, { method: 'DELETE' });
}
