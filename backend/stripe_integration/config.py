import os
import stripe
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_stripe_api_mode() -> str:
    """Return Stripe API mode (test or live)."""
    return os.getenv("STRIPE_MODE", "test")

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET") 
stripe.api_version = "2024-06-20"  # Use latest stable version

def get_stripe_publishable_key() -> str:
    """Return Stripe publishable key for frontend use."""
    return os.getenv("STRIPE_PUBLIC", "")

def get_stripe_webhook_secret() -> str:
    """Return webhook signing secret."""
    return os.getenv("STRIPE_WEBHOOK_SECRET", "")

def is_stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return (
        os.getenv("STRIPE_SECRET") and
        os.getenv("STRIPE_PUBLIC") and
        os.getenv("STRIPE_WEBHOOK_SECRET")
    )

def init_stripe():
    
    # Configure Stripe
    stripe_api_key = os.getenv("STRIPE_SECRET") 
    client = stripe.StripeClient(stripe_api_key)

    return client