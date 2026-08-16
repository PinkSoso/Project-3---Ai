import random
from typing import Tuple

import numpy as np
from sqlalchemy.orm import Session

from backend.models.db_models import ExperimentResult, Subscriber

# ── Engagement rates per (segment, test_variable) ─────────────────────────────
# Based on test_cases.md expected dynamics.
# Variant B always wins — uplift magnitude reflects how strong the signal is
# for that specific segment × test variable combination.
#
# open_rate: realistic range for the segment (same for A and B — open rate is
#            driven by subject line only when test_variable != subject_line)
# ctor_a:    control CTOR range
# ctor_b:    challenger CTOR range (always higher than ctor_a)
#
# Strong uplift  (~+20–30pp CTOR): signal is clear, B clearly resonates
# Medium uplift  (~+12–18pp CTOR): meaningful but not overwhelming
# Modest uplift  (~+8–12pp CTOR):  directional, Bayesian shows moderate confidence

RATES = {
    # ── Re-engagement / Lapsed_90d ────────────────────────────────────────────
    # Personalised first-name subject >> generic product-led (strong signal)
    ("Lapsed_90d", "subject_line"): {
        "open_rate": (0.14, 0.20),
        "ctor_a": (0.10, 0.14),
        "ctor_b": (0.28, 0.36),   # +18–22pp — personalisation resonates strongly
    },
    # Warm/empathetic tone >> informational (medium signal)
    ("Lapsed_90d", "body_tone"): {
        "open_rate": (0.15, 0.20),
        "ctor_a": (0.11, 0.15),
        "ctor_b": (0.23, 0.29),   # +12–14pp
    },
    # Softer CTA "Come back home" >> "Shop now" (modest signal)
    ("Lapsed_90d", "cta"): {
        "open_rate": (0.14, 0.19),
        "ctor_a": (0.10, 0.14),
        "ctor_b": (0.18, 0.24),   # +8–10pp
    },

    # ── Welcome / New_signups ─────────────────────────────────────────────────
    # Question-led subject >> statement (medium signal)
    ("New_signups", "subject_line"): {
        "open_rate": (0.38, 0.46),
        "ctor_a": (0.14, 0.18),
        "ctor_b": (0.28, 0.36),   # +14–18pp — new users respond to uncertainty framing
    },
    # Structured/benefit-led >> warm brand story (strong signal)
    ("New_signups", "body_tone"): {
        "open_rate": (0.36, 0.44),
        "ctor_a": (0.13, 0.17),
        "ctor_b": (0.30, 0.38),   # +17–21pp — clarity wins for new users
    },
    # Specific CTA "Start with 3 products" >> "Explore the range" (medium signal)
    ("New_signups", "cta"): {
        "open_rate": (0.37, 0.45),
        "ctor_a": (0.14, 0.18),
        "ctor_b": (0.24, 0.30),   # +10–12pp
    },

    # ── Promotional / High_Value ──────────────────────────────────────────────
    # Exclusivity framing >> discount-led (strong signal for this segment)
    ("High_Value", "subject_line"): {
        "open_rate": (0.30, 0.38),
        "ctor_a": (0.18, 0.22),
        "ctor_b": (0.38, 0.46),   # +20–24pp — status > discounts for HV
    },
    # Editorial/curated >> promotional/offer-first (medium signal)
    ("High_Value", "body_tone"): {
        "open_rate": (0.29, 0.37),
        "ctor_a": (0.17, 0.22),
        "ctor_b": (0.30, 0.38),   # +13–16pp
    },
    # "Claim your access" >> "Shop the offer" (medium signal)
    ("High_Value", "cta"): {
        "open_rate": (0.30, 0.38),
        "ctor_a": (0.18, 0.23),
        "ctor_b": (0.30, 0.38),   # +12–15pp
    },

    # ── Abandoned cart / Browse_only ──────────────────────────────────────────
    # Product-led reminder >> urgency (strong signal — naming product re-anchors intent)
    ("Browse_only", "subject_line"): {
        "open_rate": (0.24, 0.32),
        "ctor_a": (0.12, 0.16),
        "ctor_b": (0.30, 0.38),   # +18–22pp
    },
    # Social proof >> scarcity framing (medium signal)
    ("Browse_only", "body_tone"): {
        "open_rate": (0.23, 0.31),
        "ctor_a": (0.12, 0.16),
        "ctor_b": (0.22, 0.28),   # +10–12pp
    },
    # Scarcity CTA "Get it before it's gone" >> "Complete your order" (modest)
    ("Browse_only", "cta"): {
        "open_rate": (0.23, 0.30),
        "ctor_a": (0.12, 0.16),
        "ctor_b": (0.20, 0.26),   # +8–10pp
    },
}


def _simulate(n: int, open_rate: float, ctor: float) -> Tuple[int, int]:
    opens = int(np.random.binomial(n, open_rate))
    clicks = int(np.random.binomial(opens, ctor)) if opens > 0 else 0
    return opens, clicks


def run_experiment(
    campaign_id: str,
    segment: str,
    test_variable: str,
    variant_a_id: str,
    variant_b_id: str,
    db: Session,
) -> list:
    rates = RATES.get((segment, test_variable))
    if not rates:
        raise ValueError(f"No simulation rates defined for ({segment}, {test_variable})")

    subscribers = (
        db.query(Subscriber)
        .filter(Subscriber.segment == segment)
        .limit(100)
        .all()
    )
    random.shuffle(subscribers)
    n_a = len(subscribers[:50])
    n_b = len(subscribers[50:100])

    open_rate = random.uniform(*rates["open_rate"])
    ctor_a = random.uniform(*rates["ctor_a"])
    ctor_b = random.uniform(*rates["ctor_b"])

    opens_a, clicks_a = _simulate(n_a, open_rate, ctor_a)
    opens_b, clicks_b = _simulate(n_b, open_rate, ctor_b)

    results = []
    for variant_id, variant_name, n, opens, clicks in [
        (variant_a_id, "A", n_a, opens_a, clicks_a),
        (variant_b_id, "B", n_b, opens_b, clicks_b),
    ]:
        actual_open_rate = round(opens / n, 4) if n else 0
        actual_ctr = round(clicks / n, 4) if n else 0
        actual_ctor = round(clicks / opens, 4) if opens else 0

        result = ExperimentResult(
            campaign_id=campaign_id,
            variant_id=variant_id,
            variant_name=variant_name,
            sent=n,
            opens=opens,
            clicks=clicks,
            open_rate=actual_open_rate,
            ctr=actual_ctr,
            ctor=actual_ctor,
        )
        db.add(result)
        results.append(result)

    db.commit()
    return results
