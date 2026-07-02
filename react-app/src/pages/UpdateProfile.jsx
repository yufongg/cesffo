import React from 'react';

export default function UpdateProfile() {
  return (
    <div className="page">
      <div className="container" style={{ maxWidth: '720px' }}>
        <div className="page-header">
          <span className="eyebrow">Account</span>
          <h1>Profile settings</h1>
          <p className="subtitle">Update your personal details and how others see you.</p>
        </div>

        <div className="card">
          <div className="card__body">
            <form>
              <div className="field">
                <label htmlFor="name" className="label">Update Username</label>
                <input id="name" name="name" type="text" className="input"
                  placeholder="Enter your name" />
              </div>

              <div className="field">
                <label htmlFor="email" className="label">Update Email</label>
                <input id="email" name="email" type="email" className="input"
                  placeholder="you@example.com" />
                <small className="field__hint">
                  We&apos;ll use this address for account and course notifications.
                </small>
              </div>

              <div className='field'>
                <strong className="field__hint">
                  Password Reset
                </strong>

              </div>
              <div className="field">
                <label htmlFor="name" className="label">Old-Password</label>
                <input id="opass" name="opass" type="password" className="input"
                  placeholder="Enter your current password" />
              </div>

              <div className="field">
                <label htmlFor="name" className="label">New Password</label>
                <input id="npass" name="npass" type="password" className="input"
                  placeholder="Enter new password" />
              </div>

              <div className="field">
                <label htmlFor="name" className="label">Retype Password</label>
                <input id="r_npass" name="r_npass" type="password" className="input"
                  placeholder="Retype new password" />
              </div>

              <div className="row-actions" style={{ marginTop: '8px' }}>
                <button type="submit" className="btn btn--primary">Save changes</button>
                <button type="reset" className="btn btn--secondary">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
