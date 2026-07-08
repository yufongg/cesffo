import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function StripeSuccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [stripeSessionId, setStripeSessionId] = useState('');
  const [loading, setLoading] = useState(true);
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const sessionId = searchParams.get('stripeSessionId');
    if (sessionId) {
      setStripeSessionId(sessionId);
      verifyPayment(sessionId);
    } else {
      setError('No payment session found. Please contact support.');
      setLoading(false);
    }
  }, [searchParams]);

  const verifyPayment = async (sessionId) => {
    try {
      const response = await fetch('/api/v1/stripe/verify-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ stripe_session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error('Payment verification failed');
      }

      const data = await response.json();
      if (data.valid) {
        setVerified(true);
      } else {
        setError('Payment could not be verified. Please try again.');
      }
    } catch (e) {
      setError(e.message || 'Unable to verify payment');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div className="container dashboard">
          <div className="dashboard__main" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
            <div style={{ textAlign: 'center' }}>
              <h2>Verifying Payment...</h2>
              <p>Please wait while we confirm your purchase.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <div className="container dashboard">
          <div className="dashboard__main" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
            <div style={{ textAlign: 'center' }}>
              <h2 style={{ color: '#d32f2f' }}>Payment Verification Failed</h2>
              <p className="alert alert--error">{error}</p>
              <p style={{ marginTop: '20px' }}>
                <button type="button" className="btn btn--primary" onClick={() => navigate('/cart')}>
                  Return to Cart
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (verified) {
    return (
      <div className="page">
        <div className="container dashboard">
          <div className="dashboard__main" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: '80px',
                height: '80px',
                margin: '0 auto 20px',
                borderRadius: '50%',
                background: '#4caf50',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <svg width="40" height="40" viewBox="0 0 24 24" fill="white">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
              </div>
              <h2 style={{ color: '#388e3c' }}>Payment Successful!</h2>
              <p style={{ color: '#666', marginTop: '10px' }}>
                Your payment for {stripeSessionId.substring(0, 20)}... has been verified.
              </p>
              <p style={{ marginTop: '20px', color: '#666' }}>
                You have been enrolled in your course(s). Redirecting to your courses...
              </p>
              <button 
                type="button" 
                className="btn btn--primary" 
                style={{ marginTop: '20px' }}
                onClick={() => navigate('/courses')}
              >
                View My Courses
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
