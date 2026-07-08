import hashlib
import os

import httpx

_HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/"

# Kept short so a slow/hung HIBP endpoint can never stall registration.
_HIBP_TIMEOUT_SECONDS = 3.0

# Opt-out (offline dev / tests): PWNED_CHECK_ENABLED=false|0|no|off skips the call.
_PWNED_DISABLED_VALUES = {"false", "0", "no", "off"}

# Checks the user password against HIBP range API using k-anonymity
def is_pwned(password: str) -> bool:
    """Return True if ``password`` appears in the HIBP breach corpus.

    Fails OPEN: returns False when the check is disabled OR when HIBP can't be
    reached (network error / timeout / non-2xx). We never want a third party's
    availability to hard-block a legitimate signup, and the local policy checks
    still apply, so we never drop below the baseline.
    """
    if os.getenv("PWNED_CHECK_ENABLED", "true").strip().lower() in _PWNED_DISABLED_VALUES:
        return False

    sha1 = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    try:
        resp = httpx.get(
            f"{_HIBP_RANGE_URL}{prefix}",
            headers={"Add-Padding": "true"},  # blunts response-size traffic analysis
            timeout=_HIBP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        return False  # fail open — local checks in validate_password_strength() still stand

    # Body is CRLF-separated "SUFFIX:COUNT" lines, all sharing our prefix.
    for line in resp.text.splitlines():
        line_suffix, _, _count = line.partition(":")
        if line_suffix.strip().upper() == suffix:
            return True
    return False
