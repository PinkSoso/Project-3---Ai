import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Segment → price range guide (for filtering suggestions) ───────────────────
SEGMENT_PRICE_RANGE = {
    "Lapsed_90d":  (28, 75),
    "New_signups": (12, 25),
    "High_Value":  (80, 200),
    "Browse_only": (25, 70),
}

SEGMENT_TO_CAMPAIGN = {
    "Lapsed_90d":  "Re-engagement",
    "New_signups": "Welcome",
    "High_Value":  "Promotional",
    "Browse_only": "Abandoned cart",
}

TEST_VAR_LABELS = {
    "subject_line": "Subject line",
    "body_tone":    "Body / tone",
    "cta":          "CTA",
}

SEGMENT_LABELS = {
    "Lapsed_90d":  "Lapsed 90d (100 subs)",
    "New_signups": "New signups (100 subs)",
    "High_Value":  "High Value (100 subs)",
    "Browse_only": "Browse only (100 subs)",
}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Lumino · AB Testing Agent",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* hide Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 900px; }

  /* cards */
  .card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
  }
  .card-selected {
    background: #f5f3ff;
    border: 2px solid #7c3aed;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
  }

  /* stat boxes */
  .stat-box {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
  }
  .stat-label { font-size: 0.75rem; color: #6b7280; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
  .stat-value { font-size: 1.5rem; font-weight: 700; color: #111827; margin-top: 0.2rem; }
  .stat-value-green { font-size: 1.5rem; font-weight: 700; color: #059669; margin-top: 0.2rem; }

  /* badges */
  .badge-control  { background:#e0e7ff; color:#3730a3; font-size:0.72rem; font-weight:600; padding:2px 10px; border-radius:99px; }
  .badge-challenger { background:#fef3c7; color:#92400e; font-size:0.72rem; font-weight:600; padding:2px 10px; border-radius:99px; }
  .badge-winner   { background:#d1fae5; color:#065f46; font-size:0.72rem; font-weight:600; padding:2px 10px; border-radius:99px; }
  .badge-method   { background:#ede9fe; color:#5b21b6; font-size:0.72rem; font-weight:600; padding:2px 10px; border-radius:99px; }
  .badge-neutral  { background:#f3f4f6; color:#374151; font-size:0.72rem; font-weight:600; padding:2px 10px; border-radius:99px; }

  /* callout */
  .callout {
    background: #f0fdf4;
    border-left: 4px solid #22c55e;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    color: #166534;
    margin-bottom: 1rem;
  }
  .callout-purple {
    background: #f5f3ff;
    border-left: 4px solid #7c3aed;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    color: #4c1d95;
    margin-bottom: 1rem;
  }

  /* narrative box */
  .narrative {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    font-size: 0.92rem;
    color: #374151;
    line-height: 1.7;
  }

  /* section heading */
  .section-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b7280;
    margin-bottom: 0.5rem;
  }

  /* product pill */
  .product-pill {
    display: inline-block;
    background: #ede9fe;
    color: #5b21b6;
    border-radius: 99px;
    padding: 4px 14px;
    font-size: 0.82rem;
    font-weight: 500;
    margin-top: 0.4rem;
  }

  /* divider */
  hr { border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0; }

  /* note text */
  .note { font-size: 0.80rem; color: #9ca3af; margin-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "screen": 1,
        "campaign_id": None,
        "variants": None,
        "brief": None,
        "results": None,
        "product_cache": {},
        "all_products": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ── Helpers ────────────────────────────────────────────────────────────────────
def go(screen: int):
    st.session_state.screen = screen
    st.rerun()


def fetch_all_products() -> list:
    if "all_products" in st.session_state and st.session_state.all_products:
        return st.session_state.all_products
    try:
        r = requests.get(f"{BACKEND_URL}/products", timeout=5)
        if r.status_code == 200:
            st.session_state.all_products = r.json()
            return st.session_state.all_products
    except Exception:
        pass
    return []


def fetch_product(name: str) -> dict:
    if name in st.session_state.product_cache:
        return st.session_state.product_cache[name]
    try:
        r = requests.get(f"{BACKEND_URL}/products/{requests.utils.quote(name)}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            st.session_state.product_cache[name] = data
            return data
    except Exception:
        pass
    return {}


def api_post(path: str, payload: dict = None) -> dict | None:
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=90)
        if r.status_code == 200:
            return r.json()
        st.error(f"API error {r.status_code}: {r.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running on port 8000.")
    return None


def api_get(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=15)
        if r.status_code == 200:
            return r.json()
        st.error(f"API error {r.status_code}: {r.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running on port 8000.")
    return None


def fmt_pct(v) -> str:
    return f"{v:.1%}" if v is not None else "—"


def fmt_p(v) -> str:
    return f"{v:.4f}" if v is not None else "—"


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Campaign brief
# ══════════════════════════════════════════════════════════════════════════════
def screen_1():
    st.markdown("## New A/B test")
    st.markdown(
        "<p style='color:#6b7280;margin-bottom:1.5rem'>Set up your campaign, choose one element to test, and select your statistical approach.</p>",
        unsafe_allow_html=True,
    )

    # ── Goal ──────────────────────────────────────────────────────────────────
    goal = st.text_area(
        "What is this campaign about?",
        placeholder="e.g. Re-engagement email for customers who haven't bought in 90 days — homeware focus, 15% off",
        height=90,
    )

    # ── Campaign type + Segment ────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        segment = st.selectbox(
            "Target segment",
            options=list(SEGMENT_LABELS.keys()),
            format_func=lambda s: SEGMENT_LABELS[s],
        )
    with col2:
        campaign_type = SEGMENT_TO_CAMPAIGN[segment]
        st.text_input("Campaign type", value=campaign_type, disabled=True)

    # ── Element to test ────────────────────────────────────────────────────────
    st.markdown("<div class='section-label' style='margin-top:1rem'>What do you want to test? Choose one element — everything else stays identical in both variants.</div>", unsafe_allow_html=True)

    test_options = list(TEST_VAR_LABELS.keys())
    test_descriptions = {
        "subject_line": "Two subject lines. Body and CTA identical in both.",
        "body_tone":    "Two content approaches. Subject and CTA identical in both.",
        "cta":          "Two call-to-action texts. Subject and body identical in both.",
    }

    if "test_variable" not in st.session_state:
        st.session_state.test_variable = "subject_line"

    cols = st.columns(3)
    for i, key in enumerate(test_options):
        with cols[i]:
            selected = st.session_state.test_variable == key
            css_class = "card-selected" if selected else "card"
            st.markdown(
                f"<div class='{css_class}' style='cursor:pointer'>"
                f"<b style='color:{'#7c3aed' if selected else '#111827'}'>{TEST_VAR_LABELS[key]}</b>"
                f"<p style='font-size:0.82rem;color:#6b7280;margin-top:0.3rem'>{test_descriptions[key]}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"Select {TEST_VAR_LABELS[key]}", key=f"tv_{key}", use_container_width=True):
                st.session_state.test_variable = key
                st.rerun()

    test_variable = st.session_state.test_variable

    # ── Product selector ───────────────────────────────────────────────────────
    st.markdown("<div class='section-label' style='margin-top:0.5rem'>Product to feature in this campaign</div>", unsafe_allow_html=True)

    all_products = fetch_all_products()
    price_min, price_max = SEGMENT_PRICE_RANGE.get(segment, (0, 999))
    suggested = [p for p in all_products if price_min <= p["price"] <= price_max]
    other = [p for p in all_products if not (price_min <= p["price"] <= price_max)]

    product_options = (
        ["── Suggested for this segment ──"] +
        [p["name"] for p in suggested] +
        (["── Other products ──"] + [p["name"] for p in other] if other else [])
    )
    separators = {"── Suggested for this segment ──", "── Other products ──"}

    selected_product = st.selectbox(
        "Select product",
        options=product_options,
        label_visibility="collapsed",
    )

    if selected_product in separators:
        st.warning("Please select a product, not a category header.")
        product_name = ""
        product = {}
    else:
        product_name = selected_product
        product = fetch_product(product_name) if product_name else {}
        if product:
            st.markdown(
                f"<div class='callout-purple'>"
                f"<b>{product_name}</b> &middot; £{product.get('price', '')}"
                f"<br><span style='opacity:0.8'>{product.get('copy_hook', '')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )


    # ── Offer ──────────────────────────────────────────────────────────────────
    offer = st.text_input("Discount / offer (optional)", placeholder="e.g. 15% off")

    # ── Generate ───────────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    _, btn_col = st.columns([3, 1])
    with btn_col:
        generate_clicked = st.button("Generate variants →", type="primary", use_container_width=True)

    if generate_clicked:
        if not goal.strip():
            st.warning("Please enter a campaign goal.")
            return

        if not product_name or product_name in separators:
            st.warning("Please select a product.")
            return

        if not product:
            st.error(f"Could not load product details for '{product_name}'. Make sure the backend is running.")
            return

        brief_payload = {
            "goal": goal.strip(),
            "campaign_type": campaign_type,
            "segment": segment,
            "test_variable": test_variable,
            "statistical_method": "Bayesian",
            "offer": offer.strip() or None,
            "product_name": product_name,
            "product_description": product.get("description", ""),
            "product_price": product.get("price", 0),
            "product_copy_hook": product.get("copy_hook", ""),
        }

        with st.spinner("Generating variants with Claude…"):
            data = api_post("/generate", brief_payload)

        if data:
            st.session_state.campaign_id = data["campaign_id"]
            st.session_state.variants = data
            st.session_state.brief = brief_payload
            go(2)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — Review variants
# ══════════════════════════════════════════════════════════════════════════════
def screen_2():
    brief = st.session_state.brief
    variants = st.session_state.variants
    test_variable = brief["test_variable"]
    tv_label = TEST_VAR_LABELS[test_variable]

    st.markdown("## Review variants")
    st.markdown(
        f"<p style='color:#6b7280;margin-bottom:1rem'>Testing: <b>{tv_label}</b> · body copy and CTA are identical in both variants.</p>",
        unsafe_allow_html=True,
    )

    # Shared fields callout
    va = variants["variant_a"]
    vb = variants["variant_b"]

    if test_variable == "subject_line":
        held = f"<b>Body</b> — identical &middot; <b>CTA</b> — '{va['cta']}' &middot; <b>From name</b> — Lumino"
        bottom_note = "The body and CTA are identical — any difference in results is attributable solely to the subject line."
    elif test_variable == "body_tone":
        held = f"<b>Subject</b> — '{va['subject']}' &middot; <b>CTA</b> — '{va['cta']}' &middot; <b>From name</b> — Lumino"
        bottom_note = "The subject line and CTA are identical — any difference in results is attributable solely to the body copy."
    else:
        held = f"<b>Subject</b> — '{va['subject']}' &middot; <b>Body</b> — identical &middot; <b>From name</b> — Lumino"
        bottom_note = "The subject line and body are identical — any difference in results is attributable solely to the CTA."

    st.markdown(f"<div class='callout'>{held}</div>", unsafe_allow_html=True)

    # Side-by-side variants
    col_a, col_b = st.columns(2)

    def render_variant(col, variant, badge_html, badge_class):
        with col:
            st.markdown(
                f"<div class='card'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem'>"
                f"<span style='font-weight:600;color:#111827'>Variant {variant['variant_name']}</span>"
                f"<span class='{badge_class}'>{badge_html}</span>"
                f"</div>"
                f"<div class='section-label'>Subject</div>"
                f"<p style='font-weight:600;color:#111827;margin:0 0 0.8rem'>{variant['subject']}</p>"
                f"<div class='section-label'>Body</div>"
                f"<p style='font-size:0.88rem;color:#374151;line-height:1.6;margin:0 0 0.8rem'>{variant['body']}</p>"
                f"<div class='section-label'>CTA</div>"
                f"<div style='display:inline-block;background:#7c3aed;color:white;border-radius:6px;padding:6px 16px;font-size:0.85rem;font-weight:500'>{variant['cta']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    render_variant(col_a, va, "Control", "badge-control")
    render_variant(col_b, vb, "Challenger", "badge-challenger")

    st.markdown(f"<p class='note'>{bottom_note}</p>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    btn_left, _, btn_right = st.columns([1, 2, 1])
    with btn_left:
        if st.button("← Edit brief", use_container_width=True):
            go(1)
    with btn_right:
        if st.button("Run test →", type="primary", use_container_width=True):
            with st.spinner("Running simulation and evaluating winner…"):
                result = api_post(f"/run-test/{st.session_state.campaign_id}")
            if result:
                data = api_get(f"/results/{st.session_state.campaign_id}")
                if data:
                    st.session_state.results = data
                    go(3)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — Results
# ══════════════════════════════════════════════════════════════════════════════
def screen_3():
    data = st.session_state.results
    if not data:
        st.error("No results found.")
        return

    campaign = data["campaign"]
    variants = {v["variant_name"]: v for v in data["variants"]}
    results = {r["variant_name"]: r for r in data["results"]}
    decision = data["decision"]

    ra = results.get("A", {})
    rb = results.get("B", {})
    va = variants.get("A", {})
    vb = variants.get("B", {})

    winner = decision["winning_variant"]
    ctor_margin = decision["ctor_margin"]

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("## Results")
    st.markdown(
        f"<p style='color:#6b7280;margin-bottom:1.2rem'>"
        f"{campaign['campaign_type']} · {campaign['segment']} · "
        f"{TEST_VAR_LABELS.get(campaign['test_variable'], campaign['test_variable'])} test · "
        f"50 subscribers per group"
        f"</p>",
        unsafe_allow_html=True,
    )

    # ── Stat boxes ────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    winner_display = f"Variant {winner}" if winner in ("A", "B") else "No clear winner"
    margin_display = f"{ctor_margin:+.1%}" if ctor_margin is not None else "—"
    p_b = decision.get("p_b_best")
    p_a = decision.get("p_a_best")

    with c1:
        color = "#059669" if winner in ("A", "B") else "#6b7280"
        st.markdown(
            f"<div class='stat-box'><div class='stat-label'>Winner</div>"
            f"<div class='stat-value' style='color:{color};font-size:1.2rem'>{winner_display}</div></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='stat-box'><div class='stat-label'>CTOR margin</div>"
            f"<div class='stat-value-green'>{margin_display}</div></div>",
            unsafe_allow_html=True,
        )
    with c3:
        p_b_display = f"{p_b:.1%}" if p_b is not None else "—"
        st.markdown(
            f"<div class='stat-box'><div class='stat-label'>Confidence B wins</div>"
            f"<div class='stat-value' style='font-size:1.2rem'>{p_b_display}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Variant comparison table ───────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    def render_result_card(col, variant, result, is_winner):
        v_name = variant.get("variant_name", "")
        badge = "<span class='badge-winner'>Winner</span>" if is_winner else ""
        border = "border: 2px solid #059669;" if is_winner else ""
        with col:
            st.markdown(
                f"<div class='card' style='{border}'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem'>"
                f"<span style='font-weight:600'>Variant {v_name} {'(Control)' if v_name=='A' else '(Challenger)'}</span>"
                f"{badge}"
                f"</div>"
                f"<div class='section-label'>Subject</div>"
                f"<p style='font-weight:500;margin:0 0 0.8rem;font-size:0.9rem'>{variant.get('subject','')}</p>"
                f"<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;text-align:center'>"
                f"<div><div class='section-label'>Open rate</div><b style='color:{'#059669' if is_winner else '#111827'}'>{fmt_pct(result.get('open_rate'))}</b></div>"
                f"<div><div class='section-label'>CTOR</div><b style='font-size:1.1rem;color:{'#059669' if is_winner else '#111827'}'>{fmt_pct(result.get('ctor'))}</b></div>"
                f"<div><div class='section-label'>Clicks</div><b style='color:{'#059669' if is_winner else '#111827'}'>{result.get('clicks','—')}</b></div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    render_result_card(col_a, va, ra, winner == "A")
    render_result_card(col_b, vb, rb, winner == "B")

    # ── Bayesian panel ─────────────────────────────────────────────────────────
    uplift = decision.get("expected_uplift")
    confidence_label = "High confidence" if (p_b and p_b > 0.90) else "Moderate confidence"
    st.markdown(
        f"<div class='card'>"
        f"<div style='display:flex;justify-content:space-between;margin-bottom:0.6rem'>"
        f"<b>Bayesian analysis</b>"
        f"<span class='badge-method'>{confidence_label}</span>"
        f"</div>"
        f"<table style='width:100%;font-size:0.88rem;border-collapse:collapse'>"
        f"<tr><td style='color:#6b7280;padding:4px 0'>Chance Variant A wins</td><td style='text-align:right;font-weight:600'>{fmt_pct(p_a)}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:4px 0'>Chance Variant B wins</td><td style='text-align:right;font-weight:600'>{fmt_pct(p_b)}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:4px 0'>Expected CTOR uplift</td><td style='text-align:right;font-weight:600'>{fmt_pct(uplift)}</td></tr>"
        f"</table>"
        f"<p style='font-size:0.80rem;color:#6b7280;margin-top:0.6rem'>"
        f"Based on {fmt_pct(p_b)} probability that Variant B has a higher true click-to-open rate."
        f"</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── AI narrative ───────────────────────────────────────────────────────────
    st.markdown("<div class='section-label' style='margin-top:0.5rem'>AI analysis</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='narrative'>"
        f"<p style='margin:0 0 0.8rem'>{decision.get('narrative','')}</p>"
        f"<p style='margin:0;color:#7c3aed;font-weight:500'>→ {decision.get('recommendation','')}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Tags ──────────────────────────────────────────────────────────────────
    tv = TEST_VAR_LABELS.get(campaign["test_variable"], campaign["test_variable"])
    st.markdown(
        f"<div style='margin-top:1rem'>"
        f"<span class='badge-neutral'>Tested: {tv} only</span> &nbsp;"
        f"<span class='badge-neutral'>Segment: {campaign['segment']}</span> &nbsp;"
        f"<span class='badge-neutral'>Bayesian analysis</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    btn_l, _, btn_r = st.columns([1, 2, 1])
    with btn_l:
        if st.button("View history", use_container_width=True):
            go(4)
    with btn_r:
        if st.button("New test →", type="primary", use_container_width=True):
            st.session_state.campaign_id = None
            st.session_state.variants = None
            st.session_state.brief = None
            st.session_state.results = None
            go(1)


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — Test history
# ══════════════════════════════════════════════════════════════════════════════
def screen_4():
    st.markdown("## Test history")
    st.markdown(
        "<p style='color:#6b7280;margin-bottom:1.5rem'>All completed A/B tests — variable tested, winner, and statistical method used.</p>",
        unsafe_allow_html=True,
    )

    history = api_get("/history")
    if history is None:
        return
    if not history:
        st.info("No completed tests yet. Run your first test to see results here.")
        if st.button("New test →", type="primary"):
            go(1)
        return

    # ── Summary stats ──────────────────────────────────────────────────────────
    total = len(history)
    agreed = sum(1 for h in history if h.get("methods_agreed") is True)
    agreed_str = f"{agreed}/{total}" if total > 0 else "—"
    ctors = [h["winning_ctor"] for h in history if h.get("winning_ctor") is not None]
    avg_ctor = sum(ctors) / len(ctors) if ctors else None

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f"<div class='stat-box'><div class='stat-label'>Tests run</div><div class='stat-value'>{total}</div></div>", unsafe_allow_html=True)
    with s2:
        st.markdown(f"<div class='stat-box'><div class='stat-label'>Both methods agreed</div><div class='stat-value'>{agreed_str}</div></div>", unsafe_allow_html=True)
    with s3:
        st.markdown(f"<div class='stat-box'><div class='stat-label'>Avg winning CTOR</div><div class='stat-value'>{fmt_pct(avg_ctor)}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Filters ────────────────────────────────────────────────────────────────
    f1, f2, f3, f4 = st.columns(4)
    campaign_types = ["All"] + sorted(set(h["campaign_type"] for h in history))
    segments = ["All"] + sorted(set(h["segment"] for h in history))
    test_vars = ["All"] + sorted(set(h["test_variable"] for h in history))
    methods = ["All"] + sorted(set(h["statistical_method"] for h in history))

    with f1:
        ft_campaign = st.selectbox("Campaign type", campaign_types, key="hist_ft_campaign")
    with f2:
        ft_segment = st.selectbox("Segment", segments, key="hist_ft_segment")
    with f3:
        ft_var = st.selectbox("Element tested", test_vars, key="hist_ft_var")
    with f4:
        ft_method = st.selectbox("Method", methods, key="hist_ft_method")

    sort_by = st.selectbox("Sort by", ["Date (newest)", "Winning CTOR ↓", "CTOR margin ↓"], key="hist_sort")

    # Filter
    filtered = history
    if ft_campaign != "All":
        filtered = [h for h in filtered if h["campaign_type"] == ft_campaign]
    if ft_segment != "All":
        filtered = [h for h in filtered if h["segment"] == ft_segment]
    if ft_var != "All":
        filtered = [h for h in filtered if h["test_variable"] == ft_var]
    if ft_method != "All":
        filtered = [h for h in filtered if h["statistical_method"] == ft_method]

    # Sort
    if sort_by == "Winning CTOR ↓":
        filtered.sort(key=lambda h: h.get("winning_ctor") or 0, reverse=True)
    elif sort_by == "CTOR margin ↓":
        filtered.sort(key=lambda h: abs(h.get("ctor_margin") or 0), reverse=True)

    if not filtered:
        st.info("No tests match the current filters.")
    else:
        for h in filtered:
            w = h.get("winning_variant", "—")
            winner_badge = f"<span class='badge-winner'>Variant {w}</span>" if w in ("A", "B") else f"<span class='badge-neutral'>{w}</span>"
            tv_label = TEST_VAR_LABELS.get(h["test_variable"], h["test_variable"])
            method_badge = f"<span class='badge-method'>{h['statistical_method']}</span>"
            ctor_str = fmt_pct(h.get("winning_ctor"))
            margin_str = f"{h['ctor_margin']:+.1%}" if h.get("ctor_margin") is not None else "—"
            date_str = h["created_at"][:10]

            st.markdown(
                f"<div class='card' style='margin-bottom:0.6rem'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.4rem'>"
                f"<div>"
                f"<b style='color:#111827'>{h['campaign_type']}</b>"
                f"<span style='color:#6b7280;font-size:0.85rem'> · {h['segment']}</span>"
                f"</div>"
                f"<div style='display:flex;gap:0.4rem;align-items:center'>"
                f"<span class='badge-neutral'>{tv_label}</span>"
                f"{winner_badge}"
                f"<span style='font-weight:600;color:#059669'>{ctor_str} CTOR</span>"
                f"<span style='color:#6b7280;font-size:0.82rem'>({margin_str})</span>"
                f"{method_badge}"
                f"<span style='color:#9ca3af;font-size:0.80rem'>{date_str}</span>"
                f"</div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr>", unsafe_allow_html=True)
    _, btn_col = st.columns([3, 1])
    with btn_col:
        if st.button("New test →", type="primary", use_container_width=True):
            st.session_state.campaign_id = None
            st.session_state.variants = None
            st.session_state.brief = None
            st.session_state.results = None
            go(1)


# ══════════════════════════════════════════════════════════════════════════════
# Nav bar + router
# ══════════════════════════════════════════════════════════════════════════════
def nav():
    screen = st.session_state.screen
    steps = ["Brief", "Review", "Results", "History"]
    cols = st.columns([1, 4, 1])
    with cols[0]:
        st.markdown("**✦ Lumino**", unsafe_allow_html=True)
    with cols[1]:
        step_html = ""
        for i, label in enumerate(steps, 1):
            active = i == screen
            color = "#7c3aed" if active else "#9ca3af"
            weight = "700" if active else "400"
            step_html += f"<span style='margin-right:1.5rem;color:{color};font-weight:{weight};font-size:0.88rem'>{i}. {label}</span>"
        st.markdown(step_html, unsafe_allow_html=True)
    with cols[2]:
        if st.button("History", key="nav_history"):
            go(4)
    st.markdown("<hr style='margin:0.5rem 0 1.5rem'>", unsafe_allow_html=True)


nav()

screen = st.session_state.screen
if screen == 1:
    screen_1()
elif screen == 2:
    screen_2()
elif screen == 3:
    screen_3()
elif screen == 4:
    screen_4()
