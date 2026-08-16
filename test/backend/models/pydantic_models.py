from pydantic import BaseModel
from typing import Optional, Literal


class CampaignBrief(BaseModel):
    goal: str
    campaign_type: Literal["Re-engagement", "Welcome", "Promotional", "Abandoned cart"]
    segment: Literal["Lapsed_90d", "New_signups", "High_Value", "Browse_only"]
    test_variable: Literal["subject_line", "body_tone", "cta"]
    statistical_method: Literal["Bayesian"]
    offer: Optional[str] = None
    product_name: str
    product_description: str
    product_price: float
    product_copy_hook: str


class EmailVariant(BaseModel):
    variant_name: Literal["A", "B"]
    subject: str
    body: str
    cta: str


class EmailVariantPair(BaseModel):
    variant_a: EmailVariant
    variant_b: EmailVariant


class BayesianResult(BaseModel):
    p_a_best: float
    p_b_best: float
    expected_uplift: float
