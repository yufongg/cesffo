import React from 'react';
import { Link } from 'react-router-dom';

// Single source of truth for the support address so the mailto link and the
// visible text never drift apart.
const SUPPORT_EMAIL = 'cesffo.courses@gmail.com';
const MAILTO = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent('Cesffo Support Request')}`;

/* ----- Icons (stroke style, matching the rest of the app) --------------- */

function MailIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

const TOPICS = [
  {
    icon: <UserIcon />,
    title: 'Account & sign-in',
    body: 'Trouble signing in, updating your email, or keeping your account secure.',
  },
  {
    icon: <LockIcon />,
    title: 'Password & security',
    body: 'Reset a forgotten password, change your current one, or unlock your account.',
  },
  {
    icon: <BookIcon />,
    title: 'Courses & learning',
    body: 'Enrolling in courses, tracking progress, quizzes, and earning XP.',
  },
  {
    icon: <ChatIcon />,
    title: 'Community & forums',
    body: 'Posting questions, replying to others, and our community guidelines.',
  },
];

const FAQS = [
  {
    q: 'How do I reset a forgotten password?',
    a: (
      <>
        Head to the <Link to="/forgot-password">Forgot password</Link> page and enter
        your account email. We'll send a one-time reset link that stays valid for 30
        minutes. If it doesn't arrive, check your spam folder before trying again.
      </>
    ),
  },
  {
    q: 'Why is my account locked?',
    a: (
      <>
        For your security, accounts are temporarily locked after several failed
        sign-in attempts. Wait a short while and try again, or email us if you still
        can't get in and we'll help restore access.
      </>
    ),
  },
  {
    q: 'How do I enroll in a course?',
    a: (
      <>
        Open the <Link to="/marketplace">Marketplace</Link>, choose a course to see
        its preview, then select <strong>Enroll</strong>. It will appear under
        <em> My Learning</em> so you can pick up right where you left off.
      </>
    ),
  },
  {
    q: 'How do I update my profile or email address?',
    a: (
      <>
        Go to <Link to="/updateProfile">My Profile</Link> to update your details. For
        security, some changes may ask you to confirm your current password.
      </>
    ),
  },
  {
    q: 'How long until support replies?',
    a: (
      <>
        We aim to respond to every message within 1–2 business days. Including your
        account email and a clear description of the issue helps us resolve it faster.
      </>
    ),
  },
];

export default function HelpSupport() {
  return (
    <div className="page">
      <div className="container">
        <header className="page-header">
          <span className="eyebrow">Support</span>
          <h1>Help &amp; Support</h1>
          <p className="subtitle">
            Find quick answers to common questions, or reach our team directly —
            we're happy to help.
          </p>
        </header>

        {/* Primary contact — the one thing we most want people to find. */}
        <section className="support-contact card" aria-labelledby="support-contact-title">
          <div className="support-contact__lead">
            <span className="support-contact__icon" aria-hidden="true"><MailIcon /></span>
            <div>
              <h2 id="support-contact-title" className="support-contact__title">
                Contact our support team
              </h2>
              <p className="support-contact__sub">
                Email us and we'll get back to you within 1–2 business days. We
                typically reply Monday to Friday.
              </p>
              <a className="support-contact__email" href={MAILTO}>{SUPPORT_EMAIL}</a>
            </div>
          </div>
          <a className="btn btn--primary" href={MAILTO}>Email us</a>
        </section>

        {/* Help topics */}
        <section className="section">
          <div className="section__head">
            <h2>Browse help topics</h2>
          </div>
          <div className="support-grid">
            {TOPICS.map((t) => (
              <article className="support-topic" key={t.title}>
                <span className="support-topic__icon" aria-hidden="true">{t.icon}</span>
                <div>
                  <h3 className="support-topic__title">{t.title}</h3>
                  <p className="support-topic__body">{t.body}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        {/* FAQ — native details/summary so it's accessible and JS-free. */}
        <section className="section">
          <div className="section__head">
            <h2>Frequently asked questions</h2>
          </div>
          <div className="support-faq">
            {FAQS.map((item) => (
              <details className="support-faq__item" key={item.q}>
                <summary className="support-faq__q">
                  <span>{item.q}</span>
                  <svg className="support-faq__chevron" width="18" height="18"
                    viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </summary>
                <div className="support-faq__a">{item.a}</div>
              </details>
            ))}
          </div>
        </section>

        {/* Closing nudge back to contact for anything not covered above. */}
        <p className="support-foot">
          Still need a hand? Email us at{' '}
          <a href={MAILTO}>{SUPPORT_EMAIL}</a> and we'll take it from there.
        </p>
      </div>
    </div>
  );
}
