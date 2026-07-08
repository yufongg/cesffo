import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiFetch } from '../api/client';
import SafeHtml from '../components/Security/SafeHtml';
import { CartApi } from '../services/cartApi';

// Read-only syllabus for a course the student has NOT enrolled in yet. The
// backend /preview endpoint only returns the outline (module titles, blurbs and
// quiz counts) — never the reading bodies or quiz answers — so nothing
// sensitive is exposed here. Enrolling is what unlocks the real content.

function LockIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function PreviewModule({ module, index }) {
  const readings = module.reading_material_titles || [];
  return (
    <div className="card module">
      <div className="card__body">
        <div className="module__head">
          <h3>{index + 1}. {module.title}</h3>
          {module.activity_count > 0 && (
            <span className="tag">{module.activity_count} quiz question{module.activity_count === 1 ? '' : 's'}</span>
          )}
        </div>

        {module.description && (
          // Parsed through the shared allow-list into React elements (no raw HTML).
          <SafeHtml className="module__description" html={module.description} />
        )}

        {readings.length > 0 && (
          <ul className="preview-toc">
            {readings.map((title, i) => (
              <li key={i} className="preview-toc__item">
                <span className="preview-toc__lock" aria-hidden="true"><LockIcon /></span>
                {title}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function formatMoney(cents = 0, currency = 'SGD') {
  if (!cents) return 'Free';
  return new Intl.NumberFormat('en-SG', {
    style: 'currency',
    currency: currency || 'SGD',
  }).format(cents / 100);
}

export default function CoursePreview() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [enrolling, setEnrolling] = useState(false);
  const [addingToCart, setAddingToCart] = useState(false);
  const [enrollError, setEnrollError] = useState('');

  const load = useCallback(() => {
    let active = true;
    setLoading(true);
    apiFetch(`/api/v1/courses/${courseId}/preview`)
      .then((data) => { if (active) setCourse(data); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [courseId]);

  useEffect(() => load(), [load]);

  const enroll = async () => {
    setEnrollError('');
    setEnrolling(true);
    try {
      await apiFetch(`/api/v1/courses/${courseId}/enroll`, { method: 'POST' });
      navigate(`/courses/${courseId}/learn`);
    } catch (e) {
      setEnrollError(e.message);
      setEnrolling(false);
    }
  };

  const addToCart = async () => {
    setEnrollError('');
    setAddingToCart(true);
    try {
      await CartApi.addCourse(courseId);
      setCourse((prev) => ({ ...prev, is_in_cart: true }));
    } catch (e) {
      setEnrollError(e.message);
    } finally {
      setAddingToCart(false);
    }
  };

  if (loading) {
    return <div className="page"><div className="container"><p>Loading course…</p></div></div>;
  }

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
  console.log(course);
  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Course preview</span>
          <h1>{course.course_name}</h1>
          {course.instructor && <p className="subtitle">By {course.instructor}</p>}
        </div>

        {/* ---- Summary / meta ---- */}
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card__body">
            {course.summary && <p>{course.summary}</p>}

            <div className="course-card__tags" style={{ marginTop: '12px' }}>
              {course.level && <span className="tag">{course.level}</span>}
              {(course.tags || []).map((t) => <span className="tag" key={t}>{t}</span>)}
            </div>

            <div className="account-level__stats" style={{ marginTop: '16px' }}>
              <div><strong>{course.module_count}</strong><span>Modules</span></div>
              <div><strong>{course.total_activities}</strong><span>Quiz questions</span></div>
              <div><strong>{course.enrollment_count}</strong><span>Enrolled</span></div>
              <div><strong>{formatMoney(course.price_cents, course.currency)}</strong><span>Price</span></div>
              {course.xp_reward > 0 && (
                <div><strong>{course.xp_reward.toLocaleString()}</strong><span>XP reward</span></div>
              )}
            </div>

            {enrollError && (
              <p role="alert" className="alert alert--error" style={{ marginTop: '16px' }}>{enrollError}</p>
            )}

            <div style={{ display: 'flex', gap: '10px', marginTop: '20px', flexWrap: 'wrap' }}>
              { course.is_pending_payment ? (
                <Link to={`/courses/${courseId}/preview`} className="btn btn--primary" disabled>
                  Awaiting payment
                </Link>
              ) : course.is_enrolled ? (
                <Link to={`/courses/${courseId}/learn`} className="btn btn--primary">
                  Go to course
                </Link>
              ) : course.price_cents > 0 && course.is_in_cart ? (
                <Link to="/cart" className="btn btn--primary">
                  Go to cart
                </Link>
              ) : course.price_cents > 0 ? (
                <button type="button" className="btn btn--primary" onClick={addToCart} disabled={addingToCart}>
                  {addingToCart ? 'Adding…' : 'Add to cart'}
                </button>
              ) : (
                <button type="button" className="btn btn--primary" onClick={enroll} disabled={enrolling}>
                  {enrolling ? 'Enrolling…' : 'Enroll for free'}
                </button>
              )}
              <Link to="/marketplace" className="btn btn--ghost">Back to marketplace</Link>
            </div>
          </div>
        </div>

        {/* ---- Syllabus outline ---- */}
        <div className="section__head">
          <h2>What you'll learn</h2>
          {!course.is_enrolled && (
            <span className="count"><LockIcon /> Enroll to unlock</span>
          )}
        </div>

        {course.modules.length > 0 ? (
          <div className="module-list">
            {course.modules.map((m, i) => (
              <PreviewModule key={m.module_id} module={m} index={i} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <h3>Syllabus coming soon</h3>
            <p>This course doesn't have any published modules yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}
