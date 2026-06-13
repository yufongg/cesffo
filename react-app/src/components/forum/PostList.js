import { useState } from 'react';
import {
  API_BASE,
  addPostAttachments,
  deletePostAttachment,
} from '../../services/forumApi';
import PostEditor from './PostEditor';

function isContentEmpty(content) {
  const plainText = content
    .replace(/<br\s*\/?>/gi, '')
    .replace(/<p><\/p>/gi, '')
    .replace(/<p><br><\/p>/gi, '')
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/g, '')
    .trim();

  return plainText.length === 0;
}

function PostList({
  posts,
  selectedThread,
  onUpdateThread,
  onDeleteThread,
  onRefreshThread,
}) {
  const [isEditingThread, setIsEditingThread] = useState(false);
  const [editingTitle, setEditingTitle] = useState('');
  const [editingContent, setEditingContent] = useState('');
  const [editErrorMessage, setEditErrorMessage] = useState('');
  const [deletedAttachmentIds, setDeletedAttachmentIds] = useState([]);

  const originalPost = posts[0];

  function startEdit() {
    setIsEditingThread(true);
    setEditingTitle(selectedThread?.title || '');
    setEditingContent(originalPost?.content || '');
    setEditErrorMessage('');
    setDeletedAttachmentIds([]);
  }

  function cancelEdit() {
    setIsEditingThread(false);
    setEditingTitle('');
    setEditingContent('');
    setEditErrorMessage('');
    setDeletedAttachmentIds([]);
  }

  async function saveThreadEdit(content, files) {
    if (!selectedThread || !originalPost) return false;

    if (!editingTitle.trim() && isContentEmpty(content)) {
      setEditErrorMessage(
        'Please enter a subject and post content before saving the thread.'
      );
      return false;
    }

    if (!editingTitle.trim()) {
      setEditErrorMessage('Thread subject cannot be empty.');
      return false;
    }

    if (isContentEmpty(content)) {
      setEditErrorMessage('Thread post content cannot be empty.');
      return false;
    }

    setEditErrorMessage('');

    await onUpdateThread(
      selectedThread.thread_id,
      editingTitle.trim(),
      content
    );

    if (files.length > 0) {
      await addPostAttachments(originalPost.post_id, files.slice(0, 5));
    }

    if (onRefreshThread) {
      await onRefreshThread();
    }

    cancelEdit();

    return true;
  }

  async function removeAttachment(attachmentId) {
    if (!window.confirm('Delete this image?')) return;

    await deletePostAttachment(attachmentId);

    setDeletedAttachmentIds((currentIds) => [
      ...currentIds,
      attachmentId,
    ]);

    if (onRefreshThread) {
      await onRefreshThread();
    }
  }

  if (!selectedThread) {
    return (
      <p className="muted empty-state">
        Select a thread to view its original post.
      </p>
    );
  }

  if (!originalPost) {
    return (
      <p className="muted empty-state">
        This thread does not have an original post yet.
      </p>
    );
  }

  const visibleAttachments =
    originalPost.attachments?.filter(
      (attachment) =>
        !deletedAttachmentIds.includes(attachment.attachment_id)
    ) || [];

  return (
    <div className="post-list">
      <article className="original-thread-post">
        {isEditingThread ? (
          <div className="edit-box">
            {editErrorMessage && (
              <div className="thread-warning">
                <span>⚠️</span>
                <span>{editErrorMessage}</span>
              </div>
            )}

            <label className="thread-title-field">
              <span>Subject *</span>
              <input
                type="text"
                value={editingTitle}
                onChange={(event) => setEditingTitle(event.target.value)}
              />
            </label>

            {visibleAttachments.length > 0 && (
              <div className="attachments edit-attachments">
                {visibleAttachments.map((attachment) => (
                  <div
                    className="attachment-edit-item"
                    key={attachment.attachment_id}
                  >
                    <img
                      src={`${API_BASE}${attachment.file_url}`}
                      alt={attachment.file_name}
                    />
                    <button
                      type="button"
                      className="danger"
                      onClick={() =>
                        removeAttachment(attachment.attachment_id)
                      }
                    >
                      Delete image
                    </button>
                  </div>
                ))}
              </div>
            )}

            <PostEditor
              onSubmit={saveThreadEdit}
              submitLabel="Save Thread"
              cancelLabel="Cancel"
              onCancel={cancelEdit}
              placeholder="Edit the original post for this thread."
              attachmentHelpText="Attach new image(s). Maximum 5 images allowed."
              maxFiles={5}
              initialContent={editingContent}
            />
          </div>
        ) : (
          <>
            <div
              className="post-content"
              dangerouslySetInnerHTML={{ __html: originalPost.content }}
            />

            {visibleAttachments.length > 0 && (
              <div className="attachments thread-attachments">
                {visibleAttachments.map((attachment) => (
                  <a
                    href={`${API_BASE}${attachment.file_url}`}
                    target="_blank"
                    rel="noreferrer"
                    key={attachment.attachment_id}
                  >
                    <img
                      src={`${API_BASE}${attachment.file_url}`}
                      alt={attachment.file_name}
                    />
                  </a>
                ))}
              </div>
            )}

            <div className="button-row">
              <button type="button" onClick={startEdit}>
                Edit Thread
              </button>
              <button
                type="button"
                className="danger"
                onClick={() => onDeleteThread(selectedThread.thread_id)}
              >
                Delete Thread
              </button>
            </div>

            <hr className="reply-divider" />
          </>
        )}
      </article>

      <section className="reply-area-placeholder">
        <p className="muted">Replies will appear here.</p>
      </section>
    </div>
  );
}

export default PostList;