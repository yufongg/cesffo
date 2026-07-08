from enum import StrEnum

class PaymentStatus(StrEnum):
    PAID  = "paid"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"