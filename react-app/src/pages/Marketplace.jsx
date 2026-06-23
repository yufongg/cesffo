import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api/client';
import CourseCard from '../components/CourseCard';
import { sanitizeSearch, MAX_SEARCH_LENGTH } from '../components/Security/Sanitize';

function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

// Mirrors CourseCard's geometry so the grid does not reflow when data arrives.
function CourseCardSkeleton() {
  return (
    <article className="course-card course-card--skeleton" aria-hidden="true">
      <div className="skeleton skeleton__banner" />
      <div className="course-card__body">
        <div className="skeleton skeleton__line skeleton__line--title" />
        <div className="skeleton skeleton__line skeleton__line--meta" />
        <div className="skeleton skeleton__line" />
        <div className="skeleton skeleton__line skeleton__line--short" />
        <div className="course-card__foot">
          <div className="skeleton skeleton__line skeleton__line--pill" />
          <div className="skeleton skeleton__btn" />
        </div>
      </div>
    </article>
  );
}

function BookIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function formatMoney(cents = 0, currency = 'SGD') {
  if (!cents) return 'Free';
  return new Intl.NumberFormat('en-SG', {
    style: 'currency',
    currency: currency || 'SGD',
  }).format(cents / 100);
}

// Spotlight for the single most-popular course, shown only on the unfiltered
// "Most popular" view. A wider, asymmetric tile so it reads as the lead rather
// than just another card in the grid.
function FeaturedCourse({ course }) {
  const navigate = useNavigate();
  const {
    course_name,
    instructor,
    tags = [],
    summary,
    xp_reward = 0,
    price_cents = 0,
    currency = 'SGD',
    enrollment_count = 0,
  } = course;

  return (
    <article className="featured-course">
      <div className="featured-course__art" aria-hidden="true">
        <span className="featured-course__art-icon"><BookIcon /></span>
        {xp_reward > 0 && (
          <span className="course-card__xp">+{xp_reward.toLocaleString()} XP</span>
        )}
      </div>
      <div className="featured-course__body">
        <span className="featured-course__badge">Most popular</span>
        <h3 className="featured-course__title">{course_name}</h3>
        {instructor && <p className="featured-course__meta">By {instructor}</p>}
        {summary && <p className="featured-course__summary">{summary}</p>}
        {tags.length > 0 && (
          <div className="course-card__tags">
            {tags.map((t) => <span className="tag" key={t}>{t}</span>)}
          </div>
        )}
        <div className="featured-course__foot">
          <span className="course-card__enrollments">
            {formatMoney(price_cents, currency)} · {enrollment_count} enrolled
          </span>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => navigate(`/courses/${course.course_id}/preview`)}
          >
            View course
          </button>
        </div>
      </div>
    </article>
  );
}

const SORTS = [
  { value: 'popular', label: 'Most popular' },
  { value: 'newest', label: 'Newest' },
  { value: 'name', label: 'Name (A-Z)' },
];

