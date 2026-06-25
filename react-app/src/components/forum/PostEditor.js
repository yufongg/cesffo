import { useEffect, useRef, useState } from 'react';

function PostEditor({
  onSubmit,
  submitLabel = 'Post',
  cancelLabel = 'Cancel',
  onCancel,
  placeholder = 'Write a forum post.',
  attachmentHelpText = 'Upload image files.',
  maxFiles = 5,
  existingFileCount = 0,
  initialContent = '',
}) {
  const editorRef = useRef(null);
  const fileInputRef = useRef(null);

  const [files, setFiles] = useState([]);
  const [blockType, setBlockType] = useState('p');
  const [activeFormats, setActiveFormats] = useState({
    bold: false,
    italic: false,
    underline: false,
    bullet: false,
  });
  const [fileErrorMessage, setFileErrorMessage] = useState('');

  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.innerHTML = initialContent || '';
    }
  }, [initialContent]);

  function refreshToolbarState() {
    setActiveFormats({
      bold: document.queryCommandState('bold'),
      italic: document.queryCommandState('italic'),
      underline: document.queryCommandState('underline'),
      bullet: document.queryCommandState('insertUnorderedList'),
    });

    const block = document.queryCommandValue('formatBlock')?.toLowerCase();
    setBlockType(block === 'h2' ? 'h2' : 'p');
  }

  function applyFormat(command, value = null) {
    editorRef.current?.focus();

    if (command === 'insertUnorderedList') {
      document.execCommand('formatBlock', false, 'p');
      setBlockType('p');
    }

    document.execCommand(command, false, value);
    setTimeout(refreshToolbarState, 0);
  }

  function handleEditorKeyDown(event) {
    if (event.key === 'Enter' && blockType === 'h2') {
      event.preventDefault();
      document.execCommand('insertHTML', false, '<p><br></p>');
      setBlockType('p');
      document.execCommand('formatBlock', false, 'p');
    }
  }

  function clearEditor() {
    if (editorRef.current) editorRef.current.innerHTML = '';
    setFiles([]);
    setFileErrorMessage('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      if (existingFileCount + files.length > maxFiles) {
        setFileErrorMessage(`Maximum ${maxFiles} images allowed.`);
        return;
      }

      const content = editorRef.current?.innerHTML || '';
      const shouldClear = await onSubmit(content, files.slice(0, maxFiles));

      if (shouldClear !== false) {
        clearEditor();
      }
    } catch (error) {
      setFileErrorMessage(error.message || 'Request failed');
    }
  }

  return (
    <form className="post-editor" onSubmit={handleSubmit}>
      <div className="editor-toolbar">
        <select
          value={blockType}
          onChange={(event) => {
            setBlockType(event.target.value);
            applyFormat('formatBlock', event.target.value);
          }}
        >
          <option value="p">Paragraph</option>
          <option value="h2">Heading</option>
        </select>

        <button
          type="button"
          className={activeFormats.bold ? 'active' : ''}
          onClick={() => applyFormat('bold')}
          title="Bold"
        >
          <strong>B</strong>
        </button>

        <button
          type="button"
          className={activeFormats.italic ? 'active' : ''}
          onClick={() => applyFormat('italic')}
          title="Italic"
        >
          <em>I</em>
        </button>

        <button
          type="button"
          className={activeFormats.underline ? 'active' : ''}
          onClick={() => applyFormat('underline')}
          title="Underline"
        >
          <u>U</u>
        </button>

        <button
          type="button"
          className={activeFormats.bullet ? 'active' : ''}
          onClick={() => applyFormat('insertUnorderedList')}
          title="Bullet list"
        >
          •
        </button>

        <button
          type="button"
          onClick={() => {
            const url = window.prompt('Enter link URL');
            if (url) applyFormat('createLink', url);
          }}
          title="Link"
        >
          🔗
        </button>
      </div>

      <div
        ref={editorRef}
        className="rich-editor"
        contentEditable
        suppressContentEditableWarning
        data-placeholder={placeholder}
        onKeyDown={handleEditorKeyDown}
        onKeyUp={refreshToolbarState}
        onMouseUp={refreshToolbarState}
        onInput={refreshToolbarState}
      />

      {fileErrorMessage && (
        <div className="thread-warning">
          <span>⚠️</span>
          <span>{fileErrorMessage}</span>
        </div>
      )}

      <div className="attachment-box">
        <div>
          <strong>Attachments</strong>
          <p>{attachmentHelpText}</p>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          onChange={(event) => {
            const selectedFiles = Array.from(event.target.files);

            if (selectedFiles.length > maxFiles) {
              setFileErrorMessage(`Maximum ${maxFiles} images allowed.`);
              event.target.value = '';
              setFiles([]);
              return;
            }

            setFileErrorMessage('');
            setFiles(selectedFiles);
          }}
        />
      </div>

      <div className="editor-actions">
        <button type="submit" className="primary">
          {submitLabel}
        </button>

        <button
          type="button"
          className="secondary"
          onClick={() => {
            clearEditor();
            if (onCancel) onCancel();
          }}
        >
          {cancelLabel}
        </button>
      </div>
    </form>
  );
}

export default PostEditor;