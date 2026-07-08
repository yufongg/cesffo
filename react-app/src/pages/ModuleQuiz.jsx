import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiFetch } from '../api/client';

function QuizQuestion({ activity, answer, onChange, gradedResult }) {
  const isMcq = activity.activity_type === 'mcq_single' || activity.activity_type === 'mcq_multi';
  const selected = answer?.optionIds || new Set();
  const text = answer?.text || '';

  const toggleOption = (optionId) => {
    const next = new Set(activity.activity_type === 'mcq_single' ? [] : selected);
    if (selected.has(optionId) && activity.activity_type === 'mcq_multi') {
      next.delete(optionId);
    } else {
      next.add(optionId);
    }
    onChange({ optionIds: next });
  };

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
                disabled={!!gradedResult}
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
          onChange={(e) => onChange({ text: e.target.value })}
          placeholder="Type your answer…"
          maxLength={2000}
          disabled={!!gradedResult}
        />
      )}

      {gradedResult && (
        <p role="status" className={`alert ${gradedResult.is_correct ? 'alert--success' : 'alert--warning'}`}>
          {gradedResult.is_correct ? 'Correct' : 'Incorrect'}
        </p>
      )}
    </div>
  );
}

export default function ModuleQuiz() {
  const { courseId, moduleId } = useParams();
  const [module, setModule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Quiz state lives only here — leaving this page (and never hitting "Submit
  // quiz") unmounts everything below with no server write, so an abandoned
  // attempt never leaves a mark behind.
  const [answers, setAnswers] = useState({});
  const [results, setResults] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    let active = true;
    apiFetch(`/api/v1/modules/${moduleId}/materials`)
      .then((data) => { if (active) setModule(data); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [moduleId]);

  if (loading) return <div className="page"><div className="container"><p>Loading quiz…</p></div></div>;

  if (error) {
    return (
      <div className="page">
        <div className="container">
          <p role="alert" className="alert alert--error">{error}</p>
          <Link to={`/courses/${courseId}/learn`} className="btn btn--secondary">Back to course</Link>
        </div>
      </div>
    );
  }

  const activities = module.activities;

  const isAnswered = (activity) => {
    const a = answers[activity.activity_id];
    if (!a) return false;
    const isMcq = activity.activity_type === 'mcq_single' || activity.activity_type === 'mcq_multi';
    return isMcq ? (a.optionIds && a.optionIds.size > 0) : !!(a.text && a.text.trim());
  };

  const allAnswered = activities.every(isAnswered);

  const setAnswer = (activityId, value) => {
    setAnswers((prev) => ({ ...prev, [activityId]: value }));
  };

  const submitQuiz = async () => {
    setSubmitError('');
    setSubmitting(true);
    try {
      const graded = await Promise.all(
        activities.map(async (activity) => {
          const a = answers[activity.activity_id];
          const isMcq = activity.activity_type === 'mcq_single' || activity.activity_type === 'mcq_multi';
          const body = isMcq ? { option_ids: [...a.optionIds] } : { text: a.text };
          const response = await apiFetch(`/api/v1/activities/${activity.activity_id}/submit`, {
            method: 'POST',
            body,
          });
          return [activity.activity_id, response];
        }),
      );
      setResults(Object.fromEntries(graded));
    } catch (e) {
      setSubmitError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const retake = () => {
    setAnswers({});
    setResults(null);
    setSubmitError('');
  };

  const correctCount = results ? Object.values(results).filter((r) => r.is_correct).length : 0;

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Quiz</span>
          <h1>{module.title}</h1>
        </div>

        <div className="card module">
          <div className="card__body">
            <div className="quiz">
              {activities.map((a) => (
                <QuizQuestion
                  key={a.activity_id}
                  activity={a}
                  answer={answers[a.activity_id]}
                  onChange={(value) => setAnswer(a.activity_id, value)}
                  gradedResult={results?.[a.activity_id]}
                />
              ))}

              {submitError && <p role="alert" className="alert alert--error">{submitError}</p>}

              {results ? (
                <>
                  <p role="status" className={`alert ${correctCount === activities.length ? 'alert--success' : 'alert--warning'}`}>
                    You scored {correctCount} / {activities.length}
                  </p>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button type="button" className="btn btn--secondary btn--sm" onClick={retake}>
                      Retake quiz
                    </button>
                    <Link to={`/courses/${courseId}/learn`} className="btn btn--primary btn--sm">
                      Back to course
                    </Link>
                  </div>
                </>
              ) : (
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={submitQuiz}
                    disabled={!allAnswered || submitting}
                  >
                    {submitting ? 'Grading…' : 'Submit quiz'}
                  </button>
                  <Link to={`/courses/${courseId}/learn`} className="btn btn--ghost btn--sm">
                    Back to course
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
