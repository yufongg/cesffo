import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiFetch } from '../api/client';

function ActivityBlock({ activity, onGraded }) {
  const isMcq = activity.activity_type === 'mcq_single' || activity.activity_type === 'mcq_multi';
  const [selected, setSelected] = useState(new Set());
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const toggleOption = (optionId) => {
    setSelected((prev) => {
      const next = new Set(activity.activity_type === 'mcq_single' ? [] : prev);
      if (prev.has(optionId) && activity.activity_type === 'mcq_multi') {
        next.delete(optionId);
      } else {
        next.add(optionId);
      }
      return next;
    });
  };

  const submit = async () => {
    setError('');
    setSubmitting(true);
    try {
      const body = isMcq ? { option_ids: [...selected] } : { text };
      const response = await apiFetch(`/api/v1/activities/${activity.activity_id}/submit`, {
        method: 'POST',
        body,
      });
      setResult(response);
      onGraded();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit = isMcq ? selected.size > 0 : text.trim().length > 0;

  return (
    <div className="quiz-question">
      <p className="quiz-question__prompt">{activity.prompt}</p>

      {isMcq ? (
        <div className="quiz-options">
          {activity.options.map((opt) => (
            <label key={opt.option_id} className="quiz-option">
              <input
                type={activity.activity_type === 'mcq_single' ? 'radio' : 'checkbox'}
                name={activity.activity_id}
                checked={selected.has(opt.option_id)}
                onChange={() => toggleOption(opt.option_id)}
              />
              <span>{opt.option_text}</span>
            </label>
          ))}
        </div>
      ) : (
        <input
          type="text"
          className="input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type your answer…"
          maxLength={2000}
        />
      )}

      {error && <p role="alert" className="alert alert--error">{error}</p>}

      {result && (
        <p role="status" className={`alert ${result.is_correct ? 'alert--success' : 'alert--warning'}`}>
          {result.is_correct ? 'Correct!' : 'Not quite — try again.'} (attempt {result.attempt_number})
        </p>
      )}

      <button type="button" className="btn btn--secondary btn--sm" onClick={submit} disabled={!canSubmit || submitting}>
        {submitting ? 'Submitting…' : result ? 'Try again' : 'Submit answer'}
      </button>
    </div>
  );
}

function ModuleSection({ module, onGraded }) {
  return (
    <div className="card module">
      <div className="card__body">
        <div className="module__head">
          <h3>{module.title}</h3>
          {module.completed && <span className="tag">Completed</span>}
        </div>

        {module.description && (
          // Server-sanitized (nh3 allow-list) before storage — safe to render as HTML.
          <div className="module__description" dangerouslySetInnerHTML={{ __html: module.description }} />
        )}

        {module.reading_materials.map((m) => (
          <article key={m.material_id} className="reading-material">
            <h4>{m.title}</h4>
            <div dangerouslySetInnerHTML={{ __html: m.body }} />
          </article>
        ))}

        {module.media_contents.map((m) => (
          <div key={m.media_id} className="media-content">
            <h4>{m.title}</h4>
            {m.media_type === 'video' ? (
              <video controls src={m.media_url} style={{ maxWidth: '100%' }} />
            ) : m.media_type === 'image' ? (
              <img src={m.media_url} alt={m.title} style={{ maxWidth: '100%' }} />
            ) : (
              <a href={m.media_url} target="_blank" rel="noreferrer">Open {m.media_type}</a>
            )}
          </div>
        ))}

        {module.activities.length > 0 && (
          <div className="quiz">
            {module.activities.map((a) => (
              <ActivityBlock key={a.activity_id} activity={a} onGraded={onGraded} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function CourseLearn() {
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    let active = true;
    apiFetch(`/api/v1/courses/${courseId}/learn`)
      .then((data) => { if (active) setCourse(data); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [courseId]);

  useEffect(() => load(), [load]);

  if (loading) return <div className="page"><div className="container"><p>Loading course…</p></div></div>;

  if (error) {
    return (
      <div className="page">
        <div className="container">
          <p role="alert" className="alert alert--error">{error}</p>
          <Link to="/marketplace" className="btn btn--secondary">Back to marketplace</Link>
        </div>
      </div>
    );
  }

  const pct = Math.max(0, Math.min(100, Math.round((course.progress ?? 0) * 100)));

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Course</span>
          <h1>{course.course_name}</h1>
        </div>

        <div className="progress" style={{ marginBottom: '32px' }}>
          <div className="progress__track">
            <div className="progress__bar" style={{ width: `${pct}%` }} />
          </div>
          <div className="progress__label">
            <span>{pct >= 100 ? 'Completed' : 'In progress'}</span>
            <span>{pct}%</span>
          </div>
        </div>

        <div className="module-list">
          {course.modules.map((m) => (
            <ModuleSection key={m.module_id} module={m} onGraded={load} />
          ))}
        </div>
      </div>
    </div>
  );
}
