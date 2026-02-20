"""Monetization hooks (feature gating + Stripe scaffold)."""
from __future__ import annotations

import os
from datetime import date

from backend.utils import can_use_pro_feature


class FeatureGate:
    def __init__(self, free_daily_limit: int = 5) -> None:
        self.free_daily_limit = free_daily_limit

    def can_explain(self, attempts_today: int) -> tuple[bool, str]:
        if can_use_pro_feature():
            return True, "Pro mode enabled"
        if attempts_today >= self.free_daily_limit:
            return False, "Free limit reached. Upgrade to Pro for unlimited explanations."
        return True, "Free mode"


def create_stripe_checkout_session_stub(price_id: str, success_url: str, cancel_url: str) -> dict:
    return {
        "status": "stub",
        "message": "Integrate with Stripe SDK in production.",
        "price_id": price_id,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "env_has_key": bool(os.getenv("STRIPE_SECRET_KEY")),
        "requested_on": str(date.today()),
    }
