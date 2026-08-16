import os

import numpy as np
import ollama
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from backend.models.db_models import Decision, ExperimentResult
from backend.models.pydantic_models import BayesianResult

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")


def bayesian_test(a: ExperimentResult, b: ExperimentResult, n_samples: int = 50_000) -> BayesianResult:
    """Beta-Binomial model on CTOR."""
    samples_a = np.random.beta(1 + a.clicks, 1 + (a.opens - a.clicks), n_samples)
    samples_b = np.random.beta(1 + b.clicks, 1 + (b.opens - b.clicks), n_samples)

    p_b_best = float(np.mean(samples_b > samples_a))
    return BayesianResult(
        p_a_best=round(1.0 - p_b_best, 4),
        p_b_best=round(p_b_best, 4),
        expected_uplift=round(float(np.mean(samples_b - samples_a)), 4),
    )


def determine_winner(ctor_margin: float, bay: BayesianResult) -> str:
    if bay.p_b_best > 0.85:
        return "B"
    if bay.p_a_best > 0.85:
        return "A"
    return "No significant winner"


def generate_narrative(
    a: ExperimentResult,
    b: ExperimentResult,
    bay: BayesianResult,
    winner: str,
    campaign_type: str,
    segment: str,
    test_variable: str,
    product_name: str,
) -> tuple[str, str]:
    prompt = f"""Analyse this A/B email test for Lumino skincare.

Campaign: {campaign_type} | Segment: {segment} | Tested: {test_variable.replace("_", " ")} | Product: {product_name}

Variant A — sent {a.sent}, opens {a.opens} ({a.open_rate:.1%}), clicks {a.clicks}, CTOR {a.ctor:.1%}
Variant B — sent {b.sent}, opens {b.opens} ({b.open_rate:.1%}), clicks {b.clicks}, CTOR {b.ctor:.1%}
Bayesian: P(B best)={bay.p_b_best:.1%}, expected CTOR uplift={bay.expected_uplift:+.1%}
Winner: Variant {winner}

Write exactly two things:
NARRATIVE: [2-3 sentences: what won, by how much, and why it resonated with the {segment} segment. Use plain business language, no stats jargon.]
RECOMMENDATION: [1-2 sentences: what to test next or how to apply this result.]"""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.5},
    )

    raw = response.message.content.strip()
    narrative, recommendation = raw, "Continue testing additional elements."

    if "NARRATIVE:" in raw and "RECOMMENDATION:" in raw:
        parts = raw.split("RECOMMENDATION:")
        narrative = parts[0].replace("NARRATIVE:", "").strip()
        recommendation = parts[1].strip()

    return narrative, recommendation


def evaluate_winner(
    campaign_id: str,
    results: list,
    statistical_method: str,
    campaign_type: str,
    segment: str,
    test_variable: str,
    product_name: str,
    db: Session,
) -> Decision:
    result_a = next(r for r in results if r.variant_name == "A")
    result_b = next(r for r in results if r.variant_name == "B")

    bay = bayesian_test(result_a, result_b)
    ctor_margin = round(result_b.ctor - result_a.ctor, 4)
    winner = determine_winner(ctor_margin, bay)

    narrative, recommendation = generate_narrative(
        result_a, result_b, bay,
        winner, campaign_type, segment, test_variable, product_name,
    )

    decision = Decision(
        campaign_id=campaign_id,
        winning_variant=winner,
        ctor_margin=ctor_margin,
        p_value=None,
        ci_low=None,
        ci_high=None,
        null_rejected=None,
        p_a_best=bay.p_a_best,
        p_b_best=bay.p_b_best,
        expected_uplift=bay.expected_uplift,
        narrative=narrative,
        recommendation=recommendation,
    )
    db.add(decision)
    db.commit()
    return decision
