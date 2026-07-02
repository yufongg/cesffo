import React, { useEffect, useRef, useState } from 'react';
import { sanitizeHtml } from '../Security/SafeHtml';

// This one mimics the SIT discussion board text area
export default function RichTextEditor({ initialContent = '', onChange, placeholder = 'Write your post…' }) {
  const editorRef = useRef(null);
  const [active, setActive] = useState({ bold: false, italic: false, underline: false, bullet: false });


  useEffect(() => {
    const el = editorRef.current;
    // Run incoming content through the shared allow-list before assigning it to
    // the live contentEditable, so a malformed/hostile draft can't seed markup.
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

  const addLink = () => {
    const url = window.prompt('Enter a URL (https://…)');
    if (!url) return;
    if (!/^https?:\/\//i.test(url)) {
      window.alert('Links must start with http:// or https://');
      return;
    }
    exec('createLink', url);
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
        <Btn label="🔗 Link" title="Insert link" onClick={addLink} />
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
    </div>
  );
}
