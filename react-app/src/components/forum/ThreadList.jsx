import React, { useMemo, useState } from 'react';
import { formatDate } from '../../utils/forumText';

// Thread list for the selected category, styled with the app's card/row system.
export default function ThreadList({ 
  title, 
  description, 
  threads, 
  selectedThreadId, 
  lastViewedThread, 
  onOpenThread, 
  onStartThread, 
  threadView, 
  onThreadViewChange, 
  reports 
}) {
  const [sortMode, setSortMode] = useState('recent');

  function handleViewChange(e) {
    onThreadViewChange(e.target.value);
  }

  const sortedThreads = useMemo(() => {
    const list = [...(threads || [])];
    if (sortMode === 'oldest') {
      return list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }
    return list.sort(
      (a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at),
    );
  }, [threads, sortMode]);

  const sortedReports = useMemo(() => {
    const list = [...(reports || [])];
    if (sortMode === "oldest") {
      return list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }
    return list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }, [reports, sortMode]);

  return (
    <section className="section">
      <div className="section__head">
        <div>
          <h2>{title || 'Threads'}</h2>
          {description && <p className="subtitle">{description}</p>}
        </div>
        <div className="forum-toolbar">
          <select
            className="select"
            value={threadView}
            onChange={handleViewChange}
          >
            <option value="all">All Threads</option>
            <option value="liked">Liked Threads</option>
            <option value="mine">My Threads</option>
            <option value="reports">My Reports</option>
          </select>
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

      {threadView === "reports" ? (
        sortedReports.length === 0 ? (
          <div className="empty-state">
            <h3>No reports submitted</h3>
            <p>Reports you submit will appear here.</p>
          </div>
        ) : (
          <div className="report-list">
            {sortedReports.map((report) => (
              <div key={report.report_id} className="report-card">
                <div className="report-card__left">
                  <h3>{report.title}</h3>
                  <div className="report-section">
                    <span className="report-label">Reported Content</span>
                    <p className="report-preview">{report.reported_content}</p>
                  </div>
                </div>
                <div className="report-card__middle">
                  <div className="report-section">
                    <span className="report-label">Reason</span>
                    <p>{report.reason}</p>
                  </div>
                  {report.description && (
                    <div className="report-section">
                      <span className="report-label">Your Description</span>
                      <p>{report.description}</p>
                    </div>
                  )}
                </div>
                <div className="report-card__right">
                  <span className={`report-status ${report.status.toLowerCase()}`}>
                    {report.status}
                  </span>
                  <small>{new Date(report.created_at).toLocaleString()}</small>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        sortedThreads.length === 0 ? (
          <div className="empty-state">
            <h3>No threads yet</h3>
            <p>Be the first to start a discussion in {title || "this section"}.</p>
            <button type="button" className="btn btn--primary" onClick={onStartThread}>
              Start a thread
            </button>
          </div>
        ) : (
          <div className="forum-thread-rows">
            {sortedThreads.map((thread) => (
              <button
                type="button"
                key={thread.thread_id}
                className={`forum-thread-row ${selectedThreadId === thread.thread_id ? "selected" : ""}`}
                onClick={() => onOpenThread(thread.thread_id)}
              >
                <div className="forum-thread-row__main">
                  <div className="forum-thread-title">
                    <h3>{thread.title}</h3>
                    {lastViewedThread?.thread_id === thread.thread_id && (
                      <span className="last-viewed-badge">📖 Last Viewed</span>
                    )}
                  </div>
                  <p>
                    {thread.creator_name || "Unknown user"} started {formatDate(thread.created_at)}
                  </p>
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
        )
      )}
    </section>
  );
}