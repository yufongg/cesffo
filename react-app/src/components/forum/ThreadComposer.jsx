import React, { useState } from 'react';
import RichTextEditor from './RichTextEditor';
import { validateImageUpload, MAX_UPLOAD_BYTES } from '../Security/FileUpload';

const MAX_FILES = 5;
const MAX_TITLE_LEN = 255;
const MAX_CONTENT_LEN = 10000;

function plainText(html) {
  return html
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/g, ' ')
    .trim();
}

// Shared create/edit form for a thread's original post. Client-side validation
// mirrors the server (length caps + image allow-list via magic-byte sniffing in
// validateImageUpload); the server re-checks everything regardless.
export default function ThreadComposer({
  mode = 'create',
  categoryName,
  initialTitle = '',
  initialContent = '',
  submitLabel,
  onSubmit,
  onCancel,
}) {
  const [title, setTitle] = useState(initialTitle);
  const [content, setContent] = useState(initialContent);
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleFiles(event) {
    setError('');
    const chosen = Array.from(event.target.files || []).slice(0, MAX_FILES);
    const accepted = [];
    for (const file of chosen) {
      // eslint-disable-next-line no-await-in-loop
      const { valid, errors } = await validateImageUpload(file);
      if (!valid) {
        setError(`${file.name}: ${errors[0]}`);
        continue;
      }
      accepted.push(file);
    }
    setFiles(accepted);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    const trimmedTitle = title.trim();
    if (trimmedTitle.length < 3) {
      setError('Subject must be at least 3 characters.');
      return;
    }
    if (trimmedTitle.length > MAX_TITLE_LEN) {
      setError(`Subject must be at most ${MAX_TITLE_LEN} characters.`);
      return;
    }
    if (!plainText(content)) {
      setError('Post content cannot be empty.');
      return;
    }
    if (content.length > MAX_CONTENT_LEN) {
      setError(`Post is too long (max ${MAX_CONTENT_LEN} characters).`);
      return;
    }

    setBusy(true);
    try {
      const result = await onSubmit({ title: trimmedTitle, content, files });
      if (result !== false) {
        setFiles([]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card forum-composer" onSubmit={handleSubmit}>
      <div className="card__body">
        <h2>{mode === 'edit' ? 'Edit thread' : 'Start a new thread'}</h2>
        {categoryName && (
          <p className="subtitle">in {categoryName}</p>
        )}

        {error && <p role="alert" className="alert alert--error">{error}</p>}

        <label className="field">
          <span className="field__label">Subject</span>
          <input
            type="text"
            className="input"
            value={title}
            maxLength={MAX_TITLE_LEN}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What's your question or topic?"
          />
        </label>

        <div className="field">
          <span className="field__label">Post</span>
          <RichTextEditor
            initialContent={initialContent}
            onChange={setContent}
            placeholder="Share the details of your question or discussion…"
          />
        </div>

        <div className="field">
          <span className="field__label">
            Images <span className="field__hint">(optional, up to {MAX_FILES} · max {Math.floor(MAX_UPLOAD_BYTES / (1024 * 1024))} MB each)</span>
          </span>
          <input
            type="file"
            className="input"
            multiple
            accept="image/png,image/jpeg,image/gif,image/webp"
            onChange={handleFiles}
          />
          {files.length > 0 && (
            <p className="field__hint">{files.length} image{files.length === 1 ? '' : 's'} ready to upload</p>
          )}
        </div>

        <div className="forum-composer__actions">
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? 'Saving…' : (submitLabel || (mode === 'edit' ? 'Save changes' : 'Post thread'))}
          </button>
          <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        </div>
      </div>
    </form>
  );
}
