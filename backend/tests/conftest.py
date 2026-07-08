"""Shared pytest configuration.

Disables the HIBP breached-password network check for the whole suite so tests
stay hermetic (no outbound calls) and deterministic — otherwise registration /
password-change tests using realistic passwords would hit the live HIBP range
API and could fail if a chosen literal happens to appear in the breach corpus.
is_pwned() reads PWNED_CHECK_ENABLED at call time, so setting it here covers it.
"""

import os

os.environ.setdefault("PWNED_CHECK_ENABLED", "false")
