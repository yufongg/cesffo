import React from 'react';
import { formatDate } from '../../utils/forumText';

// Read view of a thread's original post. Content is server-sanitized (nh3) before
// storage, so rendering it as HTML is safe. Edit/Delete only render for the
// author or an admin — and the backend re-checks ownership on every mutation.
export default function ThreadDetail({
  thread,
  posts,
  canManage,
  onEdit,
  onDelete,
  onDeleteAttachment,
}) {
  const originalPost = posts[0];

  if (!thread) {
    return <p className="empty-state">Select a thread to read it.</p>;
  }
  if (!originalPost) {
    return <p className="empty-state">This thread has no post yet.</p>;
  }

  const attachments = originalPost.attachments || [];
  const stamp = originalPost.is_edited ? originalPost.updated_at : originalPost.created_at;

  return (
    <article className="card forum-thread">
      <div className="card__body">
        <div className="forum-thread__head">
          <h1>{thread.title}</h1>
          <div className="forum-thread__meta">
            <span>{formatDate(stamp)}</span>
            {originalPost.is_edited && <span className="tag">Edited</span>}
            {thread.is_locked && <span className="tag">Locked</span>}
          </div>
        </div>

        <div
          className="forum-thread__content"
          dangerouslySetInnerHTML={{ __html: originalPost.content }}
        />

        {attachments.length > 0 && (
          <div className="forum-attachments">
            {attachments.map((attachment) => (
              <figure className="forum-attachment" key={attachment.attachment_id}>
                <a href={attachment.file_url} target="_blank" rel="noreferrer">
                  <img src={attachment.file_url} alt={attachment.file_name} loading="lazy" />
                </a>
                {canManage && (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm forum-attachment__remove"
                    onClick={() => onDeleteAttachment(attachment.attachment_id)}
                  >
                    Remove
                  </button>
                )}
              </figure>
            ))}
          </div>
        )}

        {canManage && (
          <div className="forum-thread__actions">
            <button type="button" className="btn btn--secondary btn--sm" onClick={onEdit}>
              Edit thread
            </button>
            <button type="button" className="btn btn--danger btn--sm" onClick={onDelete}>
              Delete thread
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
