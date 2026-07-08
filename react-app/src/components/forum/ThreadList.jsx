import React, { useMemo, useState } from 'react';
import { formatDate } from '../../utils/forumText';

// Thread list for the selected category, styled with the app's card/row system.
export default function ThreadList({ category, onOpenThread, onStartThread }) {
  const [sortMode, setSortMode] = useState('recent');

  const threads = useMemo(() => {
    const list = [...(category?.threads || [])];
    if (sortMode === 'oldest') {
      return list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }
    return list.sort(
      (a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at),
    );
  }, [category, sortMode]);

  return (
    <section className="section">
      <div className="section__head">
        <div>
          <h2>{category?.name || 'Threads'}</h2>
          {category?.description && <p className="subtitle">{category.description}</p>}
        </div>
        <div className="forum-toolbar">
          <select
            className="select"
            value={sortMode}
            onChange={(e) => setSortMode(e.target.value)}
            aria-label="Sort threads"
          >
            <option value="recent">Most recent</option>
            <option value="oldest">Oldest first</option>
          </select>
          <button type="button" className="btn btn--primary btn--sm" onClick={onStartThread}>
            Start a thread
          </button>
        </div>
      </div>

      {threads.length === 0 ? (
        <div className="empty-state">
          <h3>No threads yet</h3>
          <p>Be the first to start a discussion in {category?.name || 'this category'}.</p>
          <button type="button" className="btn btn--primary" onClick={onStartThread}>
            Start a thread
          </button>
        </div>
      ) : (
        <div className="forum-thread-rows">
          {threads.map((thread) => (
            <button
              type="button"
              key={thread.thread_id}
              className="forum-thread-row"
              onClick={() => onOpenThread(thread.thread_id)}
            >
              <div className="forum-thread-row__main">
                <h3>{thread.title}</h3>
                <p>{thread.creator_name || 'Unknown user'} started {formatDate(thread.created_at)}</p>
              </div>
              <div className="forum-thread-row__stats">
                <span><strong>{thread.post_count}</strong> posts</span>
                <span><strong>{thread.view_count}</strong> views</span>
              </div>
              <div className="forum-thread-row__last">
                <span>Last activity</span>
                <strong>{formatDate(thread.updated_at || thread.created_at)}</strong>
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
