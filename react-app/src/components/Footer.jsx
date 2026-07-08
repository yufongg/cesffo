import React from 'react';
import { Link } from 'react-router-dom';

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="container">
        <div className="footer__top">
          <div>
            <span className="footer__brand">
              <span className="brand__mark">C</span>
              Cesffo
            </span>
            <p className="footer__blurb">
              Practical financial literacy education — structured courses, tools,
              and resources to help you make confident money decisions.
            </p>
          </div>

          <div className="footer__col">
            <h4>Learn</h4>
            <ul>
              <li><Link to="/">Courses</Link></li>
              <li><Link to="/">Resources</Link></li>
              <li><Link to="/">Pricing</Link></li>
            </ul>
          </div>

          <div className="footer__col">
            <h4>Company</h4>
            <ul>
              <li><Link to="/">About</Link></li>
              <li><Link to="/">Contact</Link></li>
              <li><Link to="/">Careers</Link></li>
            </ul>
          </div>

          <div className="footer__col">
            <h4>Legal</h4>
            <ul>
              <li><Link to="/">Privacy</Link></li>
              <li><Link to="/">Terms</Link></li>
              <li><Link to="/">Security</Link></li>
            </ul>
          </div>
        </div>

        <div className="footer__bottom">
          <span>© {year} Cesffo. All rights reserved.</span>
          <span>Built for financial confidence.</span>
        </div>
      </div>
    </footer>
  );
}
