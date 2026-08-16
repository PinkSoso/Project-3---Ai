import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    goal = Column(String)
    campaign_type = Column(String)
    segment = Column(String)
    test_variable = Column(String)
    statistical_method = Column(String)
    offer = Column(String, nullable=True)
    product_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    variants = relationship("Variant", back_populates="campaign")
    results = relationship("ExperimentResult", back_populates="campaign")
    decision = relationship("Decision", back_populates="campaign", uselist=False)


class Variant(Base):
    __tablename__ = "variants"

    variant_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"))
    variant_name = Column(String)  # "A" or "B"
    subject = Column(String)
    body = Column(String)
    cta = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="variants")
    results = relationship("ExperimentResult", back_populates="variant")


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    result_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"))
    variant_id = Column(String, ForeignKey("variants.variant_id"))
    variant_name = Column(String)
    sent = Column(Integer)
    opens = Column(Integer)
    clicks = Column(Integer)
    open_rate = Column(Float)
    ctr = Column(Float)
    ctor = Column(Float)

    campaign = relationship("Campaign", back_populates="results")
    variant = relationship("Variant", back_populates="results")


class Decision(Base):
    __tablename__ = "decisions"

    decision_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), unique=True)
    winning_variant = Column(String)
    ctor_margin = Column(Float)
    p_value = Column(Float, nullable=True)
    ci_low = Column(Float, nullable=True)
    ci_high = Column(Float, nullable=True)
    null_rejected = Column(Boolean, nullable=True)
    p_a_best = Column(Float, nullable=True)
    p_b_best = Column(Float, nullable=True)
    expected_uplift = Column(Float, nullable=True)
    narrative = Column(String)
    recommendation = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="decision")


class Subscriber(Base):
    __tablename__ = "subscribers"

    subscriber_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String)
    first_name = Column(String)
    segment = Column(String)
    last_purchase_date = Column(DateTime, nullable=True)
    total_spend = Column(Float, default=0.0)
    browse_product = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    name = Column(String, primary_key=True)
    sub_category = Column(String)
    price = Column(Float)
    description = Column(String)
    copy_hook = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
