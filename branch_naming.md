# Repo guide — branch naming and folder structure

This document covers two things: how branches are named in the `ab-testing-agent` repo, and what every folder and file in the repo is for. Read both sections before you start working. 

---

## Contents

- [Branch naming convention](#branch-naming-convention)
- [Repo structure](#repo-structure)

---

## Branch naming convention

Consistent naming makes the project board, pull request list, and git log readable at a glance — especially important when four people are working in the same repo across a six-week sprint.

### Format

```
<role>/<week>/<short-description>
```

All three parts are required. Use lowercase and hyphens only — no spaces, underscores, or mixed case.

### Role prefixes

Each team member uses the prefix that matches their primary role for the work on that branch.

| Prefix | Role |
|---|---|
| `pm` | AI Product Owner / PM |
| `ds` | Data Scientist |
| `eng` | AI & Data Engineer |
| `ui` | UI/UX Developer |

If a branch spans two roles (e.g. the PO/PM doing engineering work), use the role the work primarily belongs to. If genuinely shared, use the role of the person who opened the branch.

### Week labels

Use the week label from the project plan to make it easy to filter branches by sprint.

| Label | Dates |
|---|---|
| `w0` | 26 – 30 Mar |
| `w1` | 31 Mar – 6 Apr |
| `w2` | 7 – 13 Apr |
| `w3` | 14 – 20 Apr |
| `w4` | 21 – 27 Apr |
| `w5` | 28 Apr – 4 May |

### Short description

2–4 words, hyphenated, describing what the branch does — not what ticket it closes. Use verbs where possible.

Good: `add-subscriber-split-logic`
Good: `build-bayesian-model`
Good: `seed-postgres-schema`

Avoid: `fix`, `update`, `changes`, `wip`, `misc`

### Examples

```bash
# Data scientist building the brief intake agent in week 1
ds/w1/brief-intake-agent

# Engineer setting up Docker Compose in week 0
eng/w0/docker-compose-setup

# Engineer building Listmonk API integration in week 1
eng/w1/listmonk-api-integration

# Data scientist building the Bayesian model in week 2
ds/w2/bayesian-beta-binomial-model

# Engineer building the simulated send engine in week 2
eng/w2/simulated-send-engine

# UI/UX developer building the results screen in week 3
ui/w3/results-screen

# PO/PM adding the variation axes config file in week 0
pm/w0/variation-axes-config

# Data scientist tuning synthetic data distributions in week 3
ds/w3/tune-synthetic-distributions

# Engineer fixing a pipeline bug in week 4
eng/w4/fix-pipeline-cold-start
```

### Special branches

| Branch | Purpose |
|---|---|
| `main` | Stable, demo-ready code only. No direct commits — merge via PR. |
| `develop` | Integration branch. All feature branches merge here first. |

Nobody commits directly to `main`. All work goes to a feature branch, then into `develop` via a pull request, then `develop` is merged to `main` when a week's exit gate is confirmed passing.

### Pull request titles

Use the same format as the branch name but written as a sentence:

```
[DS/W1] Add brief intake agent with Pydantic CampaignBrief model
[ENG/W2] Build simulated send engine with engagement event injection
[UI/W3] Build results screen with frequentist and Bayesian panels
[PM/W0] Add variation axes config for all four campaign types
```

### Quick reference

```
pm/w{n}/what-it-does       → PO/PM work
ds/w{n}/what-it-does       → Data science work
eng/w{n}/what-it-does      → Engineering work
ui/w{n}/what-it-does       → UI/UX work
```

---

## Repo structure

The tree below shows every folder and file in the repo. The sections that follow explain what each one is for, who owns it, and exactly how it should be used. Since the repo currently has no code, this guide tells the team what to build where before anything exists.

```
ab-testing-agent/
│
├── agents/
│   ├── brief_intake.py
│   ├── content_generation.py
│   ├── simulated_send.py
│   └── winner.py
│
├── models/
│   ├── __init__.py
│   ├── campaign_brief.py
│   ├── email_variant.py
│   └── winner_result.py
│
├── config/
│   ├── variation_axes.py
│   ├── campaign_types.py
│   └── segments.py
│
├── data/
│   ├── seed/
│   │   ├── seed_all.py
│   │   ├── subscribers.py
│   │   ├── products.py
│   │   └── campaign_history.py
│   └── schema/
│       └── schema.sql
│
├── dashboard/
│   ├── app.py
│   └── screens/
│       ├── new_test.py
│       ├── review_variants.py
│       ├── results.py
│       └── history.py
│
├── infrastructure/
│   └── docker-compose.yml
│
├── decisions/
│   ├── README.md
│   ├── DS-001-*.md
│   └── ENG-001-*.md
│
├── tests/
│   ├── test_agents/
│   └── test_data/
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

### `agents/`

**Owner:** Data Scientist (`brief_intake.py`, `content_generation.py`), AI/Data Engineer (`simulated_send.py`, `winner.py`)

The four LangChain agents that make up the pipeline. Each file is one agent with one responsibility. Agents communicate by passing validated Pydantic models — they do not share state directly.

Business logic belongs here and nowhere else. It does not belong in the dashboard screens, in the config files, or in the models.

The agents run in sequence: `brief_intake` → `content_generation` → `simulated_send` → `winner`. Each receives its inputs as a Pydantic model, does its work, and returns a Pydantic model to the next.

---

**`agents/brief_intake.py`**

*Owner: Data Scientist*

Agent 1. Receives a natural language campaign brief from the user along with their selections for campaign type, target segment, test variable (subject line, body, or CTA), and statistical method. Uses an LLM to parse and classify the input, then queries Postgres to enrich the brief with live segment data — subscriber count, average order value, top product category, and days since last purchase.

Outputs a validated `CampaignBrief` Pydantic object (defined in `models/campaign_brief.py`).

**Responsible for:** NLP parsing, campaign type and segment classification, Postgres enrichment queries, emitting a `CampaignBrief`.

**Not responsible for:** generating email content — that is `content_generation.py`.

If the LLM returns output that cannot be parsed or fails Pydantic validation, this agent retries once with an error correction prompt appended. If the retry fails, it raises with the full context logged.

---

**`agents/content_generation.py`**

*Owner: Data Scientist*

Agent 2. Receives the `CampaignBrief` and makes a single LLM call to generate exactly two email variants — Variant A (control) and Variant B (challenger). Only the element specified by `test_variable` in the brief differs between the two. All other elements — the ones not being tested — are word-for-word identical across both variants.

**Responsible for:** constructing the LLM prompt using the variation axes from `config/variation_axes.py`, enforcing the single-variable constraint, parsing the JSON response into two `EmailVariant` objects, and running a consistency check that confirms all shared fields are identical. Includes retry logic (max two retries) if the LLM output is malformed or the consistency check fails.

**Important:** variation instructions must not be hardcoded here. They live in `config/variation_axes.py`. This agent reads from that config and injects the relevant instructions into the prompt.

---

**`agents/simulated_send.py`**

*Owner: AI/Data Engineer*

Agent 3. Receives two `EmailVariant` objects and runs the simulated send. Creates two campaigns in Listmonk via its REST API — one per variant — splits the target subscriber segment 50/50, assigns each group to its campaign, and triggers the sends. Listmonk routes sends through Mailhog (configured as the SMTP server), which captures them without delivering to any real inbox.

After sending, injects synthetic engagement events per variant: open counts, click counts, CTOR, and conversion rate. These are computed from the campaign type base rate (`config/campaign_types.py`) multiplied by a segment modifier (`config/segments.py`) plus Gaussian noise. There is no score-weighting — results are driven purely by campaign type, segment, and randomness. Results are written back to the `variants` and `campaign_history` tables in Postgres.

**Responsible for:** Listmonk API calls (create campaign, create lists, assign subscribers, trigger send), subscriber splitting, synthetic engagement event injection, Postgres write-back.

**Not responsible for:** statistical analysis — that is `winner.py`.

All Listmonk API calls go through a shared httpx client wrapper with retry logic. Non-200 responses raise an exception with the request details included.

---

**`agents/winner.py`**

*Owner: AI/Data Engineer (orchestration and Postgres logging), Data Scientist (statistical methods)*

Agent 4. Receives the engagement results from the simulated send and runs two independent statistical analyses.

**Frequentist analysis** (scipy.stats): two-proportion z-test on click counts. Outputs p-value, 95% confidence interval, and null hypothesis decision (rejected at p < 0.05).

**Bayesian analysis**: Beta-Binomial model. Updates a Beta(1,1) prior with click and non-click counts per variant. Samples from the posterior distributions to compute P(A is best), P(B is best), and expected uplift.

**Decision state** is determined as follows:
- **WINNER** — both methods agree on the same variant winning
- **INCONCLUSIVE** — methods disagree (e.g. frequentist significant for A, but Bayesian gives only 60% for A). Both results surfaced in full.
- **DEFER** — click counts too low for either method to produce a reliable result

An LLM then generates a plain-language narrative referencing both outputs: what won, the margin, and a recommended next action. Written for a non-technical marketing audience.

All results logged to MLflow (parent run per test, child runs per variant) and written to the `ab_tests` table. Outputs a `WinnerResult` Pydantic object for the dashboard.

---

### `models/`

**Owner:** Data Scientist (defines the models), AI/Data Engineer (reviews before finalising)

Pydantic data models that serve as contracts between agents. Every piece of data flowing from one agent to the next is typed and validated here. These are the single source of truth for what fields exist, what their types are, and what constraints apply.

**Rule: do not change a model without discussing with the team first.** Adding a field to `CampaignBrief` affects the brief intake agent, the content generation agent, and the dashboard all at once. Removing a field breaks any agent that reads it.

---

**`models/__init__.py`**

Exports all three models so they can be imported cleanly from anywhere:

```python
from models import CampaignBrief, EmailVariant, WinnerResult
```

---

**`models/campaign_brief.py`**

Defines `CampaignBrief` — the object Agent 1 emits and Agent 2 consumes. Key fields: `campaign_type` (Literal: promotional, abandoned_cart, re_engagement, welcome), `segment` (Literal: active_buyers, browse_only, lapsed_90d, new_signups, vip), `test_variable` (Literal: subject_line, body, cta), `stat_method` (Literal: frequentist, bayesian, both), `segment_size`, `goal`, `tone_hint`, `product_category`, `featured_product_ids`, `discount_pct`, `created_at`. All fields are typed. Optional fields have explicit defaults.

---

**`models/email_variant.py`**

Defines `EmailVariant` — the email content for a single variant. Fields: `variant_label` (A or B), `subject_line`, `preheader`, `body_html`, `cta_text`, `axis_label` (e.g. "personalised" or "product-led"). Validators enforce: subject line ≤ 50 characters, CTA text ≤ 5 words.

Used twice per pipeline run — once for Variant A, once for Variant B. Both are passed to the simulated send agent together.

---

**`models/winner_result.py`**

Defines `WinnerResult` — the full output of the winner agent. Fields: `winner` (A, B, or None), `decision_state` (WINNER, INCONCLUSIVE, DEFER), `p_value`, `confidence_interval` (tuple), `null_hypothesis_rejected` (bool), `p_a_best` (float), `p_b_best` (float), `expected_uplift` (float), `narrative` (str), `methods_agree` (bool). The Streamlit results screen reads directly from this object.

---

### `config/`

**Owner:** PO/PM (owns the business logic decisions that these values represent), Data Scientist (implements the values)

Configuration that drives the pipeline's behaviour. The distinction between `config/` and `agents/` matters: agents contain code logic, config contains the values that logic operates on. To change what the pipeline does creatively or statistically, edit config — not agents.

All config files are plain Python dictionaries or constants. Agents import them directly.

---

**`config/variation_axes.py`**

The most important config file in the repo. Defines, for each combination of campaign type and test variable, what creative strategy Variant A and Variant B should explore. The content generation agent reads from this file to construct its LLM prompt.

Structure: a nested dictionary keyed by `campaign_type` → `test_variable` → variant label (A or B). Each entry has a `label` (displayed as a badge in the dashboard, e.g. "personalised") and an `instruction` (injected directly into the LLM prompt to guide what that variant should do differently).

Example structure:
```python
VARIATION_AXES = {
    "re_engagement": {
        "subject_line": {
            "A": {
                "label": "personalised",
                "instruction": "Use the subscriber's first name in the subject line and open with a direct personal reference..."
            },
            "B": {
                "label": "product-led",
                "instruction": "Lead with a new arrival in the subscriber's preferred product category..."
            },
        },
    },
}
```

When adding a new campaign type or adjusting what a variant explores, edit this file. Do not touch the agent.

---

**`config/campaign_types.py`**

Defines the base engagement rates used by the simulated send engine. Each of the four campaign types has a baseline open rate, click rate, CTOR, and conversion rate drawn from realistic email marketing benchmarks for that type. These are the starting values before segment modifiers are applied.

---

**`config/segments.py`**

Defines a multiplier per segment applied on top of the campaign type base rates during engagement simulation. VIP subscribers have a multiplier above 1.0 (they engage more). Lapsed 90d subscribers have a multiplier below 1.0. This makes simulated results segment-aware and realistic rather than uniformly distributed across all tests.

---

### `data/`

**Owner:** Data Scientist

Everything needed to populate the Postgres database with synthetic data. Split into `seed/` for data generation scripts and `schema/` for table definitions.

---

**`data/schema/schema.sql`**

Creates all database tables. Run this before any seed scripts. Tables: `subscribers`, `products`, `campaign_history`, `ab_tests`, `variants`. Written with `CREATE TABLE IF NOT EXISTS` throughout so it is idempotent — safe to re-run if the database is wiped and recreated.

---

**`data/seed/seed_all.py`**

The single entry point for seeding the database. Runs all seed scripts in the correct order: schema first, then products, then subscribers, then campaign history. Run this once on the machine hosting Postgres:

```bash
python data/seed/seed_all.py
```

All seed scripts are idempotent — safe to re-run on an empty database.

---

**`data/seed/subscribers.py`**

Generates and inserts 800 synthetic subscriber profiles using Faker. Distributed across five segments with realistic counts: Active Buyers (210), Browse-Only (150), Lapsed 90d (160), New Signups (158), VIP (122). Each profile includes email, first name, last name, segment, preferred product category, average order value, days since last purchase, and days since last email open. Distributions within each segment are calibrated to produce distinct behavioural patterns that the agents can respond to meaningfully.

---

**`data/seed/products.py`**

Generates and inserts 50 Lumino product records across five categories: home (10), beauty (10), wellness (10), clothing (10), accessories (10). Each product has a name, category, price, and short description. The brief intake agent fetches the top three products in a subscriber's preferred category when enriching the `CampaignBrief`.

---

**`data/seed/campaign_history.py`**

Generates and inserts 90 days of historical campaign engagement data across all four campaign types and all five segments. Open rates, click rates, CTORs, and conversion rates vary realistically by segment and campaign type. This data serves two purposes: the brief intake agent reads it during enrichment to ground the tone hint in historical performance, and it gives the simulated send engine a realistic backdrop for the engagement rates it generates.

---

### `dashboard/`

**Owner:** UI/UX Developer (screens and layout), AI/Data Engineer (connecting pipeline to dashboard)

The Streamlit application. Single entry point (`app.py`) and four screen files. Screens do not contain pipeline logic — they call agents and display what they return. All business logic stays in `agents/`.

---

**`dashboard/app.py`**

Entry point. Launch with:

```bash
streamlit run dashboard/app.py
```

Handles: page configuration, navigation between the four screens, and session state initialisation. Session state carries data between screens — the `CampaignBrief` created on Screen 1 needs to be available on Screen 2 and Screen 3. The structure of the session state object must be agreed between the UI/UX developer and the engineer before Screen 2 is built.

---

**`dashboard/screens/new_test.py`**

Screen 1 — New test. The brief input screen. Renders: a free-text textarea for the campaign brief, a campaign type dropdown (promotional, abandoned cart, re-engagement, welcome), a target segment dropdown (Active Buyers, Browse-Only, Lapsed 90d, New Signups, VIP), a three-option mutually exclusive selector for the test variable (subject line, body/tone, CTA), and a statistical method selector (Frequentist, Bayesian, Both — with Both pre-highlighted as recommended).

When the user clicks Generate variants, this screen calls the brief intake and content generation agents in sequence, stores the results in session state, and navigates to Screen 2. A loading spinner is shown while the agents run. The Generate button is disabled until all required fields are filled.

---

**`dashboard/screens/review_variants.py`**

Screen 2 — Review variants. Displays the two generated email variants side by side before the test is run. Shows: a held-constant note at the top listing every element that is identical in both variants, and two columns each containing the subject line, preheader, body copy, CTA, and an axis label badge for that variant.

The user can click Edit brief to return to Screen 1 with all selections preserved, or click Run test to trigger the simulated send agent and navigate to Screen 3. State must be fully preserved on back-navigation.

---

**`dashboard/screens/results.py`**

Screen 3 — Results. Displays the full output after the winner agent completes. Contains: three headline metric cards (winner, decision state, whether both methods agreed), two variant comparison cards with engagement metrics per variant (open rate, CTOR, conversions), two side-by-side statistical panels (frequentist: p-value, 95% CI, null hypothesis decision; Bayesian: P(A best), P(B best), expected uplift), the LLM-generated plain-language narrative, and a row of summary badges (what was tested, what was held constant, p-value, Bayesian confidence).

The winning variant card has a green border. If the decision state is INCONCLUSIVE, both panels are shown equally weighted with a note explaining the disagreement. If DEFER, a message explains that the sample was too small to conclude.

---

**`dashboard/screens/history.py`**

Screen 4 — History. Accumulates all past A/B tests and displays them as a table. Headline metrics at the top: total tests run, method agreement rate across all tests, and average winning CTOR. Table columns: campaign type, segment, variable tested, winning variant, CTOR, p-value, Bayesian probability, decision state (colour-coded: green for WINNER, amber for INCONCLUSIVE, grey for DEFER).

This is the most important screen for demonstrating long-term value at the showcase — it shows the system accumulating learning and the two statistical methods consistently agreeing.

---

### `infrastructure/`

**Owner:** AI/Data Engineer

---

**`infrastructure/docker-compose.yml`**

Defines all four local services: Postgres (port 5432), Listmonk (port 9000), Mailhog (SMTP port 1025, web UI port 8025), and MLflow (port 5000). Listmonk is configured to use Mailhog as its SMTP relay — every email Listmonk sends is captured by Mailhog and never delivered to a real address. MLflow uses Postgres as its backend store so experiment runs survive container restarts.

```bash
docker compose up -d      # start all services
docker compose down        # stop all services
docker compose logs -f listmonk  # view logs for a service
```

---

### `decisions/`

**Owner:** PO/PM (maintains the index), Data Scientist (DS- files), AI/Data Engineer (ENG- files)

Architecture Decision Records — written records of every significant design decision, including the context, the options considered, and the rationale for what was chosen. These exist so the team can answer Q&A at the showcase confidently, and so anyone reading the code later understands why things are the way they are.

---

**`decisions/README.md`**

The index of all decisions. Add a row every time a new ADR file is created. Columns: ID, title, date, status (Proposed / Decided / Superseded).

---

**`decisions/DS-001-*.md` (and subsequent DS- files)**

Data science and modelling decisions. What belongs here: why Beta(1,1) was chosen as the Bayesian prior, how synthetic engagement distributions were calibrated, why scipy.stats rather than PyMC, how the INCONCLUSIVE threshold was set. Prefix and number make decisions easy to reference ("see DS-002").

---

**`decisions/ENG-001-*.md` (and subsequent ENG- files)**

Engineering and infrastructure decisions. What belongs here: why Listmonk over alternatives, why the local Postgres hosting approach was used, any non-obvious Docker networking decisions, how the MLflow experiment structure was designed. Same prefix convention.

**ADR template** — copy this when creating a new file:

```markdown
# [DS/ENG]-[number] — [Short title]

**Date:** [Date]
**Author:** [Name]
**Status:** Decided

## Context
What problem were we solving? What constraints applied?

## Options considered
| Option | Pros | Cons |
|---|---|---|
| Option A | ... | ... |
| Option B | ... | ... |

## Decision
What was decided and why.

## Consequences
What this means for the rest of the system. What becomes easier or harder as a result.
```

---

### `tests/`

**Owner:** Data Scientist (`test_agents/`), AI/Data Engineer (`test_data/`)

Unit tests for agents and seed data. Run with `pytest tests/` from the repo root. Write tests as you build — not after. The most critical tests to have in place before the week 3 end-to-end run: brief intake classification (correct campaign type and segment?), content generation consistency (are shared fields truly identical?), and statistical methods (do z-test and Bayesian model produce correct outputs for known inputs?).

---

### Root-level files

**`.env.example`**

Template showing all environment variables the pipeline needs. Copy to `.env` and fill in. The `.env` file is in `.gitignore` and must never be committed to the repo. Share connection strings with teammates directly — not via the repo.

**`.gitignore`**

Ensures `.env`, `__pycache__`, `.DS_Store`, and other non-code files are never committed. Do not remove any entries from this file.

**`requirements.txt`**

All Python package dependencies with pinned versions. If you add a new package during development, add it here immediately — do not let dependency versions drift between team members' environments. Install with `pip install -r requirements.txt`.

**`README.md`**

The project overview for anyone arriving at the repo for the first time: what the system does, how to get started, how to run the pipeline, and which ports each service runs on.
