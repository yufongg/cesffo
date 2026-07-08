import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import DashboardSidebar from '../components/DashboardSidebar';
import { CartApi } from '../services/cartApi';

// --- Helpers ---
function formatMoney(cents = 0, currency = 'SGD') {
  if (!cents) return 'Free';
  return new Intl.NumberFormat('en-SG', {
    style: 'currency',
    currency: currency || 'SGD',
  }).format(cents / 100);
}

// --- Page ---
export default function Cart() {
  const navigate = useNavigate();
  const [cart, setCart] = useState({ items: [], item_count: 0, subtotal_cents: 0, currency: 'SGD' });
  const [loading, setLoading] = useState(true);
  const [busyCourseId, setBusyCourseId] = useState('');
  const [checkingOut, setCheckingOut] = useState(false);
  const [checkoutComplete, setCheckoutComplete] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [stripeUrl, setStripeUrl] = useState('');
  const [isRedirecting, setIsRedirecting] = useState(false);

  // Reset checkout state when cart is refreshed
  useEffect(() => {
    setCheckoutComplete(false);
    setSuccess('');
    setError('');
  }, [cart.items.length]);
  const [searchParams] = useSearchParams();

  const items = cart.items || [];
  const totalLabel = useMemo(
    () => formatMoney(cart.subtotal_cents, cart.currency),
    [cart.subtotal_cents, cart.currency],
  );

  // --- Data loading ---
  async function loadCart() {
    setError('');
    const data = await CartApi.getCart();
    setCart(data || { items: [], item_count: 0, subtotal_cents: 0, currency: 'SGD' });
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    CartApi.getCart()
      .then((data) => {
        if (active) setCart(data || { items: [], item_count: 0, subtotal_cents: 0, currency: 'SGD' });
      })
      .catch((e) => { if (active) setError(e.message || 'Unable to load cart'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  // --- Cart actions ---
  async function removeItem(courseId) {
    setBusyCourseId(courseId);
    setError('');
    setSuccess('');
    try {
      const data = await CartApi.removeCourse(courseId);
      setCart(data || { items: [], item_count: 0, subtotal_cents: 0, currency: 'SGD' });
    } catch (e) {
      setError(e.message || 'Unable to remove course');
    } finally {
      setBusyCourseId('');
    }
  }

  async function checkout() {
    setCheckingOut(true);
    setCheckoutComplete(false);
    setError('');
    setSuccess('');
    
    try {
      // Get cart data for the return URL
      const cartData = await CartApi.getCart();
      const returnUrl = `${window.location.origin}/cart`;
      const successUrl = `${window.location.origin}/stripe/success`;
      
      // Call checkout - backend will return the Stripe URL
      const response = await CartApi.checkout();
      
      // Backend returns a JSON object with the redirect URL (since FastAPI redirects don't work well with fetch)
      if (response?.redirect_url) {
        setIsRedirecting(true);
        // Redirect to Stripe checkout page
        window.location.href = response.redirect_url;  // + `&return_url=${encodeURIComponent(returnUrl)}`;
      } else {
        throw new Error('Unexpected checkout response');
      }
    } catch (e) {
      setIsRedirecting(false);
      setCheckingOut(false);
      setError(e.message || 'Checkout failed');
    }
  }

  // Handle being redirected back from Stripe
  useEffect(() => {
    // Check if we're being redirected back from Stripe
    const urlParams = new URLSearchParams(window.location.search);
    const returnUrl = urlParams.get('return_url');
    
    // If we have a return URL, verify payment and redirect there
    if (returnUrl) {
      // Store the return URL for verification
      window.__returnUrl = returnUrl;
    }
  }, []);

  // Verify payment after Stripe redirect
  const verifyPayment = async (sessionId) => {
    try {
      const returnUrl = window.__returnUrl || `${window.location.origin}/cart`;
      const response = await fetch('/api/v1/cart/stripe/success', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ stripe_session_id: sessionId, return_url: returnUrl }),
      });

      if (!response.ok) {
        throw new Error('Payment verification failed');
      }

      const data = await response.json();
      
      // Reload cart to update enrollment status
      await loadCart();
      setSuccess(`Payment verified! You have been enrolled in ${data.item_count} ${data.item_count === 1 ? 'course' : 'courses'}.`);
      setCheckoutComplete(true);
      
      // Redirect to return URL after a short delay
      setTimeout(() => {
        navigate(returnUrl);
      }, 2000);
    } catch (e) {
      setError(e.message || 'Unable to verify payment');
    }
  };

  // Handle being redirected back from Stripe
  useEffect(() => {
    // Check if we're being redirected back from Stripe
    const urlParams = new URLSearchParams(window.location.search);
    const stripeSessionId = urlParams.get('stripeSessionId');
    
    if (stripeSessionId) {
      // Verify the payment through the backend
      verifyPayment(stripeSessionId);
    }
  }, []);

  

  return (
    <div className="page">
      <div className="container dashboard">
        <DashboardSidebar />

        <div className="dashboard__main">
          <div className="page-header">
            <span className="eyebrow">Cart</span>
            <h1>Checkout courses</h1>
            <p className="subtitle">Review selected paid courses before mock checkout enrollment.</p>
          </div>

          {error && <p role="alert" className="alert alert--error">{error}</p>}
          {success && (
            <div className="alert alert--success">
              {success}{' '}
              <button type="button" className="link-button" onClick={() => navigate('/courses')}>
                View my courses
              </button>
            </div>
          )}

          {loading ? (
            <p style={{ color: 'var(--color-muted)' }}>Loading your cart…</p>
          ) : items.length === 0 ? (
            <div className="empty-state">
              <h3>Your cart is empty</h3>
              <p>Add paid courses from the marketplace to check out here.</p>
              <Link to="/marketplace" className="btn btn--primary">Browse courses</Link>
            </div>
          ) : (
            <div className="cart-layout">
              <section className="cart-items" aria-label="Cart items">
                {items.map((item) => (
                  <article className="cart-item" key={item.course_id}>
                    <div className="cart-item__body">
                      <h2>{item.course_name}</h2>
                      {item.instructor && <p className="course-card__meta">By {item.instructor}</p>}
                      {item.summary && <p className="course-card__summary">{item.summary}</p>}
                      <div className="course-card__tags">
                        {item.level && <span className="tag">{item.level}</span>}
                        {(item.tags || []).map((tag) => <span className="tag" key={tag}>{tag}</span>)}
                        {item.xp_reward > 0 && <span className="tag">{item.xp_reward.toLocaleString()} XP</span>}
                      </div>
                    </div>
                    <div className="cart-item__side">
                      <strong>{formatMoney(item.price_cents, item.currency)}</strong>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => removeItem(item.course_id)}
                        disabled={busyCourseId === item.course_id}
                      >
                        {busyCourseId === item.course_id ? 'Removing…' : 'Remove'}
                      </button>
                    </div>
                  </article>
                ))}
              </section>

              <aside className="cart-summary" aria-label="Order summary">
                <h2>Summary</h2>
                <div className="summary-row">
                  <span>{cart.item_count} {cart.item_count === 1 ? 'course' : 'courses'}</span>
                  <strong>{totalLabel}</strong>
                </div>
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={checkout}
                  disabled={checkingOut}
                >
                  {checkingOut ? 'Checking out…' : 'Checkout'}
                </button>
                <Link to="/marketplace" className="btn btn--ghost">Continue browsing</Link>
              </aside>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
