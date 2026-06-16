import React, { useEffect, useMemo, useState } from 'react';
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

const SORTS = [
  { value: 'popular', label: 'Most popular' },
  { value: 'newest', label: 'Newest' },
  { value: 'name', label: 'Name (A–Z)' },
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

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Marketplace</span>
          <h1>Explore courses</h1>
          <p className="subtitle">Browse financial literacy courses by topic and find your next skill.</p>
        </div>

        <div className="filters">
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
            style={{ flex: '0 1 200px' }}
          >
            {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>

        {categories.length > 0 && (
          <div className="chips" role="group" aria-label="Filter by category">
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
          <p style={{ color: 'var(--color-muted)' }}>Loading courses…</p>
        ) : courses.length > 0 ? (
          <>
            <p className="subtitle" style={{ marginBottom: '16px' }}>{resultLabel}</p>

            { /* This creates a card for EACH course id found from the search */}
            <div className="course-grid">
              {courses.map((c) => <CourseCard key={c.course_id} course={c} />)}
            </div>
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
