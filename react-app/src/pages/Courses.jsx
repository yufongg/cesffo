import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api/client';
import DashboardSidebar from '../components/DashboardSidebar';
import CourseCard from '../components/CourseCard';
import PiggyProgress from '../components/PiggyProgress';
import { useAuth } from '../components/Security/RoleCheck';

// --- Tier / XP model -------------------------------------------------------
//? There is no XP/tier backend yet, so we derive a lightweight score from the
//? progress of the courses the user is already enrolled in: every enrolled
//? course is worth up to 1000 XP, scaled by how far through it they are. When a
//? real progression service exists, swap `deriveProgress()` for that payload.
const XP_PER_COURSE = 1000;

const TIERS = [
  { name: 'Bronze', min: 0, className: 'tier--bronze' },
  { name: 'Silver', min: 2000, className: 'tier--silver' },
  { name: 'Gold', min: 5000, className: 'tier--gold' },
  { name: 'Platinum', min: 10000, className: 'tier--platinum' },
  { name: 'Diamond', min: 20000, className: 'tier--diamond' },
];

function deriveTier(totalXp) {
  let idx = 0;
  for (let i = 0; i < TIERS.length; i += 1) {
    if (totalXp >= TIERS[i].min) idx = i;
  }
  return TIERS[idx];
}

function deriveProgress(enrolled) {
  const totalXp = enrolled.reduce(
    (sum, c) => sum + Math.round(Math.max(0, Math.min(1, c.progress ?? 0)) * XP_PER_COURSE),
    0,
  );
  const level = Math.floor(totalXp / 500) + 1;

  const tier = deriveTier(totalXp);
  const idx = TIERS.indexOf(tier);

  const nextTier = TIERS[idx + 1] || null;
  const span = nextTier ? nextTier.min - tier.min : 1;
  const into = totalXp - tier.min;
  const pctToNext = nextTier ? Math.round((into / span) * 100) : 100;

  return { totalXp, level, tier, nextTier, pctToNext };
}

// --- Horizontal course row (max 2–3 ongoing) -------------------------------
function CourseProgressRow({ course }) {
  const pct = Math.max(0, Math.min(100, Math.round((course.progress ?? 0) * 100)));
  const completed = pct >= 100;
  return (
    <article className="course-row">
      <div className="course-row__thumb" aria-hidden="true">
        <span>{course.course_name?.charAt(0)?.toUpperCase() || 'C'}</span>
      </div>
      <div className="course-row__body">
        <div className="course-row__head">
          <h3 className="course-row__title">{course.course_name}</h3>
          {course.level && <span className="course-row__level">{course.level}</span>}
          {course.xp_reward > 0 && (
            <span className="xp-chip">{course.xp_reward.toLocaleString()} XP</span>
          )}
        </div>
        {course.instructor && <p className="course-row__meta">By {course.instructor}</p>}
        <div className="progress">
          <div className="progress__track">
            <div className="progress__bar" style={{ width: `${pct}%` }} />
          </div>
          <div className="progress__label">
            <span>{completed ? 'Completed' : 'In progress'}</span>
            <span>{pct}%</span>
          </div>
        </div>
      </div>
      <div className="course-row__action">
        <Link to={`/courses/${course.course_id}/learn`} className="btn btn--primary btn--sm">
          {completed ? 'Review' : 'Continue'}
        </Link>
      </div>
    </article>
  );
}

