"""SQLAlchemy column types that transparently encrypt PII at rest.

Adding a new encrypted field is a one-line change: declare the column as
``EncryptedString`` and (only if you need to search/uniquely-constrain it) add a
companion blind-index column. Reads return plaintext, so most application code
is unchanged.

Example::

    from common.encrypted_types import EncryptedString

    class Purchase(Base):
        card_last4 = Column(EncryptedString)   # encrypted at rest, plaintext in Python
"""

from sqlalchemy.types import Text, TypeDecorator

from common.encryption import decrypt, encrypt


class EncryptedString(TypeDecorator):
    """A string column whose value is AES-256-GCM encrypted in the database.

    Stored as a base64 token in a TEXT column. Values are encrypted on write and
    decrypted on read automatically.

    IMPORTANT: because the ciphertext is randomized (fresh nonce per write), you
    CANNOT filter, sort, or put a UNIQUE constraint on an ``EncryptedString``
    column. For equality lookups / uniqueness, keep a separate plaintext-keyed
    blind-index column populated via ``common.encryption.blind_index``.
    """

    # TEXT because base64 ciphertext is longer than the original plaintext and
    # we don't want to track per-field length budgets.
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        # Python value -> column value (on INSERT/UPDATE and in query parameters).
        return encrypt(value)

    def process_result_value(self, value, dialect):
        # Column value -> Python value (on SELECT).
        return decrypt(value)
