import React, { useState } from 'react';
import RichTextEditor from './RichTextEditor';
import { validateImageUpload, MAX_UPLOAD_BYTES } from '../Security/FileUpload';
import { plainText } from '../../utils/forumText';

const MAX_FILES = 5;
const MAX_CONTENT_LEN = 10000;

// Reply box shown to every authenticated viewer of a thread. Mirrors the
// server's content/image validation (the server re-checks regardless). On a
// successful post we bump `resetKey` to remount the editor + file input, which
// is the reliable way to clear a contentEditable.
export default function ReplyComposer({ onSubmit }) {
  const [content, setContent] = useState('');
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [resetKey, setResetKey] = useState(0);

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

    if (!plainText(content)) {
      setError('Reply cannot be empty.');
      return;
    }
    if (content.length > MAX_CONTENT_LEN) {
      setError(`Reply is too long (max ${MAX_CONTENT_LEN} characters).`);
      return;
    }

    setBusy(true);
    try {
      const result = await onSubmit({ content, files });
      if (result !== false) {
        setContent('');
        setFiles([]);
        setResetKey((k) => k + 1);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card forum-reply" onSubmit={handleSubmit}>
      <div className="card__body">
        <h3>Post a reply</h3>

        {error && <p role="alert" className="alert alert--error">{error}</p>}

        <div className="field">
          <RichTextEditor
            key={`editor-${resetKey}`}
            onChange={setContent}
            placeholder="Share your reply…"
          />
        </div>

        <div className="field">
          <span className="field__label">
            Images <span className="field__hint">(optional, up to {MAX_FILES} · max {Math.floor(MAX_UPLOAD_BYTES / (1024 * 1024))} MB each)</span>
          </span>
          <input
            key={`files-${resetKey}`}
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
            {busy ? 'Posting…' : 'Post reply'}
          </button>
        </div>
      </div>
    </form>
  );
}
