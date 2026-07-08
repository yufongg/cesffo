import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();
  const isAuthed = Boolean(localStorage.getItem('access_token'));

  return (
    <div className="notfound">
      <div className="notfound__inner">
        <div className="notfound__code">404</div>
        <h1>Page not found</h1>
        <p>
          The page you&apos;re looking for doesn&apos;t exist, may have moved, or
          you don&apos;t have access to it.
        </p>
        <div className="notfound__actions">
          <button type="button" className="btn btn--secondary" onClick={() => navigate(-1)}>
            Go back
          </button>
          <Link to={isAuthed ? '/courses' : '/'} className="btn btn--primary">
            {isAuthed ? 'Back to My Learning' : 'Back to login'}
          </Link>
        </div>
      </div>
    </div>
  );
}
