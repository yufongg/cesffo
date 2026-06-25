import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { NavLink } from 'react-router-dom';
import { CartApi } from '../services/cartApi';

// Left-hand dashboard navigation, inspired by the OffSec console layout.
//? These are presentational entry points only — the destinations (cart,
//? achievements, etc.) are placeholders for now. Routes that don't exist yet
//? fall through to the catch-all <NotFound/> in App.js, so nothing breaks.

// --- Icons ---
function BrowseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
    </svg>
  );
}

function CartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="9" cy="21" r="1" />
      <circle cx="20" cy="21" r="1" />
      <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
    </svg>
  );
}

function TrophyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4z" />
      <path d="M5 9a3 3 0 0 1-3-3V5h3M19 9a3 3 0 0 0 3-3V5h-3" />
    </svg>
  );
}

function LeaderboardIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function ForumIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

function SupportIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

// Destination, label and icon for each item. `end` keeps the active state from
// bleeding into child routes.
const ITEMS = [
  { to: '/marketplace', label: 'Browse courses', Icon: BrowseIcon },
  { to: '/cart', label: 'Cart', Icon: CartIcon },
  { to: '/achievements', label: 'Achievements', Icon: TrophyIcon },
  { to: '/leaderboard', label: 'Leaderboard', Icon: LeaderboardIcon },
  { to: '/forums', label: 'Forums', Icon: ForumIcon },
  { to: '/support', label: 'Help & support', Icon: SupportIcon },
];

// --- Helpers ---
function formatMoney(cents = 0, currency = 'SGD') {
  if (!cents) return 'Free';
  return new Intl.NumberFormat('en-SG', {
    style: 'currency',
    currency: currency || 'SGD',
  }).format(cents / 100);
}

export default function DashboardSidebar() {
  const cartHoverRef = useRef(null);
  const cartPopoverRef = useRef(null);
  const [cartOpen, setCartOpen] = useState(false);
  const [cartPosition, setCartPosition] = useState({ top: 0, left: 0 });
  const [cartLoading, setCartLoading] = useState(false);
  const [cartError, setCartError] = useState('');
  const [cart, setCart] = useState({ items: [], item_count: 0, subtotal_cents: 0, currency: 'SGD' });

  const linkClass = ({ isActive }) =>
    isActive ? 'side-nav__link side-nav__link--active' : 'side-nav__link';

  // --- Cart preview ---
  async function openCartPreview() {
    const rect = cartHoverRef.current?.getBoundingClientRect();
    if (rect) {
      const width = 320;
      const gap = 12;
      const pagePad = 16;
      const canOpenRight = rect.right + gap + width <= window.innerWidth - pagePad;
      setCartPosition({
        top: Math.max(pagePad, rect.top),
        left: canOpenRight
          ? rect.right + gap
          : Math.max(pagePad, window.innerWidth - width - pagePad),
      });
    }
    setCartOpen(true);
    setCartLoading(true);
    setCartError('');
    try {
      const data = await CartApi.getCart();
      setCart(data || { items: [], item_count: 0, subtotal_cents: 0, currency: 'SGD' });
    } catch (e) {
      setCartError(e.message || 'Unable to load cart');
    } finally {
      setCartLoading(false);
    }
  }

  function closeCartPreview(event) {
    if (
      event?.relatedTarget
      && (
        cartHoverRef.current?.contains(event.relatedTarget)
        || cartPopoverRef.current?.contains(event.relatedTarget)
      )
    ) {
      return;
    }
    setCartOpen(false);
  }

  const cartPopover = cartOpen ? createPortal(
    <div
      className="cart-popover"
      role="status"
      aria-live="polite"
      ref={cartPopoverRef}
      style={{ top: cartPosition.top, left: cartPosition.left }}
      onMouseEnter={() => setCartOpen(true)}
      onMouseLeave={closeCartPreview}
      onFocus={() => setCartOpen(true)}
      onBlur={closeCartPreview}
    >
      <div className="cart-popover__head">
        <strong>Cart</strong>
        <span>{cart.item_count || 0} {(cart.item_count || 0) === 1 ? 'item' : 'items'}</span>
      </div>

      {cartLoading ? (
        <p className="cart-popover__muted">Loading…</p>
      ) : cartError ? (
        <p className="cart-popover__error">{cartError}</p>
      ) : (cart.items || []).length === 0 ? (
        <p className="cart-popover__muted">Your cart is empty.</p>
      ) : (
        <>
          <ul className="cart-popover__list">
            {(cart.items || []).slice(0, 3).map((item) => (
              <li key={item.course_id}>
                <span>{item.course_name}</span>
                <strong>{formatMoney(item.price_cents, item.currency)}</strong>
              </li>
            ))}
          </ul>
          {(cart.items || []).length > 3 && (
            <p className="cart-popover__muted">+{cart.items.length - 3} more</p>
          )}
          <div className="cart-popover__total">
            <span>Total</span>
            <strong>{formatMoney(cart.subtotal_cents, cart.currency)}</strong>
          </div>
        </>
      )}
      <NavLink to="/cart" className="cart-popover__link">View cart</NavLink>
    </div>,
    document.body,
  ) : null;

  return (
    <>
      <aside className="side-nav" aria-label="Dashboard">
        <p className="side-nav__heading">Learn</p>
        <nav className="side-nav__group">
          {ITEMS.slice(0, 1).map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className={linkClass}>
              <span className="side-nav__icon"><Icon /></span>
              {label}
            </NavLink>
          ))}

          <div
            className="side-nav__item side-nav__item--cart"
            ref={cartHoverRef}
            onMouseEnter={openCartPreview}
            onMouseLeave={closeCartPreview}
            onFocus={openCartPreview}
            onBlur={closeCartPreview}
          >
            <NavLink to="/cart" className={linkClass}>
              <span className="side-nav__icon"><CartIcon /></span>
              Cart
            </NavLink>
          </div>

          {ITEMS.slice(1).map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className={linkClass}>
              <span className="side-nav__icon"><Icon /></span>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      {cartPopover}
    </>
  );
}
