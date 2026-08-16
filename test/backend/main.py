import os
import uuid

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

load_dotenv()

from backend.agents.content_agent import generate_variants
from backend.agents.winner_agent import evaluate_winner
from backend.db.session import get_db
from backend.db.setup_db import init_db
from backend.models.db_models import Campaign, Decision, ExperimentResult, Product, Variant
from backend.models.pydantic_models import CampaignBrief
from backend.simulation.experiment import run_experiment

app = FastAPI(title="AB Testing AI Agent", version="1.0")


@app.on_event("startup")
def startup():
    import logging
    logging.basicConfig(level=logging.INFO)
    try:
        init_db()
        logging.info("Database initialised successfully.")
    except Exception as e:
        logging.error(f"Database startup failed: {e}")
        raise


# ── POST /generate ─────────────────────────────────────────────────────────────

@app.post("/generate")
def generate(brief: CampaignBrief, db: Session = Depends(get_db)):
    pair = generate_variants(brief)

    campaign_id = str(uuid.uuid4())
    campaign = Campaign(
        campaign_id=campaign_id,
        goal=brief.goal,
        campaign_type=brief.campaign_type,
        segment=brief.segment,
        test_variable=brief.test_variable,
        statistical_method=brief.statistical_method,
        offer=brief.offer,
        product_name=brief.product_name,
    )
    db.add(campaign)

    variant_a = Variant(
        variant_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        variant_name="A",
        subject=pair.variant_a.subject,
        body=pair.variant_a.body,
        cta=pair.variant_a.cta,
    )
    variant_b = Variant(
        variant_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        variant_name="B",
        subject=pair.variant_b.subject,
        body=pair.variant_b.body,
        cta=pair.variant_b.cta,
    )
    db.add(variant_a)
    db.add(variant_b)
    db.commit()

    return {
        "campaign_id": campaign_id,
        "variant_a": {
            "variant_id": variant_a.variant_id,
            "variant_name": "A",
            "subject": variant_a.subject,
            "body": variant_a.body,
            "cta": variant_a.cta,
        },
        "variant_b": {
            "variant_id": variant_b.variant_id,
            "variant_name": "B",
            "subject": variant_b.subject,
            "body": variant_b.body,
            "cta": variant_b.cta,
        },
    }


# ── POST /run-test/{campaign_id} ───────────────────────────────────────────────

@app.post("/run-test/{campaign_id}")
def run_test(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    existing_decision = db.query(Decision).filter(Decision.campaign_id == campaign_id).first()
    if existing_decision:
        raise HTTPException(status_code=400, detail="Test already run for this campaign")

    variants = db.query(Variant).filter(Variant.campaign_id == campaign_id).all()
    variant_a = next(v for v in variants if v.variant_name == "A")
    variant_b = next(v for v in variants if v.variant_name == "B")

    results = run_experiment(
        campaign_id=campaign_id,
        segment=campaign.segment,
        test_variable=campaign.test_variable,
        variant_a_id=variant_a.variant_id,
        variant_b_id=variant_b.variant_id,
        db=db,
    )

    evaluate_winner(
        campaign_id=campaign_id,
        results=results,
        statistical_method=campaign.statistical_method,
        campaign_type=campaign.campaign_type,
        segment=campaign.segment,
        test_variable=campaign.test_variable,
        product_name=campaign.product_name,
        db=db,
    )

    return {"status": "complete", "campaign_id": campaign_id}


# ── GET /results/{campaign_id} ─────────────────────────────────────────────────

@app.get("/results/{campaign_id}")
def get_results(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    variants = db.query(Variant).filter(Variant.campaign_id == campaign_id).all()
    results = db.query(ExperimentResult).filter(ExperimentResult.campaign_id == campaign_id).all()
    decision = db.query(Decision).filter(Decision.campaign_id == campaign_id).first()

    return {
        "campaign": {
            "campaign_id": campaign.campaign_id,
            "goal": campaign.goal,
            "campaign_type": campaign.campaign_type,
            "segment": campaign.segment,
            "test_variable": campaign.test_variable,
            "statistical_method": campaign.statistical_method,
            "offer": campaign.offer,
            "product_name": campaign.product_name,
            "created_at": campaign.created_at.isoformat(),
        },
        "variants": [
            {
                "variant_name": v.variant_name,
                "subject": v.subject,
                "body": v.body,
                "cta": v.cta,
            }
            for v in sorted(variants, key=lambda x: x.variant_name)
        ],
        "results": [
            {
                "variant_name": r.variant_name,
                "sent": r.sent,
                "opens": r.opens,
                "clicks": r.clicks,
                "open_rate": r.open_rate,
                "ctr": r.ctr,
                "ctor": r.ctor,
            }
            for r in sorted(results, key=lambda x: x.variant_name)
        ],
        "decision": {
            "winning_variant": decision.winning_variant,
            "ctor_margin": decision.ctor_margin,
            "p_value": decision.p_value,
            "ci_low": decision.ci_low,
            "ci_high": decision.ci_high,
            "null_rejected": decision.null_rejected,
            "p_a_best": decision.p_a_best,
            "p_b_best": decision.p_b_best,
            "expected_uplift": decision.expected_uplift,
            "narrative": decision.narrative,
            "recommendation": decision.recommendation,
        }
        if decision
        else None,
    }


# ── GET /history ───────────────────────────────────────────────────────────────

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    campaigns = (
        db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    )

    history = []
    for campaign in campaigns:
        decision = db.query(Decision).filter(Decision.campaign_id == campaign.campaign_id).first()
        if not decision:
            continue

        results = db.query(ExperimentResult).filter(ExperimentResult.campaign_id == campaign.campaign_id).all()
        winning_ctor = None
        if decision.winning_variant in ("A", "B"):
            wr = next((r for r in results if r.variant_name == decision.winning_variant), None)
            winning_ctor = wr.ctor if wr else None

        methods_agreed = None
        if decision.null_rejected is not None and decision.p_b_best is not None:
            freq_winner = "B" if (decision.null_rejected and decision.ctor_margin > 0) else "A" if (decision.null_rejected and decision.ctor_margin < 0) else None
            bay_winner = "B" if decision.p_b_best > 0.85 else "A" if decision.p_a_best > 0.85 else None
            methods_agreed = freq_winner == bay_winner if (freq_winner and bay_winner) else None

        history.append({
            "campaign_id": campaign.campaign_id,
            "campaign_type": campaign.campaign_type,
            "segment": campaign.segment,
            "test_variable": campaign.test_variable,
            "statistical_method": campaign.statistical_method,
            "product_name": campaign.product_name,
            "winning_variant": decision.winning_variant,
            "ctor_margin": decision.ctor_margin,
            "winning_ctor": winning_ctor,
            "p_value": decision.p_value,
            "p_b_best": decision.p_b_best,
            "methods_agreed": methods_agreed,
            "created_at": campaign.created_at.isoformat(),
        })

    return history


# ── GET /products ──────────────────────────────────────────────────────────────

@app.get("/products")
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active == True).order_by(Product.sub_category, Product.name).all()
    return [
        {
            "name": p.name,
            "sub_category": p.sub_category,
            "price": p.price,
            "description": p.description,
            "copy_hook": p.copy_hook,
        }
        for p in products
    ]


@app.get("/products/{name}")
def get_product(name: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.name == name).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "name": product.name,
        "sub_category": product.sub_category,
        "price": product.price,
        "description": product.description,
        "copy_hook": product.copy_hook,
    }
