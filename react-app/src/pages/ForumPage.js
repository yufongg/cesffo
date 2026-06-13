import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import CategoryList from '../components/forum/CategoryList';
import PostList from '../components/forum/PostList';
import ThreadEditor from '../components/forum/ThreadEditor';
import ThreadList from '../components/forum/ThreadList';
import { formatDate } from '../utils/forumText';
import {
  WS_BASE,
  createForumThread,
  deleteForumThread,
  listCategories,
  listPosts,
  updateForumThread,
} from '../services/forumApi';

function normalizeId(value) {
  return value ? value.replaceAll('-', '') : value;
}

function ForumPage({ initialCategoryName }) {
  const [categories, setCategories] = useState([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [createdThread, setCreatedThread] = useState(null);
  const [posts, setPosts] = useState([]);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [viewMode, setViewMode] = useState('list');

  const selectedThreadIdRef = useRef(null);
  const selectedCategoryIdRef = useRef(null);
  const initialCategoryAppliedRef = useRef(false);
  const [threadPendingDelete, setThreadPendingDelete] = useState(null);

  const selectedCategory = useMemo(
    () => categories.find((category) => category.category_id === selectedCategoryId),
    [categories, selectedCategoryId]
  );

  const selectedThread = useMemo(() => {
    const threadFromCategory = selectedCategory?.threads?.find(
      (thread) => normalizeId(thread.thread_id) === normalizeId(selectedThreadId)
    );

    if (threadFromCategory) return threadFromCategory;

    if (
      createdThread &&
      normalizeId(createdThread.thread_id) === normalizeId(selectedThreadId)
    ) {
      return createdThread;
    }

    return null;
  }, [selectedCategory, selectedThreadId, createdThread]);

  const showError = useCallback((message) => {
    setErrorMessage(message);
    setTimeout(() => setErrorMessage(''), 5000);
  }, []);

  const showStatus = useCallback((message) => {
    setStatusMessage(message);
    setTimeout(() => setStatusMessage(''), 3500);
  }, []);

  const loadCategories = useCallback(async () => {
    const data = await listCategories();
    setCategories(data);

    const currentCategoryId = selectedCategoryIdRef.current;

    if (
      currentCategoryId &&
      data.some((category) => category.category_id === currentCategoryId)
    ) {
      setSelectedCategoryId(currentCategoryId);
      return;
    }

    if (data.length > 0) {
      setSelectedCategoryId(data[0].category_id);
      selectedCategoryIdRef.current = data[0].category_id;
    }
  }, []);

  const loadThreadPosts = useCallback(async (threadId) => {
    if (!threadId) {
      setPosts([]);
      return;
    }

    setPosts(await listPosts(threadId));
  }, []);

  useEffect(() => {
    selectedThreadIdRef.current = selectedThreadId;
  }, [selectedThreadId]);

  useEffect(() => {
    selectedCategoryIdRef.current = selectedCategoryId;
  }, [selectedCategoryId]);

  useEffect(() => {
    loadCategories().catch((error) => showError(error.message));
  }, [loadCategories, showError]);

  useEffect(() => {
    if (initialCategoryAppliedRef.current) return;
    if (!initialCategoryName || categories.length === 0) return;

    const matchedCategory = categories.find(
      (category) =>
        category.name.toLowerCase() === initialCategoryName.toLowerCase()
    );

    if (matchedCategory) {
      setSelectedCategoryId(matchedCategory.category_id);
      setSelectedThreadId(null);
      setCreatedThread(null);
      setViewMode('list');
      initialCategoryAppliedRef.current = true;
    }
  }, [initialCategoryName, categories]);

  useEffect(() => {
    if (viewMode !== 'detail') return;
    loadThreadPosts(selectedThreadId).catch((error) => showError(error.message));
  }, [loadThreadPosts, selectedThreadId, showError, viewMode]);

  useEffect(() => {
    let socket;
    let retryTimer;

    function connect() {
      console.log('Forum WS URL:', `${WS_BASE}/api/v1/forum/ws`);

      socket = new WebSocket(`${WS_BASE}/api/v1/forum/ws`);

      socket.onopen = () => {
        console.log('Forum WebSocket connected');
        socket.send('hello');
      };

      socket.onerror = (error) => {
        console.error('Forum WebSocket error:', error);
      };

      socket.onclose = () => {
        console.log('Forum WebSocket closed. Reconnecting...');
        retryTimer = setTimeout(connect, 3000);
      };

      socket.onmessage = async (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('Forum WebSocket message:', message);

          const currentThreadId = selectedThreadIdRef.current;
          const messageThreadId = normalizeId(message.thread_id);

          if (
            message.event === 'thread_deleted' &&
            currentThreadId &&
            messageThreadId === currentThreadId
          ) {
            await loadCategories();

            setSelectedThreadId(null);
            setCreatedThread(null);
            setPosts([]);
            setViewMode('list');
            return;
          }

          if (
            message.event === 'thread_created' ||
            message.event === 'thread_updated' ||
            message.event === 'thread_deleted' ||
            message.event === 'post_created' ||
            message.event === 'post_updated' ||
            message.event === 'post_deleted'
          ) {
            await loadCategories();
          }

          if (
            currentThreadId &&
            messageThreadId === currentThreadId &&
            message.event !== 'thread_deleted'
          ) {
            await loadThreadPosts(currentThreadId);
          }
        } catch (error) {
          console.error('Forum WebSocket message handling failed:', error);
        }
      };
    }

    connect();

    return () => {
      clearTimeout(retryTimer);
      if (socket) socket.close();
    };
  }, [loadCategories, loadThreadPosts]);

  function selectCategory(category) {
    initialCategoryAppliedRef.current = true;
    selectedCategoryIdRef.current = category.category_id;

    setSelectedCategoryId(category.category_id);
    setSelectedThreadId(null);
    setCreatedThread(null);
    setPosts([]);
    setViewMode('list');
  }

  function openThread(threadId) {
    setSelectedThreadId(normalizeId(threadId));
    setCreatedThread(null);
    setViewMode('detail');
  }

  function startThread() {
    setSelectedThreadId(null);
    setCreatedThread(null);
    setPosts([]);
    setViewMode('create');
  }

  function backToList() {
    setSelectedCategoryId(selectedCategoryIdRef.current);
    setSelectedThreadId(null);
    setCreatedThread(null);
    setPosts([]);
    setViewMode('list');
  }

  async function handleCreateThread(title, content, files) {
    if (!selectedCategoryId) {
      showError('Select a category first.');
      return false;
    }

    try {
      const thread = await createForumThread(
        selectedCategoryId,
        title,
        content,
        files
      );

      const newThreadId = normalizeId(thread.thread_id);

      setCreatedThread(thread);
      setSelectedThreadId(newThreadId);
      selectedThreadIdRef.current = newThreadId;

      await loadThreadPosts(newThreadId);
      await loadCategories();

      setViewMode('detail');
      showStatus('Thread created.');
      return true;
    } catch (error) {
      showError(error.message);
      return false;
    }
  }

  async function handleUpdateThread(threadId, title, content) {
    const previousCategoryId = selectedCategoryId;

    try {
      await updateForumThread(threadId, title, content);
      await loadCategories();

      setSelectedCategoryId(previousCategoryId);
      setSelectedThreadId(null);
      setCreatedThread(null);
      setPosts([]);
      setViewMode('list');

      showStatus('Thread updated.');
      return true;
    } catch (error) {
      showError(error.message);
      return false;
    }
  }

  function handleDeleteThread(threadId) {
    setThreadPendingDelete(threadId);
  }

  async function confirmDeleteThread() {
    if (!threadPendingDelete) return;

    const previousCategoryId = selectedCategoryId;

    try {
      await deleteForumThread(threadPendingDelete);
      await loadCategories();

      setSelectedCategoryId(previousCategoryId);
      setThreadPendingDelete(null);
      setSelectedThreadId(null);
      setCreatedThread(null);
      setPosts([]);
      setViewMode('list');

      showStatus('Thread deleted.');
    } catch (error) {
      setThreadPendingDelete(null);
      showError(error.message);
    }
  }

  return (
    <main className="forum-page">
      <CategoryList
        categories={categories}
        selectedCategoryId={selectedCategoryId}
        onSelectCategory={selectCategory}
      />

      {statusMessage && <div className="alert success">{statusMessage}</div>}
      {errorMessage && <div className="alert error">{errorMessage}</div>}

      {viewMode === 'list' && (
        <section className="forum-list-page">
          <ThreadList
            selectedCategory={selectedCategory}
            selectedThreadId={selectedThreadId}
            onSelectThread={openThread}
            onStartThread={startThread}
            variant="full"
          />
        </section>
      )}

      {viewMode === 'create' && (
        <section className="forum-detail-page">
          <button type="button" className="back-link" onClick={backToList}>
            Discussions List
          </button>

          <ThreadEditor
            selectedCategory={selectedCategory}
            onSubmit={handleCreateThread}
            onCancel={backToList}
          />
        </section>
      )}

      {viewMode === 'detail' && (
        <section className="forum-detail-page">
          <button type="button" className="back-thread-button" onClick={backToList}>
            Back
          </button>

          <section className="discussion-column detail-only">
            <div className="thread-detail-header">
              <div className="thread-header-info">
                <h2>{selectedThread?.title || posts[0]?.title || 'Select a thread'}</h2>

                {posts[0] && (
                  <div className="thread-header-meta">
                    <span>
                      {formatDate(
                        posts[0].is_edited
                          ? posts[0].updated_at
                          : posts[0].created_at
                      )}
                    </span>

                    {posts[0].is_edited && <span>Edited</span>}
                  </div>
                )}
              </div>
            </div>

            <PostList
              posts={posts}
              selectedThread={selectedThread}
              onUpdateThread={handleUpdateThread}
              onDeleteThread={handleDeleteThread}
              onRefreshThread={() => loadThreadPosts(selectedThreadId)}
            />
          </section>

          <button type="button" className="back-thread-button bottom" onClick={backToList}>
            Back
          </button>
        </section>
      )}

      {threadPendingDelete && (
        <div className="delete-confirm-overlay">
          <div className="delete-confirm-card">
            <h2>Delete thread?</h2>
            <p>Are you sure you want to delete this thread? This will remove the original post and attachments.</p>

            <div className="delete-confirm-actions">
              <button
                type="button"
                className="delete-confirm-cancel"
                onClick={() => setThreadPendingDelete(null)}
              >
                Cancel
              </button>

              <button
                type="button"
                className="delete-confirm-delete"
                onClick={confirmDeleteThread}
              >
                Delete Thread
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default ForumPage;