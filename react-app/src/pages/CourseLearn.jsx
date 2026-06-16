import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiFetch } from '../api/client';

function ModuleSection({ courseId, module }) {
  const hasQuiz = module.activities.length > 0;

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

        {hasQuiz && (
          // Quiz lives on its own page — read the content here first, then
          // move on to take the quiz once you're done.
          <Link to={`/courses/${courseId}/modules/${module.module_id}/quiz`} className="btn btn--primary btn--sm">
            {module.completed ? 'Review quiz' : 'Take quiz'}
          </Link>
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
            <ModuleSection key={m.module_id} courseId={courseId} module={m} />
          ))}
        </div>
      </div>
    </div>
  );
}
