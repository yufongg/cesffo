import React from 'react';
import { formatDate } from '../../utils/forumText';
import SafeHtml from '../Security/SafeHtml';
import ReplyComposer from './ReplyComposer';

// Read view of a thread: the original post plus every reply. All content is
// sanitized server-side (nh3), then re-parsed through the same allow-list into
// React elements here (no raw HTML injected). Replies are open to any
// authenticated viewer; the backend re-checks ownership/lock state on every
// mutation.

function PostAttachments({ attachments, canManage, onDeleteAttachment }) {
  if (!attachments || attachments.length === 0) return null;
  return (
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
  );
}

export default function ThreadDetail({
  thread,
  posts,
  canManage,        // manage the THREAD (edit/delete the original) — author or admin
  canManagePost,    // (post) => bool — manage an individual reply
  onEdit,
  onDelete,
  onDeleteAttachment,
  onReply,
  onDeletePost,
}) {
  if (!thread) {
    return <p className="empty-state">Select a thread to read it.</p>;
  }

  const originalPost = posts[0];
  if (!originalPost) {
    return <p className="empty-state">This thread has no post yet.</p>;
  }

  const replies = posts.slice(1);
  const stamp = originalPost.is_edited ? originalPost.updated_at : originalPost.created_at;

  return (
    <>
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

          <SafeHtml className="forum-thread__content" html={originalPost.content} />

          <PostAttachments
            attachments={originalPost.attachments}
            canManage={canManage}
            onDeleteAttachment={onDeleteAttachment}
          />

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

      <section className="forum-replies" aria-label="Replies">
        <h2 className="forum-replies__heading">
          {replies.length} {replies.length === 1 ? 'reply' : 'replies'}
        </h2>

        {replies.map((reply) => {
          const replyStamp = reply.is_edited ? reply.updated_at : reply.created_at;
          const mine = canManagePost ? canManagePost(reply) : false;
          return (
            <article className="card forum-reply-item" key={reply.post_id}>
              <div className="card__body">
                <div className="forum-thread__meta">
                  <span>{formatDate(replyStamp)}</span>
                  {reply.is_edited && <span className="tag">Edited</span>}
                </div>

                <SafeHtml className="forum-thread__content" html={reply.content} />

                <PostAttachments
                  attachments={reply.attachments}
                  canManage={mine}
                  onDeleteAttachment={onDeleteAttachment}
                />

                {mine && (
                  <div className="forum-thread__actions">
                    <button
                      type="button"
                      className="btn btn--danger btn--sm"
                      onClick={() => onDeletePost(reply.post_id)}
                    >
                      Delete reply
                    </button>
                  </div>
                )}
              </div>
            </article>
          );
        })}
      </section>

      {thread.is_locked ? (
        <p className="empty-state">This thread is locked — new replies are disabled.</p>
      ) : (
        <ReplyComposer onSubmit={onReply} />
      )}
    </>
  );
}
