import json
import os

import ollama
from dotenv import load_dotenv

from backend.models.pydantic_models import CampaignBrief, EmailVariant, EmailVariantPair

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")

SYSTEM_PROMPT = """You are an expert email marketing copywriter for Lumino, a premium skincare brand.
Lumino brand voice: clean, confident, warm but never pushy. British English spelling.

Your task: generate exactly 2 email variants (A and B) for an A/B test.

CRITICAL RULE: Only the element being tested may differ. Every other field must be word-for-word identical.

You MUST return ONLY a valid JSON object — no explanation, no markdown, no code fences. Just raw JSON.

Use this exact structure:
{
  "shared": {
    "body": "...",
    "cta": "..."
  },
  "variant_a": {
    "subject": "...",
    "body": "...",
    "cta": "..."
  },
  "variant_b": {
    "subject": "...",
    "body": "...",
    "cta": "..."
  }
}

Rules:
- subject_line test: only subject differs. Put the shared body and cta in shared block.
- body_tone test: only body differs. Put shared subject and cta in shared block.
- cta test: only cta differs. Put shared subject and body in shared block.
- Body copy: 2-3 natural sentences. Reference the product. Not salesy."""

TEST_VARIABLE_LABELS = {
    "subject_line": "subject line",
    "body_tone": "body copy and tone",
    "cta": "call-to-action text",
}


def build_user_prompt(brief: CampaignBrief) -> str:
    test_label = TEST_VARIABLE_LABELS[brief.test_variable]
    return f"""Campaign brief:
- Goal: {brief.goal}
- Campaign type: {brief.campaign_type}
- Segment: {brief.segment}
- Product: {brief.product_name} (£{brief.product_price})
- Description: {brief.product_description}
- Copy hook: {brief.product_copy_hook}
{f"- Offer: {brief.offer}" if brief.offer else ""}

Test element: {test_label}
Variant A = control (conventional baseline)
Variant B = challenger (alternative framing that may outperform A for {brief.segment})

Return ONLY the JSON object. Nothing else."""


def _assemble(data: dict, test_variable: str) -> tuple[EmailVariant, EmailVariant]:
    shared = data.get("shared", {})
    va = data["variant_a"]
    vb = data["variant_b"]

    if test_variable == "subject_line":
        body = shared.get("body") or va.get("body", "")
        cta = shared.get("cta") or va.get("cta", "")
        return (
            EmailVariant(variant_name="A", subject=va["subject"], body=body, cta=cta),
            EmailVariant(variant_name="B", subject=vb["subject"], body=body, cta=cta),
        )
    elif test_variable == "body_tone":
        subject = shared.get("subject") or va.get("subject", "")
        cta = shared.get("cta") or va.get("cta", "")
        return (
            EmailVariant(variant_name="A", subject=subject, body=va["body"], cta=cta),
            EmailVariant(variant_name="B", subject=subject, body=vb["body"], cta=cta),
        )
    else:  # cta
        subject = shared.get("subject") or va.get("subject", "")
        body = shared.get("body") or va.get("body", "")
        return (
            EmailVariant(variant_name="A", subject=subject, body=body, cta=va["cta"]),
            EmailVariant(variant_name="B", subject=subject, body=body, cta=vb["cta"]),
        )


def _shared_identical(a: EmailVariant, b: EmailVariant, test_variable: str) -> bool:
    if test_variable == "subject_line":
        return a.body == b.body and a.cta == b.cta
    elif test_variable == "body_tone":
        return a.subject == b.subject and a.cta == b.cta
    return a.subject == b.subject and a.body == b.body


def generate_variants(brief: CampaignBrief) -> EmailVariantPair:
    user_prompt = build_user_prompt(brief)
    variant_a, variant_b = None, None

    for attempt in range(3):
        extra = ""
        if attempt > 0:
            extra = f"\n\nPrevious attempt failed: shared fields were not identical. Only {TEST_VARIABLE_LABELS[brief.test_variable]} may differ. Return ONLY JSON."

        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt + extra},
            ],
            format="json",
            options={"temperature": 0.7},
        )

        raw = response.message.content.strip()

        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            continue

        try:
            variant_a, variant_b = _assemble(data, brief.test_variable)
        except (KeyError, TypeError):
            continue

        if _shared_identical(variant_a, variant_b, brief.test_variable):
            break

    if variant_a is None:
        raise RuntimeError("Content agent failed to generate valid variants after 3 attempts.")

    return EmailVariantPair(variant_a=variant_a, variant_b=variant_b)
