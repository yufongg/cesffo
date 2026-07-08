import json
import os
import stripe
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select

from model.models import CourseEnrollment
from model.constants import PaymentStatus
# from core.security import get_current_user
from db.db import get_db_session

router = APIRouter()

IS_PRODUCTION = os.getenv("APP_ENV", "development") == "production"

@router.post("/stripe/webhook", status_code=200)
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    Verifies signature and processes payment events.
    """
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    #! Fail closed in production: an unsigned webhook must never be able to
    #! mutate payment state (e.g. a forged checkout.session.completed marking
    #! an unpaid enrollment as paid). The unverified path is dev-only.
    if IS_PRODUCTION and not endpoint_secret:
        raise HTTPException(status_code=500, detail="Webhook not configured")
    raw_payload = await request.body()
    payload = raw_payload.decode('utf-8')

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as e:
        print('Webhook error while parsing basic request.' + str(e))
        return {'success': False}
    
    if endpoint_secret:
        # Only verify the event if there is an endpoint secret defined
        # Otherwise use the basic event deserialized with json
        sig_header = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                raw_payload, sig_header, endpoint_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            # ValueError covers a missing/garbled Stripe-Signature header.
            print('Webhook signature verification failed.' + str(e))
            return {'success': False}

    # Handle the event
    if event and event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']  # contains a stripe.PaymentIntent
        print('Payment for {} succeeded'.format(payment_intent['amount']))
        await _handle_payment_succeeded(event['data'], request)
    elif event['type'] == 'payment_method.attached':
        payment_method = event['data']['object']  # contains a stripe.PaymentMethod
        print('Payment method attached: {}'.format(payment_method['id']))
        # await _handle_payment_method_attached(payment_method)
    elif event['type'] == 'checkout.session.completed':
        data = event['data']
        print(request, data)
        await _handle_checkout_completed(data, request)
    elif event['type'] == 'payment_intent.payment_failed':
        data = event['data']
        print(data)
        await _handle_payment_failed(data, request)
    elif event['type'] == 'checkout.session.expired':
        await _handle_checkout_expired(event['data'], request)
    else:
        # Unexpected event type
        # print('Unhandled event type {}'.format(event['type']))

        return {'success': False}
async def _handle_checkout_completed(data: dict, request: Request):
    """
    Handle checkout.session.completed event.
    Finds pre-staged enrollments by Stripe Checkout Session ID and marks them paid.
    """
    stripe_session = data["object"]
    session_id = stripe_session.id  
    
    with get_db_session() as db_session:
        # Look up all pending records matching this exact checkout session ID
        existing_enrollments = db_session.scalars(
            select(CourseEnrollment).where(
                CourseEnrollment.stripe_payment_id == session_id
            )
        ).all()
        
        if not existing_enrollments:
            print(f" Warning: No pending enrollments found for session ID {session_id}")
            raise HTTPException(status_code=404, detail="Enrollments not found")
        
        # Update your pre-staged entries
        for enrollment in existing_enrollments:
            enrollment.payment_status = PaymentStatus.PAID
            enrollment.amount_paid = getattr(stripe_session, "amount_total", enrollment.amount_paid)
            enrollment.currency = getattr(stripe_session, "currency", "sgd").upper()
            
            payment_intent_id = getattr(stripe_session, "payment_intent", None)
            if payment_intent_id:
                enrollment.stripe_payment_id = payment_intent_id
        
        db_session.flush()


async def _handle_payment_succeeded(data: dict, request: Request):
    """
    Handle payment_intent.succeeded event.
    Finds enrollments matching the underlying PaymentIntent ID.
    """
    payment_intent = data["object"]
    pi_id = payment_intent.id  # e.g., pi_...

    with get_db_session() as db_session:
        # Look up records matching this specific payment intent identifier
        existing_enrollments = db_session.scalars(
            select(CourseEnrollment).where(
                CourseEnrollment.stripe_payment_id == pi_id
            )
        ).all()
        
        # Fallback: if checkout.session.completed handled it first, it swapped IDs.
        # If no entries are found, they might still bear the original session_id wrapper.
        if not existing_enrollments:
            metadata = getattr(payment_intent, "metadata", {}) or {}
            user_id = metadata.get("user_id")
            
            # If metadata exists, run a structural fallback check to prevent data gaps
            if user_id:
                existing_enrollments = db_session.scalars(
                    select(CourseEnrollment).where(
                        CourseEnrollment.student_id == user_id,
                        CourseEnrollment.payment_status == PaymentStatus.PENDING
                    )
                ).all()

        for enrollment in existing_enrollments:
            enrollment.payment_status = PaymentStatus.PAID
            enrollment.stripe_payment_id = pi_id
            enrollment.amount_paid = payment_intent.amount
            enrollment.currency = payment_intent.currency.upper()
            
        db_session.flush()


async def _handle_checkout_expired(data: dict, request: Request):
    """
    Handle checkout.session.expired event (the user abandoned the Checkout
    page). Marks the pre-staged PENDING rows failed so the courses can be
    added to the cart and purchased again.
    """
    stripe_session = data["object"]
    session_id = stripe_session.id

    with get_db_session() as db_session:
        existing_enrollments = db_session.scalars(
            select(CourseEnrollment).where(
                CourseEnrollment.stripe_payment_id == session_id,
                CourseEnrollment.payment_status == PaymentStatus.PENDING,
            )
        ).all()

        for enrollment in existing_enrollments:
            enrollment.payment_status = PaymentStatus.FAILED

        db_session.flush()


async def _handle_payment_failed(data: dict, request: Request):
    """
    Handle payment_intent.payment_failed event.
    Marks enrollments as failed based on the PaymentIntent ID.
    """
    payment_intent = data["object"]
    pi_id = payment_intent.id  

    with get_db_session() as db_session:
        # Look up records matching this failed payment intent identifier
        existing_enrollments = db_session.scalars(
            select(CourseEnrollment).where(
                CourseEnrollment.stripe_payment_id == pi_id
            )
        ).all()
        
        for enrollment in existing_enrollments:
            enrollment.payment_status = PaymentStatus.FAILED
            
        db_session.flush()