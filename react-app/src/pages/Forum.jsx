import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForumCategoryNav from '../components/forum/ForumCategoryNav';
import ThreadList from '../components/forum/ThreadList';
import ThreadDetail from '../components/forum/ThreadDetail';
import ThreadComposer from '../components/forum/ThreadComposer';
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
} from '../services/forumApi';

const norm = (value) => (value ? value.replaceAll('-', '').toLowerCase() : '');

export default function Forum() {
  const [categories, setCategories] = useState([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [posts, setPosts] = useState([]);
  const [viewMode, setViewMode] = useState('list'); // list | create | detail | edit
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const selectedThreadIdRef = useRef(null);
  const currentUserId = norm(localStorage.getItem('user_id'));
  const isAdmin = localStorage.getItem('user_role') === 'admin';

  const selectedCategory = useMemo(
    () => categories.find((c) => c.category_id === selectedCategoryId) || null,
    [categories, selectedCategoryId],
  );

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

  useEffect(() => { selectedThreadIdRef.current = selectedThreadId; }, [selectedThreadId]);

  useEffect(() => {
    loadCategories().catch((e) => flashError(e.message));
  }, [loadCategories, flashError]);

  // Live updates: reload the category tree on any forum event, and the open
  // thread's posts when it's the one that changed.
  useEffect(() => {
    let socket;
    let retry;

    function connect() {
      socket = new WebSocket(forumWsUrl());
      socket.onmessage = async (event) => {
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
        } catch {
          /* ignore malformed frames */
        }
      };
      socket.onclose = () => { retry = window.setTimeout(connect, 3000); };
    }

    connect();
    return () => {
      window.clearTimeout(retry);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [loadCategories, loadPosts]);

  function selectCategory(category) {
    setSelectedCategoryId(category.category_id);
    setSelectedThreadId(null);
    setPosts([]);
    setViewMode('list');
  }

  function openThread(threadId) {
    const id = norm(threadId);
    setSelectedThreadId(id);
    setViewMode('detail');
    loadPosts(id).catch((e) => flashError(e.message));
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

  async function handleDelete() {
    if (!selectedThread) return;
    if (!window.confirm('Delete this thread? This removes the post and its images.')) return;
    try {
      await deleteForumThread(selectedThread.thread_id);
      await loadCategories();
      backToList();
      flashStatus('Thread deleted.');
    } catch (e) {
      flashError(e.message);
    }
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

  async function handleDeletePost(postId) {
    if (!window.confirm('Delete this reply?')) return;
    try {
      await deleteForumPost(postId);
      if (selectedThread) await loadPosts(selectedThread.thread_id);
      flashStatus('Reply deleted.');
    } catch (e) {
      flashError(e.message);
    }
  }

  async function handleDeleteAttachment(attachmentId) {
    if (!window.confirm('Remove this image?')) return;
    try {
      await deletePostAttachment(attachmentId);
      if (selectedThreadId) await loadPosts(selectedThreadId);
    } catch (e) {
      flashError(e.message);
    }
  }

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
            category={selectedCategory}
            onOpenThread={openThread}
            onStartThread={() => setViewMode('create')}
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
            />
          </>
        )}
      </div>
    </div>
  );
}
