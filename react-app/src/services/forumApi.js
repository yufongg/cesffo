export const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';
export const WS_BASE = API_BASE.replace(/^http/, 'ws');

async function getErrorMessage(response, fallbackMessage = 'Request failed') {
  const error = await response.json().catch(() => ({}));

  if (typeof error.detail === 'string') {
    return error.detail;
  }

  if (Array.isArray(error.detail)) {
    return error.detail
      .map((item) => item.msg || item.message || JSON.stringify(item))
      .join(', ');
  }

  return fallbackMessage;
}

export async function requestJson(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  if (response.status === 204) return null;
  return response.json();
}

export function listCategories() {
  return requestJson(`${API_BASE}/api/v1/forum/categories`);
}

export function listPosts(threadId) {
  return requestJson(`${API_BASE}/api/v1/forum/threads/${threadId}/posts`);
}

export function createForumThread(categoryId, title, content, files) {
  const formData = new FormData();
  formData.append('title', title);
  formData.append('content', content);
  files.forEach((file) => formData.append('files', file));

  return requestJson(`${API_BASE}/api/v1/forum/categories/${categoryId}/threads`, {
    method: 'POST',
    body: formData,
  });
}

export function updateForumThread(threadId, title, content) {
  return requestJson(`${API_BASE}/api/v1/forum/threads/${threadId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content }),
  });
}

export async function deleteForumThread(threadId) {
  const response = await fetch(`${API_BASE}/api/v1/forum/threads/${threadId}`, {
    method: 'DELETE',
  });

  if (!response.ok && response.status !== 204) {
    throw new Error(await getErrorMessage(response, 'Failed to delete thread'));
  }
}

export function listNotifications() {
  return requestJson(`${API_BASE}/api/v1/forum/notifications`);
}

// Kept for teammate/backward compatibility. Your UI no longer creates normal posts.
export function createForumPost(threadId, content, files) {
  const formData = new FormData();
  formData.append('content', content);
  files.forEach((file) => formData.append('files', file));

  return requestJson(`${API_BASE}/api/v1/forum/threads/${threadId}/posts`, {
    method: 'POST',
    body: formData,
  });
}

export function updateForumPost(postId, content) {
  return requestJson(`${API_BASE}/api/v1/forum/posts/${postId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
}

export async function deleteForumPost(postId) {
  const response = await fetch(`${API_BASE}/api/v1/forum/posts/${postId}`, {
    method: 'DELETE',
  });

  if (!response.ok && response.status !== 204) {
    throw new Error(await getErrorMessage(response, 'Failed to delete post'));
  }
}

export function markNotificationRead(notificationId) {
  return requestJson(`${API_BASE}/api/v1/forum/notifications/${notificationId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_read: true }),
  });
}

export function addPostAttachments(postId, files) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  return requestJson(`${API_BASE}/api/v1/forum/posts/${postId}/attachments`, {
    method: 'POST',
    body: formData,
  });
}

export async function deletePostAttachment(attachmentId) {
  const response = await fetch(`${API_BASE}/api/v1/forum/attachments/${attachmentId}`, {
    method: 'DELETE',
  });

  if (!response.ok && response.status !== 204) {
    throw new Error(await getErrorMessage(response, 'Failed to delete attachment'));
  }
}
