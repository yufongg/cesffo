import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiFetch } from '../api/client';
import SafeHtml from '../components/Security/SafeHtml';

// Left rail: one entry per topic (module). Lets the learner jump straight to
// any topic and shows which ones are already completed.
function TopicNav({ modules, current, onSelect }) {
  return (
    <aside className="side-nav topic-nav" aria-label="Course topics">
      <p className="side-nav__heading">Topics</p>
      <nav className="topic-nav__list">
        {modules.map((m, index) => {
          const isActive = index === current;
          return (
            <button
              key={m.module_id}
              type="button"
              className={`topic-nav__link${isActive ? ' topic-nav__link--active' : ''}`}
              onClick={() => onSelect(index)}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="topic-nav__index" aria-hidden="true">{index + 1}</span>
              <span className="topic-nav__title">{m.title}</span>
              {m.completed && (
                <span className="topic-nav__check" title="Completed" aria-label="Completed">✓</span>
              )}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

// A single topic, rendered one-per-page. The module's quiz CTA lives at the end
// of its own topic — so the course's last topic naturally carries the final quiz.
function TopicPage({ courseId, module, index, total }) {
  const hasQuiz = module.activities.length > 0;

  return (
    <div className="card module">
      <div className="card__body">
        <span className="eyebrow">Topic {index + 1} of {total}</span>
        <div className="module__head">
          <h3>{module.title}</h3>
          {module.completed && <span className="tag">Completed</span>}
        </div>

        {module.description && (
          // Parsed through the shared allow-list into React elements (no raw HTML).
          <SafeHtml className="module__description" html={module.description} />
        )}

        {module.reading_materials.map((m) => (
          <article key={m.material_id} className="reading-material">
            <h4>{m.title}</h4>
            <SafeHtml html={m.body} />
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
          <div className="topic-page__quiz">
            <Link
              to={`/courses/${courseId}/modules/${module.module_id}/quiz`}
              className="btn btn--primary"
            >
              {module.completed ? 'Review quiz' : 'Take quiz'}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

// Bottom pager: first / back-3 / prev / "Page X of Y" / next / forward-3 / last.
function Pager({ page, total, onChange }) {
  if (total <= 1) return null;
  const last = total - 1;
  const atStart = page === 0;
  const atEnd = page === last;

  return (
    <nav className="pager" aria-label="Topic pagination">
      <div className="pager__group">
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={() => onChange(0)} disabled={atStart} title="First topic" aria-label="First topic">«</button>
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={() => onChange(page - 3)} disabled={atStart} title="Back 3 topics" aria-label="Back 3 topics">−3</button>
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={() => onChange(page - 1)} disabled={atStart} title="Previous topic" aria-label="Previous topic">‹</button>
      </div>

      <span className="pager__status" aria-live="polite">Page {page + 1} of {total}</span>

      <div className="pager__group">
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={() => onChange(page + 1)} disabled={atEnd} title="Next topic" aria-label="Next topic">›</button>
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={() => onChange(page + 3)} disabled={atEnd} title="Forward 3 topics" aria-label="Forward 3 topics">+3</button>
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={() => onChange(last)} disabled={atEnd} title="Last topic" aria-label="Last topic">»</button>
      </div>
    </nav>
  );
}

export default function CourseLearn() {
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(0);

  const load = useCallback(() => {
    let active = true;
    apiFetch(`/api/v1/courses/${courseId}/learn`)
      .then((data) => { if (active) setCourse(data); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [courseId]);

  useEffect(() => load(), [load]);
  // Start at the first topic whenever a different course is opened.
  useEffect(() => { setPage(0); }, [courseId]);

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

  const modules = course.modules || [];
  const total = modules.length;
  const pct = Math.max(0, Math.min(100, Math.round((course.progress ?? 0) * 100)));

  // Keep the page index valid even if the topic count changes under us.
  const current = Math.min(page, Math.max(0, total - 1));

  // Single clamp point: every jump (sidebar or pager) is bounded here.
  const goToPage = (next) => {
    const clamped = Math.max(0, Math.min(total - 1, next));
    setPage(clamped);
    if (clamped !== current) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Course</span>
          <h1>{course.course_name}</h1>
        </div>

        <div className="progress" style={{ marginBottom: '24px' }}>
          <div className="progress__track">
            <div className="progress__bar" style={{ width: `${pct}%` }} />
          </div>
          <div className="progress__label">
            <span>{pct >= 100 ? 'Completed' : 'In progress'}</span>
            <span>{pct}%</span>
          </div>
        </div>

        {total === 0 ? (
          <div className="empty-state">
            <h3>No topics yet</h3>
            <p>This course doesn’t have any published content yet. Check back soon.</p>
          </div>
        ) : (
          <div className="dashboard">
            <TopicNav modules={modules} current={current} onSelect={goToPage} />
            <div className="dashboard__main">
              <TopicPage
                courseId={courseId}
                module={modules[current]}
                index={current}
                total={total}
              />
              <Pager page={current} total={total} onChange={goToPage} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
