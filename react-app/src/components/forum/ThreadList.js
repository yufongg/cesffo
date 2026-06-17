import { useMemo, useState } from 'react';
import { formatDate } from '../../utils/forumText';

function ThreadList({
  selectedCategory,
  selectedThreadId,
  onSelectThread,
  onStartThread,
  variant = 'compact',
}) {
  const [sortMode, setSortMode] = useState('recent');

  const panelClassName =
    variant === 'full'
      ? 'thread-list-panel thread-list-panel-full'
      : 'thread-list-panel';

  const sortedThreads = useMemo(() => {
    const threads = [...(selectedCategory?.threads || [])];

    if (sortMode === 'oldest') {
      return threads.sort(
        (a, b) => new Date(a.created_at) - new Date(b.created_at)
      );
    }

    return threads.sort(
      (a, b) =>
        new Date(b.updated_at || b.created_at) -
        new Date(a.updated_at || a.created_at)
    );
  }, [selectedCategory, sortMode]);

  return (
    <section className={panelClassName}>
      <button
        type="button"
        className="primary start-thread-button"
        onClick={onStartThread}
      >
        Start a New Thread
      </button>

      <div className="thread-toolbar">
        <div>
          <span>Filter by:</span>
          <strong> All Threads</strong>
        </div>

        <label>
          <span>Sort by:</span>
          <select
            value={sortMode}
            onChange={(event) => setSortMode(event.target.value)}
          >
            <option value="recent">Most Recent Activity</option>
            <option value="oldest">Oldest First</option>
          </select>
        </label>
      </div>

      <div className="thread-list-heading">
        <h2>{selectedCategory?.name || 'Threads'}</h2>
        {selectedCategory?.description && <p>{selectedCategory.description}</p>}
      </div>

      {!sortedThreads.length && (
        <p className="muted empty-state">No threads available.</p>
      )}

      <div className="thread-list">
        {sortedThreads.map((thread) => (
          <button
            type="button"
            className={`thread-row ${
              selectedThreadId === thread.thread_id ? 'selected' : ''
            }`}
            key={thread.thread_id}
            onClick={() => onSelectThread(thread.thread_id)}
          >
            <div className="thread-row-main">
              <h3>{thread.title}</h3>
              <p>
                Created {formatDate(thread.created_at)}
              </p>
            </div>

            <div className="thread-row-stats">
              <span>
                <strong>{thread.post_count}</strong> Posts
              </span>
              <span>
                <strong>{thread.view_count}</strong> Views
              </span>
            </div>

            <div className="thread-row-last">
              <span>Last activity</span>
              <strong>{formatDate(thread.updated_at || thread.created_at)}</strong>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

export default ThreadList;