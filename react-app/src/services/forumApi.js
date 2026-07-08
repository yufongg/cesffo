// Discussion-forum API calls. All requests go through the shared apiFetch, so
// they automatically carry the Bearer token and use the same relative paths /
// error handling as the rest of the app. Image uploads are sent as FormData.
import { apiFetch, wsUrl } from '../api/client';

export const FORUM_WS_PATH = '/api/v1/forum/ws';

export function forumWsUrl() {
  return wsUrl(FORUM_WS_PATH);
}

/* -------------------------------------------------------------------------- */
/* Categories & Threads                                                       */
/* -------------------------------------------------------------------------- */

export function listCategories() {
  return apiFetch('/api/v1/forum/categories');
}

export function listPosts(threadId) {
  return apiFetch(`/api/v1/forum/threads/${threadId}/posts`);
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
    body: {
      title,
      content,
    },
  });
}

export function deleteForumThread(threadId) {
  return apiFetch(`/api/v1/forum/threads/${threadId}`, {
    method: 'DELETE',
  });
}

/* -------------------------------------------------------------------------- */
/* Posts & Replies                                                            */
/* -------------------------------------------------------------------------- */

// Reply to a thread (supports image attachments)
export function createForumPost(threadId, content, files = []) {
  const formData = new FormData();
  formData.append('content', content);
  files.forEach((file) => formData.append('files', file));

  return apiFetch(`/api/v1/forum/threads/${threadId}/posts`, {
    method: 'POST',
    body: formData,
  });
}

// Create a nested reply (parent_id)
export function createPost(threadId, content, parentId = null) {
  return apiFetch(`/api/v1/forum/threads/${threadId}/posts`, {
    method: 'POST',
    body: {
      content,
      parent_id: parentId,
    },
  });
}

export function updateForumPost(postId, content) {
  return apiFetch(`/api/v1/forum/posts/${postId}`, {
    method: 'PUT',
    body: {
      content,
    },
  });
}

export function deleteForumPost(postId) {
  return apiFetch(`/api/v1/forum/posts/${postId}`, {
    method: 'DELETE',
  });
}

/* -------------------------------------------------------------------------- */
/* Attachments                                                                */
/* -------------------------------------------------------------------------- */

export function addPostAttachments(postId, files = []) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  return apiFetch(`/api/v1/forum/posts/${postId}/attachments`, {
    method: 'POST',
    body: formData,
  });
}

export function deletePostAttachment(attachmentId) {
  return apiFetch(`/api/v1/forum/attachments/${attachmentId}`, {
    method: 'DELETE',
  });
}

/* -------------------------------------------------------------------------- */
/* Notifications                                                              */
/* -------------------------------------------------------------------------- */

export function listNotifications() {
  return apiFetch('/api/v1/forum/notifications');
}

export function markNotificationRead(notificationId) {
  return apiFetch(`/api/v1/forum/notifications/${notificationId}`, {
    method: 'PATCH',
    body: {
      is_read: true,
    },
  });
}

/* -------------------------------------------------------------------------- */
/* Likes                                                                      */
/* -------------------------------------------------------------------------- */

export function likeThread(threadId) {
  return apiFetch(`/api/v1/forum/threads/${threadId}/like`, {
    method: 'POST',
  });
}

export function unlikeThread(threadId) {
  return apiFetch(`/api/v1/forum/threads/${threadId}/like`, {
    method: 'DELETE',
  });
}

export function listLikedThreads() {
    return apiFetch("/api/v1/forum/users/liked-threads");
}

/* -------------------------------------------------------------------------- */
/* Last Viewed Thread                                                         */
/* -------------------------------------------------------------------------- */

export function getLastViewedThread() {
  return apiFetch('/api/v1/forum/users/last-viewed');
}

export function markLastViewedThread(threadId) {
  return apiFetch(`/api/v1/forum/threads/${threadId}/view`, {
    method: 'POST',
  });
}

/* -------------------------------------------------------------------------- */
/* Reporting Threads                                                          */
/* -------------------------------------------------------------------------- */


export function reportThread(threadId, reason, description = "") {
  return apiFetch(`/api/v1/forum/threads/${threadId}/report`, {
    method: "POST",
    body: {
      reason,
      description,
    },
  });
}

export function reportPost(postId, reason, description = "") {
  return apiFetch(`/api/v1/forum/posts/${postId}/report`, {
    method: "POST",
    body: {
      reason,
      description,
    },
  });
}

export function listMyReports() {
  return apiFetch("/api/v1/forum/users/reports");
}

/* -------------------------------------------------------------------------- */
/* My Threads                                                                 */
/* -------------------------------------------------------------------------- */


export function listMyThreads() {
    return apiFetch("/api/v1/forum/users/my-threads");
}

/* -------------------------------------------------------------------------- */
/* Admin Report Handling                                                      */
/* -------------------------------------------------------------------------- */

export function listAdminReports(status = "Pending") {
    return apiFetch(`/api/v1/admin/reports?status=${status}`);
}

export function resolveReport(reportId) {
    return apiFetch(`/api/v1/admin/reports/${reportId}`, {
        method: "PATCH",
        body: {status: "Resolved",},
    });
}

export function removeReportedContent(reportId) {
    return apiFetch(`/api/v1/admin/reports/${reportId}/remove`, {
        method: "DELETE",
    });
}