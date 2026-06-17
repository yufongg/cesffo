import React from 'react';
import { useNavigate } from 'react-router-dom';

function BookIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

export default function CourseCard({ course }) {
  const {
    course_name,
    instructor,
    tags = [],
    summary,
    level,
    xp_reward = 0,
    enrollment_count = 0,
    is_enrolled = false,
    progress,
  } = course;

  const navigate = useNavigate();
  const pct = Math.max(0, Math.min(100, Math.round((progress ?? 0) * 100)));
  const completed = is_enrolled && pct >= 100;

  const cta = is_enrolled ? (completed ? 'Review' : 'Continue') : 'View course';
  // Enrolled learners jump straight into the content; everyone else gets the
  // read-only preview/syllabus where they can choose to enroll.
  const target = is_enrolled
    ? `/courses/${course.course_id}/learn`
    : `/courses/${course.course_id}/preview`;

  return (
    <article className="course-card">
      <div className={`course-card__banner ${is_enrolled ? '' : 'course-card__banner--alt'}`}>
        <span className="course-card__banner-icon"><BookIcon /></span>
        {xp_reward > 0 && (
          <span className="course-card__xp" title="XP earned on completion">
            +{xp_reward.toLocaleString()} XP
          </span>
        )}
        {level && <span className="course-card__level">{level}</span>}
      </div>

      <div className="course-card__body">
        <h3 className="course-card__title">{course_name}</h3>
        {instructor && <p className="course-card__meta">By {instructor}</p>}
        {summary && <p className="course-card__summary">{summary}</p>}

        {is_enrolled && progress != null && (
          <div className="progress">
            <div className="progress__track">
              <div className="progress__bar" style={{ width: `${pct}%` }} />
            </div>
            <div className="progress__label">
              <span>{completed ? 'Completed' : 'In progress'}</span>
              <span>{pct}%</span>
            </div>
          </div>
        )}

        {tags.length > 0 && (
          <div className="course-card__tags">
            {tags.map((t) => <span className="tag" key={t}>{t}</span>)}
          </div>
        )}

        <div className="course-card__foot">
          <span className="course-card__enrollments">{enrollment_count} enrolled</span>
          <button
            type="button"
            className={`btn btn--sm ${is_enrolled ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => navigate(target)}
          >
            {cta}
          </button>
        </div>
      </div>
    </article>
  );
}