export default function Marketplace() {
  const [search, setSearch] = useState('');
  const [tag, setTag] = useState('');           // active category filter ('' = all)
  const [sort, setSort] = useState('popular');

  const [categories, setCategories] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  //? Default fetch to grab all available courses. Will be sort by name bydefault
  useEffect(() => {
    let active = true;
    apiFetch('/api/v1/courses?sort=name')
      .then((list) => {
        if (!active) return;
        const set = new Set();
        (list || []).forEach((c) => (c.tags || []).forEach((t) => set.add(t)));
        setCategories([...set].sort((a, b) => a.localeCompare(b)));
      })
      .catch(() => { /* if error, then nothing will happen  */ });
    return () => { active = false; };
  }, []);


  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');

    const handle = setTimeout(() => {
      const params = new URLSearchParams();
      const cleaned = sanitizeSearch(search).trim();
      if (cleaned) params.set('search', cleaned);
      if (tag) params.set('tag', tag);
      params.set('sort', sort);

      apiFetch(`/api/v1/courses?${params.toString()}`)
        .then((list) => { if (active) setCourses(list || []); })
        .catch((e) => { if (active) setError(e.message); })
        .finally(() => { if (active) setLoading(false); });
    }, 250);

    return () => { active = false; clearTimeout(handle); };
  }, [search, tag, sort]);

  const resultLabel = useMemo(() => {
    const n = courses.length;
    return `${n} ${n === 1 ? 'course' : 'courses'}`;
  }, [courses.length]);

  const enrolledCourses = useMemo(() => courses.filter((c) => c.is_enrolled), [courses]);
  const otherCourses = useMemo(() => courses.filter((c) => !c.is_enrolled), [courses]);

  // Only spotlight a course on the genuine "most popular" view — not while the
  // learner is searching or filtering, where "the top result" isn't meaningful.
  const isPristinePopular = sort === 'popular' && !search.trim() && !tag;
  const featured = isPristinePopular && otherCourses.length > 0 ? otherCourses[0] : null;
  const gridCourses = featured ? otherCourses.slice(1) : otherCourses;

  return (
    <div className="page">
      <div className="container">
        <header className="market-hero">
          <div className="market-hero__intro">
            <span className="eyebrow">Marketplace</span>
            <h1>Explore courses</h1>
            <p className="market-hero__sub">
              Browse financial literacy courses by topic and find your next skill.
            </p>
          </div>

          <div className="market-hero__controls">
            <div className="search">
              <span className="search__icon"><SearchIcon /></span>
              <input
                type="text"
                className="input"
                value={search}
                onChange={(e) => setSearch(sanitizeSearch(e.target.value))}
                placeholder="Search courses…"
                aria-label="Search courses"
                maxLength={MAX_SEARCH_LENGTH}
              />
            </div>

            <select
              className="select"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              aria-label="Sort courses"
            >
              {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </header>

        {categories.length > 0 && (
          <div className="chips chips--topics" role="group" aria-label="Filter by category">
            <button
              type="button"
              className={`chip ${tag === '' ? 'chip--active' : ''}`}
              onClick={() => setTag('')}
            >
              All topics
            </button>
            {categories.map((c) => (
              <button
                key={c}
                type="button"
                className={`chip ${tag === c ? 'chip--active' : ''}`}
                onClick={() => setTag(c)}
              >
                {c}
              </button>
            ))}
          </div>
        )}

        {error && <p role="alert" className="alert alert--error">{error}</p>}

        {loading ? (
          <div className="course-grid" aria-busy="true">
            {Array.from({ length: 6 }).map((_, i) => <CourseCardSkeleton key={i} />)}
          </div>
        ) : courses.length > 0 ? (
          <>
            <p className="subtitle" style={{ marginBottom: '16px' }}>{resultLabel}</p>

            {enrolledCourses.length > 0 && (
              <section className="section">
                <div className="section__head">
                  <h2>Your courses</h2>
                  <span className="count">{enrolledCourses.length} enrolled</span>
                </div>
                <div className="course-grid">
                  {enrolledCourses.map((c) => <CourseCard key={c.course_id} course={c} />)}
                </div>
              </section>
            )}

            {otherCourses.length > 0 && (
              <section className="section">
                <div className="section__head">
                  <h2>{enrolledCourses.length > 0 ? 'Discover more' : 'All courses'}</h2>
                  <span className="count">{otherCourses.length} available</span>
                </div>
                {featured && <FeaturedCourse course={featured} />}
                <div className="course-grid">
                  {gridCourses.map((c) => <CourseCard key={c.course_id} course={c} />)}
                </div>
              </section>
            )}
          </>
        ) : (
          <div className="empty-state">
            <h3>No courses match your search</h3>
            <p>Try a different keyword or clear the filters.</p>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => { setSearch(''); setTag(''); }}
            >
              Clear filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
