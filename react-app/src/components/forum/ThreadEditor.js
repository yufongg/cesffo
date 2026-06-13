import { useState } from 'react';
import PostEditor from './PostEditor';

function ThreadEditor({ selectedCategory, onSubmit, onCancel }) {
  const [title, setTitle] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  async function handleSubmit(content, files) {
    const plainContent = content.replace(/<[^>]*>/g, '').trim();

    if (!title.trim() && !plainContent) {
      setErrorMessage('Please enter a subject and post content before posting the thread.');
      return false;
    }

    if (!title.trim()) {
      setErrorMessage('Please enter a subject before posting the thread.');
      return false;
    }

    if (!plainContent) {
      setErrorMessage('Please enter post content before posting the thread.');
      return false;
    }

    setErrorMessage('');

    await onSubmit(title.trim(), content, files.slice(0, 5));
    setTitle('');

    return true;
  }

  return (
    <section className="thread-composer-card">
      <h3>Start a New Thread</h3>
      <p className="muted">
        Create a new discussion topic under{' '}
        {selectedCategory?.name || 'the selected category'}.
      </p>
      
      {errorMessage && (
        <div className="thread-warning">
          <span>⚠️</span>
          <span>{errorMessage}</span>
        </div>
      )}

      <label className="thread-title-field">
        <span>Subject *</span>
        <input
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Enter thread subject"
        />
      </label>

      <PostEditor
        onSubmit={handleSubmit}
        submitLabel="Post Thread"
        cancelLabel="Cancel"
        onCancel={onCancel}
        placeholder="Write the original post for this thread."
        attachmentHelpText="Upload image files for this thread. Maximum 5 images allowed."
        maxFiles={5}
      />
    </section>
  );
}

export default ThreadEditor;