export default function Courses() {
  const [data, setData] = useState({ enrolled: [], recommended: [] });
  const [leaderboard, setLeader] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  //? Grab info for leaderboards

  useEffect(() => {
    let active = true;
    apiFetch('/api/v1/courses/scores')
      .then((response) => {
        if (active) setLeader(response.leaderboard || []);
      })
      .catch((e) => { if (active) setError(e.message); })
      .finally((e) => { if (active) setLoading(false); });
    return () => {active = false;};
  }, []);

  //? Grab info enrolled course
  useEffect(() => {
    let active = true;
    apiFetch('/api/v1/courses/overview')
      .then((d) => {
        if (active) setData({ enrolled: d.enrolled || [], recommended: d.recommended || [] });
      })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const { enrolled, recommended } = data;
  const user = useAuth();
  const username = user?.username || '';

  const stats = useMemo(() => deriveProgress(enrolled), [enrolled]);
  const completedCount = enrolled.filter((c) => (c.progress ?? 0) >= 1).length;

  // Show at most three ongoing courses, freshest progress first.
  const ongoing = useMemo(
    () => [...enrolled]
      .filter((c) => (c.progress ?? 0) < 1)
      .sort((a, b) => (b.progress ?? 0) - (a.progress ?? 0))
      .slice(0, 3),
    [enrolled],
  );

  return (
    <div className="page">
      <div className="container dashboard">
        <DashboardSidebar />

        <div className="dashboard__main">
          <div className="page-header">
            <span className="eyebrow">My Learning</span>
            <h1>Welcome back{username ? `, ${username}` : ''}</h1>
            <p className="subtitle">Pick up where you left off, or discover something new.</p>
          </div>

          {error && <p role="alert" className="alert alert--error">{error}</p>}

          {loading ? (
            <p style={{ color: 'var(--color-muted)' }}>Loading your dashboard…</p>
          ) : (
            <>
              {/* ---- Account level ---- */}
              <section className="section">
                <div className="section__head">
                  <h2>Account level</h2>
                </div>

                <div className="account-level">
                  <PiggyProgress pct={stats.pctToNext} level={stats.level} />

                  <div className="account-level__body">
                    <div className="account-level__toprow">
                      <span className={`tier-badge ${stats.tier.className}`}>{stats.tier.name} tier</span>
                      <span className="account-level__xp">
                        {stats.totalXp.toLocaleString()} XP
                      </span>
                    </div>

                    <div className="progress">
                      <div className="progress__track">
                        <div className="progress__bar" style={{ width: `${stats.pctToNext}%` }} />
                      </div>
                      <div className="progress__label">
                        <span>
                          {stats.nextTier
                            ? `${stats.nextTier.min - stats.totalXp} XP to ${stats.nextTier.name}`
                            : 'Top tier reached'}
                        </span>
                        <span>{stats.pctToNext}%</span>
                      </div>
                    </div>

                    <div className="account-level__stats">
                      <div><strong>{enrolled.length}</strong><span>Enrolled</span></div>
                      <div><strong>{completedCount}</strong><span>Completed</span></div>
                      <div><strong>0</strong><span>XP this week</span></div>
                    </div>
                  </div>
                </div>
              </section>

              {/* ---- Continue learning (horizontal, max 3) ---- */}
              <section className="section">
                <div className="section__head">
                  <h2>Continue learning</h2>
                  <Link to="/marketplace" className="count">Browse all →</Link>
                </div>

                {ongoing.length > 0 ? (
                  <div className="course-rows">
                    {ongoing.map((c) => <CourseProgressRow key={c.course_id} course={c} />)}
                  </div>
                ) : (
                  <div className="empty-state">
                    <h3>No courses in progress</h3>
                    <p>Browse the marketplace to start building your financial skills.</p>
                    <Link to="/marketplace" className="btn btn--primary">Explore courses</Link>
                  </div>
                )}
              </section>

              {/* ---- Same-tier scoreboard ---- */}
              <section className="section">
                <div className="section__head">
                  <h2>Your {stats.tier.name} tier</h2>
                  <span className="count">Learners near your rank</span>
                </div>

                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th style={{ width: 64 }}>Rank</th>
                        <th>Learner</th>
                        <th>Tier</th>
                        <th style={{ textAlign: 'right' }}>XP</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leaderboard.map((p) => {
                        const tier = deriveTier(p.xp);
                        return (
                          <tr key={p.username} className={p.is_you ? 'scoreboard__me' : undefined}>
                            <td>#{p.rank}</td>
                            <td className="table__user">{p.username}{p.is_you && ' (you)'}</td>
                            <td><span className={`tier-badge ${tier.className}`}>{tier.name}</span></td>
                            <td style={{ textAlign: 'right' }}>{p.xp.toLocaleString()}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* ---- Recommended (the one intentional grid, capped) ---- */}
              {recommended.length > 0 && (
                <section className="section">
                  <div className="section__head">
                    <h2>Recommended for you</h2>
                    <Link to="/marketplace" className="count">View all →</Link>
                  </div>
                  <div className="course-grid">
                    {recommended.slice(0, 3).map((c) => (
                      <CourseCard key={c.course_id} course={c} />
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
