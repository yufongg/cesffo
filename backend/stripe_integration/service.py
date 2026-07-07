import stripe
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from model.models import User
    
def create_checkout_session(course_details: list, user: User) -> Dict[str, Any]:
    """
    Create a Stripe Checkout Session for the given courses.
    Follows Stripe's recommended patterns from https://docs.stripe.com/payments/checkout
    
    Args:
        course_details: List of dicts with keys: name, price_cents, currency, description
        user_id: UUID of the purchasing user
        
    Returns:
        Checkout session object with url
    """
    # Create Stripe Customer for the user
    customer = stripe.Customer.create(
        email=user.email,  
        metadata={
            "user_id": user.user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    )
    
    # Prepare line items for checkout using Stripe's modern format
    # Stripe's recommended approach: line_items as array of objects
    line_items = []
    for course in course_details:
        line_items.append({
            "price_data": {
                "currency": course["currency"].lower(),
                "product_data": {
                    "name": course["name"],
                    "description": course["description"] or f"Enrollment in {course['name']}",
                },
                "unit_amount": course["price_cents"],  # Amount in smallest currency unit (cents)
            },
            "quantity": 1,
        })

    course_ids_meta = ",".join([str(course.get("id", course["name"])) for course in course_details])
    base_url = get_frontend_url().rstrip('/')
    # Create checkout session with Stripe's recommended options
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        customer=customer,
        client_reference_id=str(user.user_id),
        success_url=f"{base_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}/cart",
        metadata={
            "user_id": user.user_id,
            "course_ids": ",".join([course["name"] for course in course_details]),
            "return_url": f"{base_url}/cart"
        },
        allow_promotion_codes=True,
        # Enable payment intent creation for webhook handling
        payment_intent_data={
            "metadata": {
                "user_id": str(user.user_id),
                "course_details": course_ids_meta,
            }
        },
    )
    
    return {
        "id": session.id,
        "url": session.url,
        "customer": customer.id,
    }

def verify_payment(payment_intent_id: str) -> bool:
    """
    Verify a payment was successful by checking the PaymentIntent.
    
    Args:
        payment_intent_id: Stripe PaymentIntent ID
        
    Returns:
        True if payment was successful, False otherwise
    """
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    
    return payment_intent.status in ["succeeded", "requires_capture"]

def get_customer_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve Stripe customer by user ID."""
    customers = stripe.Customer.list(metadata={"user_id": user_id})
    return customers.data[0] if customers.data else None

def get_frontend_url() -> str:
    """Get frontend URL from environment or default."""
    return os.getenv("FRONTEND_URL", "http://localhost:3000")