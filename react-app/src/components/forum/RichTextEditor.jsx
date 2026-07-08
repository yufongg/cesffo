import React, { useEffect, useRef, useState } from 'react';
import { sanitizeHtml } from '../Security/SafeHtml';

// This one mimics the SIT discussion board text area
export default function RichTextEditor({ initialContent = '', onChange, placeholder = 'Write your post…' }) {
  const editorRef = useRef(null);
  const [active, setActive] = useState({ bold: false, italic: false, underline: false, bullet: false });
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [linkError, setLinkError] = useState('');

  useEffect(() => {
    const el = editorRef.current;
    const safe = sanitizeHtml(initialContent);
    if (el && el.innerHTML !== safe) {
      el.innerHTML = safe;
    }
  }, [initialContent]);

  const emit = () => onChange?.(editorRef.current?.innerHTML || '');

  const refreshActive = () => {
    setActive({
      bold: document.queryCommandState('bold'),
      italic: document.queryCommandState('italic'),
      underline: document.queryCommandState('underline'),
      bullet: document.queryCommandState('insertUnorderedList'),
    });
  };

  const exec = (command, value = null) => {
    editorRef.current?.focus();
    document.execCommand(command, false, value);
    refreshActive();
    emit();
  };

  const openLinkModal = () => {
    setLinkUrl('');
    setLinkError('');
    setShowLinkModal(true);
  };

  const closeLinkModal = () => {
    setShowLinkModal(false);
    setLinkUrl('');
    setLinkError('');
  };

  const insertLink = () => {
    const trimmedUrl = linkUrl.trim();

    if (!trimmedUrl) {
      setLinkError('Please enter a URL.');
      return;
    }

    if (!/^https?:\/\//i.test(trimmedUrl)) {
      setLinkError('Links must start with http:// or https://');
      return;
    }

    exec('createLink', trimmedUrl);
    closeLinkModal();
  };

  const Btn = ({ label, title, on, command, onClick }) => (
    <button
      type="button"
      className={`forum-editor__btn ${on ? 'forum-editor__btn--active' : ''}`}
      title={title}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick || (() => exec(command))}
    >
      {label}
    </button>
  );

  return (
    <div className="forum-editor">
      <div className="forum-editor__toolbar" role="toolbar" aria-label="Text formatting">
        <Btn label={<strong>B</strong>} title="Bold" on={active.bold} command="bold" />
        <Btn label={<em>I</em>} title="Italic" on={active.italic} command="italic" />
        <Btn label={<u>U</u>} title="Underline" on={active.underline} command="underline" />
        <Btn label="• List" title="Bullet list" on={active.bullet} command="insertUnorderedList" />
        <Btn label="Heading" title="Heading" onClick={() => exec('formatBlock', 'h3')} />
        <Btn label="🔗 Link" title="Insert link" onClick={openLinkModal} />
      </div>

      <div
        ref={editorRef}
        className="forum-editor__area"
        contentEditable
        suppressContentEditableWarning
        data-placeholder={placeholder}
        onInput={() => { emit(); refreshActive(); }}
        onKeyUp={refreshActive}
        onMouseUp={refreshActive}
      />

      {showLinkModal && (
        <div className="confirm-overlay">
          <div className="confirm-modal">
            <h3>Insert Link</h3>
            <p>Enter a URL starting with http:// or https://.</p>

            {linkError && (
              <p role="alert" className="alert alert--error">
                {linkError}
              </p>
            )}

            <label className="field">
              <span className="field__label">URL</span>
              <input
                type="url"
                className="input"
                value={linkUrl}
                onChange={(event) => setLinkUrl(event.target.value)}
                placeholder="https://example.com"
                autoFocus
              />
            </label>

            <div className="confirm-actions">
              <button
                type="button"
                className="btn btn--primary"
                onClick={insertLink}
              >
                Insert
              </button>

              <button
                type="button"
                className="btn btn--ghost"
                onClick={closeLinkModal}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}