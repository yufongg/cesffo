import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForumCategoryNav from '../components/forum/ForumCategoryNav';
import ThreadList from '../components/forum/ThreadList';
import ThreadDetail from '../components/forum/ThreadDetail';
import ThreadComposer from '../components/forum/ThreadComposer';
import ReportModal from "../components/forum/ReportModal";
import {
  listCategories,
  listPosts,
  createForumThread,
  updateForumThread,
  deleteForumThread,
  createForumPost,
  deleteForumPost,
  addPostAttachments,
  deletePostAttachment,
  forumWsUrl,
  likeThread,
  unlikeThread,
  listLikedThreads,
  getLastViewedThread,
  markLastViewedThread,
  reportThread,
  reportPost,
  listMyReports
} from '../services/forumApi';

const norm = (value) => (value ? value.replaceAll('-', '').toLowerCase() : '');

export default function Forum() {
  const [categories, setCategories] = useState([]);
  const [lastViewedThread, setLastViewedThread] = useState(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [posts, setPosts] = useState([]);
  const [viewMode, setViewMode] = useState('list'); // list | create | detail | edit
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [confirmDialog, setConfirmDialog] = useState(null);

  const selectedThreadIdRef = useRef(null);
  const currentUserId = norm(localStorage.getItem('user_id'));
  const isAdmin = localStorage.getItem('user_role') === 'admin';

  const [threadView, setThreadView] = useState("all");
  const [likedThreads, setLikedThreads] = useState([]);
  const [lastViewedThreads, setLastViewedThreads] = useState([]);
  const [reportTarget, setReportTarget] = useState(null);
  const [myReports, setMyReports] = useState([]);
  

  const selectedCategory = useMemo(
    () => categories.find((c) => c.category_id === selectedCategoryId) || null,
    [categories, selectedCategoryId],
  );

  const displayThreads = useMemo(() => {

      if (threadView === "liked") {
          return likedThreads.filter(
              thread => thread.category_id === selectedCategory?.category_id
          );
      }

      return selectedCategory?.threads || [];

  }, [
      threadView,
      likedThreads,
      selectedCategory,
  ]);

  const selectedThread = useMemo(() => {
    if (!selectedThreadId) return null;
    for (const category of categories) {
      const match = (category.threads || []).find((t) => norm(t.thread_id) === norm(selectedThreadId));
      if (match) return match;
    }
    return null;
  }, [categories, selectedThreadId]);

  const canManage = useMemo(() => {
    if (!selectedThread) return false;
    return isAdmin || norm(selectedThread.creator_id) === currentUserId;
  }, [selectedThread, isAdmin, currentUserId]);

  // Whether the current user may manage a given reply (its author, or an admin).
  const canManagePost = useCallback(
    (post) => isAdmin || (!!post && norm(post.creator_id) === currentUserId),
    [isAdmin, currentUserId],
  );

  const flashError = useCallback((message) => {
    setError(message);
    window.setTimeout(() => setError(''), 5000);
  }, []);

  const flashStatus = useCallback((message) => {
    setStatus(message);
    window.setTimeout(() => setStatus(''), 3000);
  }, []);

  const loadCategories = useCallback(async () => {
    const data = await listCategories();
    console.log(data);
    setCategories(data || []);
    setSelectedCategoryId((current) => {
      if (current && (data || []).some((c) => c.category_id === current)) return current;
      return data && data.length ? data[0].category_id : null;
    });
  }, []);

  const loadPosts = useCallback(async (threadId) => {
    if (!threadId) {
      setPosts([]);
      return;
    }
    setPosts(await listPosts(threadId));
  }, []);

  const [notificationToast, setNotificationToast] = useState('');

  const showNotificationToast = useCallback((message) => {
    setNotificationToast(message);
    window.setTimeout(() => setNotificationToast(''), 5000);
  }, []);

  useEffect(() => { selectedThreadIdRef.current = selectedThreadId; }, [selectedThreadId]);

  useEffect(() => {
    loadCategories().catch((e) => flashError(e.message));
  }, [loadCategories, flashError]);


  useEffect(() => {
  async function loadLastViewed() {
    try {
      const thread = await getLastViewedThread();
      setLastViewedThread(thread);
    } catch (e) {
      console.error(e);
    }
  }

  loadLastViewed();
}, []);

  // Live updates: reload the category tree on any forum event, and the open
  // thread's posts when it's the one that changed.
  useEffect(() => {
    if (!currentUserId) {
      return undefined;
    }

    let socket;
    let retry;

    function connect() {
      const url = forumWsUrl();
      console.log('Forum WS URL:', url);

      socket = new WebSocket(url);

      socket.onopen = () => {
        console.log('Forum WS connected');
      };

      socket.onerror = (event) => {
        console.log('Forum WS error:', event);
      };

      socket.onclose = (event) => {
        console.log('Forum WS closed:', event.code, event.reason);
        retry = window.setTimeout(connect, 3000);
      };

      socket.onmessage = async (event) => {
        console.log('Forum WS message:', event.data);

        try {
          const message = JSON.parse(event.data);
          const current = selectedThreadIdRef.current;

          if (message.event === 'thread_deleted' && current && norm(message.thread_id) === norm(current)) {
            setSelectedThreadId(null);
            setPosts([]);
            setViewMode('list');
          }

          await loadCategories();

          if (current && norm(message.thread_id) === norm(current) && message.event !== 'thread_deleted') {
            await loadPosts(current);
          }

          if (message.event === 'notification_created') {
            if (norm(message.recipient_id) === currentUserId) {
              showNotificationToast(message.notification?.message || 'You have a new notification.');
            }
          }
        } catch (error) {
          console.log('Forum WS parse error:', error);
        }
      };
    }

    connect();

    return () => {
      window.clearTimeout(retry);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [loadCategories, loadPosts, currentUserId, showNotificationToast]);

  function selectCategory(category) {
    setSelectedCategoryId(category.category_id);
    setSelectedThreadId(null);
    setPosts([]);
    setViewMode('list');
  }

async function openThread(threadId) {
  try {
    await markLastViewedThread({thread_id: threadId,});
    setLastViewedThread(threadId);
  } catch (e) {
    console.error(e);
  }

  const id = norm(threadId);

  setSelectedThreadId(id);
  setViewMode('detail');

  loadPosts(id).catch((e) => flashError(e.message));
}

async function handleLikeThread() {
  if (!selectedThread) return;

  try {
    let result;

    if (selectedThread.is_liked) {
      result = await unlikeThread(selectedThread.thread_id);
    } else {
      result = await likeThread(selectedThread.thread_id);
    }

    flashStatus(
      result.liked
        ? 'Thread liked.'
        : 'Thread unliked.'
    );

    await loadCategories();
  } catch (e) {
    flashError(e.message);
  }
}

async function submitReport(reason, description) {
    if (!reportTarget) return;

    try {
        if (reportTarget.type === "thread") {
            await reportThread(
                reportTarget.id,
                reason,
                description,
            );
        } else {
            await reportPost(
                reportTarget.id,
                reason,
                description,
            );
        }

        flashStatus("Report submitted.");
        setReportTarget(null);

    } catch (e) {
        flashError(e.message);
    }
}

async function handleThreadViewChange(view) {
  setThreadView(view);

  try {
    if (view === "liked") {
      const data = await listLikedThreads();
      setLikedThreads(data);
    }
  } catch (e) {
    flashError(e.message);
  }
}

  function backToList() {
    setSelectedThreadId(null);
    setPosts([]);
    setViewMode('list');
  }

  async function handleCreate({ title, content, files }) {
    if (!selectedCategoryId) {
      flashError('Pick a category first.');
      return false;
    }
    try {
      const thread = await createForumThread(selectedCategoryId, title, content, files);
      await loadCategories();
      openThread(thread.thread_id);
      flashStatus('Thread posted.');
      return true;
    } catch (e) {
      flashError(e.message);
      return false;
    }
  }

  async function handleUpdate({ title, content, files }) {
    if (!selectedThread) return false;
    try {
      await updateForumThread(selectedThread.thread_id, title, content);
      if (files.length > 0 && posts[0]) {
        await addPostAttachments(posts[0].post_id, files);
      }
      await loadCategories();
      await loadPosts(selectedThread.thread_id);
      setViewMode('detail');
      flashStatus('Thread updated.');
      return true;
    } catch (e) {
      flashError(e.message);
      return false;
    }
  }

  function openConfirmDialog({ title, message, onConfirm }) {
    setConfirmDialog({ title, message, onConfirm });
  }

  function closeConfirmDialog() {
    setConfirmDialog(null);
  }

  function handleDelete() {
    if (!selectedThread) return;

    openConfirmDialog({
      title: 'Delete Thread',
      message: 'Delete this thread? This removes the post and its images.',
      onConfirm: async () => {
        try {
          await deleteForumThread(selectedThread.thread_id);
          await loadCategories();
          backToList();
          flashStatus('Thread deleted.');
        } catch (e) {
          flashError(e.message);
        }
      },
    });
  }

  async function handleReply({ content, files }) {
    if (!selectedThread) return false;
    try {
      await createForumPost(selectedThread.thread_id, content, files);
      await loadPosts(selectedThread.thread_id);
      flashStatus('Reply posted.');
      return true;
    } catch (e) {
      flashError(e.message);
      return false;
    }
  }

  function handleDeletePost(postId) {
    openConfirmDialog({
      title: 'Delete Reply',
      message: 'Delete this reply?',
      onConfirm: async () => {
        try {
          await deleteForumPost(postId);
          if (selectedThread) await loadPosts(selectedThread.thread_id);
          flashStatus('Reply deleted.');
        } catch (e) {
          flashError(e.message);
        }
      },
    });
  }

  function handleDeleteAttachment(attachmentId) {
    openConfirmDialog({
      title: 'Remove Image',
      message: 'Remove this image?',
      onConfirm: async () => {
        try {
          await deletePostAttachment(attachmentId);
          if (selectedThreadId) await loadPosts(selectedThreadId);
        } catch (e) {
          flashError(e.message);
        }
      },
    });
  }

  console.log("Categories:", categories);
  console.log("Display threads:", displayThreads);
  console.log("Thread view:", threadView);

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Community</span>
          <h1>Discussion forum</h1>
          <p className="subtitle">Ask questions, share tips, and learn alongside other members.</p>
        </div>

        <ForumCategoryNav
          categories={categories}
          selectedCategoryId={selectedCategoryId}
          onSelect={selectCategory}
        />

        {status && <p role="status" className="alert alert--success">{status}</p>}
        {error && <p role="alert" className="alert alert--error">{error}</p>}

        {viewMode === 'list' && (
          <ThreadList
            title={selectedCategory?.name}
            description={selectedCategory?.description}
            threads={displayThreads}
            selectedThreadId={selectedThreadId}
            lastViewedThread={lastViewedThread}
            onOpenThread={openThread}
            onStartThread={() => setViewMode('create')}
            threadView={threadView}
            onThreadViewChange={handleThreadViewChange}
        />
        )}

        {viewMode === 'create' && (
          <>
            <button type="button" className="btn btn--ghost btn--sm" onClick={backToList}>
              ← Back to threads
            </button>
            <ThreadComposer
              mode="create"
              categoryName={selectedCategory?.name}
              onSubmit={handleCreate}
              onCancel={backToList}
            />
          </>
        )}

        {viewMode === 'edit' && selectedThread && (
          <>
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => setViewMode('detail')}>
              ← Back to thread
            </button>
            <ThreadComposer
              mode="edit"
              categoryName={selectedCategory?.name}
              initialTitle={selectedThread.title}
              initialContent={posts[0]?.content || ''}
              existingFileCount={posts[0]?.attachments?.length || 0}
              existingAttachments={posts[0]?.attachments || []}
              onDeleteAttachment={handleDeleteAttachment}
              onSubmit={handleUpdate}
              onCancel={() => setViewMode('detail')}
            />
          </>
        )}

        {viewMode === 'detail' && (
          <>
            <button type="button" className="btn btn--ghost btn--sm" onClick={backToList}>
              ← Back to threads
            </button>
            <ThreadDetail
              thread={selectedThread}
              posts={posts}
              canManage={canManage}
              canManagePost={canManagePost}
              onEdit={() => setViewMode('edit')}
              onDelete={handleDelete}
              onDeleteAttachment={handleDeleteAttachment}
              onReply={handleReply}
              onDeletePost={handleDeletePost}
              onLike={handleLikeThread}
              onReportThread={() =>
                  setReportTarget({
                      type: "thread",
                      id: selectedThread.thread_id,
                  })
              }
              onReportReply={(reply) =>
                  setReportTarget({
                      type: "post",
                      id: reply.post_id,
                  })
              }
          />
          </>
        )}
        {confirmDialog && (
          <div className="confirm-overlay">
            <div className="confirm-modal">
              <h3>{confirmDialog.title}</h3>
              <p>{confirmDialog.message}</p>

              <div className="confirm-actions">
                <button
                  type="button"
                  className="btn btn--danger"
                  onClick={async () => {
                    const action = confirmDialog.onConfirm;
                    closeConfirmDialog();
                    await action();
                  }}
                >
                  Delete
                </button>

                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={closeConfirmDialog}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <ReportModal
          open={!!reportTarget}
          type={reportTarget?.type}
          onClose={() => setReportTarget(null)}
          onSubmit={submitReport}
      />

      {notificationToast && (
        <div className="notification-toast">
          🔔 {notificationToast}
        </div>
      )}
    </div>
  );
}
