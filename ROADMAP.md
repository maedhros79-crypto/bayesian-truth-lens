# Reality Calibration Platform — Master Roadmap
*Working title. Final name TBD — "Reality Calibration Platform" is the concept direction.*

---

## What This Is

A reality calibration platform built on the Examined Uncertainty principle.
Not an oracle. Not a hit piece generator. Not a political tool.
A structured epistemic aid that helps people get a more honest picture of claims,
politicians, corporations, media consumption, and social trends —
by surfacing assumptions, flagging distortions, and offering balanced leads.

**Cultural mission:** Anti-doom-scroll. Anti-radicalization. Anti-AI-delusion.
Most people given honest information make better decisions.
This platform is built on that premise.

**Business model:**
- One-time purchase gets the app and core features
- Credits purchased at near-cost for query-heavy features
- Early adopters of Bayesian Truth Lens get full platform upgrade free when it ships
- No subscription. No ongoing obligation. Value front-loaded into the product.
- Transparent about costs — user knows what queries cost and what margin exists

---

## Core Philosophy (Baked In Everywhere)

- Examined Uncertainty — claims are probabilistic, not binary
- Never "this is false" — always "confidence is Low/Medium/High, here is why"
- Surfacing assumptions is more valuable than delivering verdicts
- Consensus is one input with its own reliability rating, not ground truth
- Unfalsifiable does not mean worthless — re-frame, don't dismiss
- Conspiracy claims get kernel-of-truth-first treatment, never mockery
- Clever defection (technically kept, spirit violated) is more important to flag than outright lies
- The app is not the last word — it is a first pass

---

## Module Roadmap

---

### MODULE 1 — Bayesian Truth Lens (CURRENT — MVP COMPLETE)

Single claim assessment tool.

**Status:** Working. Follow-up conversation window just added.

**Features complete:**
- Claim taxonomy (7 categories)
- Confidence tiers: Low / Medium / High
- Key assumptions surfaced
- Kernel of truth for conspiracy claims
- Clever defection flag for political claims
- Evidence availability rating
- Socratic question at end
- Follow-up conversation window — scoped, focused, research-lead oriented
- Anti-consensus-machine prompt rules
- Shut-up-and-calculate pattern flagging
- Ontological framework consistency checking

**Next additions for Module 1:**
- Suggested research leads with steelmanning of opposing views
- Source credibility notes
- Video/transcript review — paste YouTube URL or transcript, app extracts and assesses claims, flags what wasn't said

---

### MODULE 2 — RSS Content Quality Feed

Pulls articles, podcasts, YouTube content.
Scores for epistemic quality — nuance, source diversity, assumption transparency.
Surfaces balanced content instead of engagement-optimized content.
Anti-doom-scroll feed that rewards honest complexity over outrage.

**Status:** Planned. Partially overlaps with existing RSS scorer concept.

---

### MODULE 3 — Politician Accountability Tracker

Track record assessment for any named politician.
Promises made vs kept. Stated positions vs voting record.
Clever defection flagged explicitly.
Sources cross-referenced — PolitiFact, VoteSmart, GovTrack, OpenSecrets.
Source agreement and divergence shown as signal, not averaged away.

**Design principle:** Grounded judgment helper, not hit piece generator.
Good faith actions acknowledged. Spirit-violations surfaced.
Politically neutral by design — ongoing attention required.

**Status:** Planned. Next major module after Module 1 polish.

---

### MODULE 4 — Corporate Ethics Scanner

Company name goes in.
Balanced assessment — genuine good practices acknowledged first.
Problematic practices flagged (labor conditions, environmental record, lobbying, etc.)
Alternative companies suggested at comparable price points.
Price difference noted honestly.

**Status:** Planned.

---

### MODULE 5 — Existential Risk & Mimetic Trend Tracker

Calibrated assessment of things people are worried about.
Which concerns are well-founded vs overblown?
Separates genuine trends from algorithmically amplified distortions.

Examples:
- Dating dynamics — internet phenomenon or real demographic shift?
- AI risk timelines — what does evidence actually support?
- Economic collapse narratives — calibrated vs catastrophized?
- Health panics — signal vs noise?

**Status:** Planned.

---

### MODULE 6 — Personal Media Calibration (Watch History Analysis)

User grants read access to YouTube watch history (API available).
App analyzes consumption pattern over last 30 days.
Identifies epistemic skew — not accusatory, just calibrating.
Suggests content that would balance what they've been consuming.
User chooses to engage or not — non-pushy, available on request.

TikTok integration harder due to API restrictions — YouTube first.

**Design principle:** "Based on what you've been watching, here are perspectives
you probably haven't encountered recently." No judgment. Just calibration available.

**Status:** Planned. Phase 3-4. Design toward it from now.

---

## Technical Architecture (Target)

**Frontend:** Web app (React or similar) — works on phone browser, no app store needed.
Current Streamlit version is desktop MVP only.

**Backend:** FastAPI server (~150 lines Python)
- Validates license keys
- Tracks query counts per user
- Forwards API calls to Anthropic using platform API key
- Handles credit pack redemption
- User never sees platform API key

**Payments:** Gumroad
- One-time app purchase
- Credit pack purchases
- Handles tax reporting automatically
- ~10% fee, nets ~$18 on $20 sale

**API:** Anthropic Claude (Sonnet/Opus)
Quality of reasoning is the entire value proposition.
Local models tested (Mistral 7B, LLaMA 3.1 8B) — insufficient reasoning depth for this use case.
Frontier model quality is non-negotiable for examined uncertainty framework.

**Hosting:** Railway or Render (free tier for backend), Vercel (free for frontend)

---

## Immediate Build Queue

1. ~~Follow-up conversation window~~ ✓ DONE
2. Research leads with steelmanning in follow-up responses
3. FastAPI backend with license key validation and query tracking
4. Migrate from Streamlit to web app for phone compatibility
5. Gumroad setup — app purchase + credit packs
6. Deploy to web hosting
7. Politician module
8. RSS feed module

---

## Distribution Plan

**Launch with Module 1 (Bayesian Truth Lens standalone)**
- Price: ~$20 one-time
- Early adopters get full platform upgrade free
- Transparent pricing — cost of queries shown honestly

**Target communities for launch:**
- r/slatestarcodex
- r/philosophy
- r/skeptic
- r/rational
- Hacker News — Show HN post
- Philosophy/rationalist YouTube adjacent channels

**Second press moment:** Politician module launch
**Third press moment:** Watch history calibration feature

---

## Realistic Year One Sales Estimate

Low end (modest community traction): 100–300 sales = $2,000–$6,000
Middle (good Show HN + Reddit response): 300–600 sales = $6,000–$12,000
High end (something goes modestly viral): 1,000–2,000 sales = $20,000–$40,000

Zero ongoing costs on one-time purchase model.
Every dollar after Gumroad fee is margin.

---

## Name Candidates

- Reality Calibration Platform (concept direction — working title)
- Bayesian Truth Lens (current module name — possibly too narrow for full platform)
- TBD

---

## Notes

- Shut-up-and-calculate: coined here as pejorative for deliberate avoidance
  of ontological implications of empirical theories. Worth formalizing as
  epistemic concept alongside examined uncertainty framework.
- Anti-hate framing: epistemic distortion precedes emotional radicalization.
  Intervening at the cognitive level before emotion calcifies into identity
  is the right point of intervention. This platform does that structurally.
- Early adopter loyalty: people who buy Bayesian Truth Lens now get
  full platform free. Good faith signal. Worth honoring.

---

### MODULE 7 — Phronesis Engine (Practical Wisdom Layer)

Complements the epistemic assessment with practical wisdom.
Not oracular. Not prescriptive. A reflection aid.

**The distinction it addresses:**
Episteme tells you what is likely true.
Phronesis tells you how to act well with that knowledge.
Pure epistemic balance can be sterile — wisdom is the missing layer.

**What it does:**
- Takes a situation or decision, not just a claim
- Returns historical parallels — real figures at real moments of balanced judgment
- Surfaces relevant frameworks from multiple wisdom traditions
- Asks questions worth sitting with before acting
- Never gives directives — always hands the question back enriched

**Core framing:**
"What would a reasonable, experienced, genuinely good person consider here?"
Not a perfect person. Not a saint. A reasonable one with good values and real experience.

**Multi-tradition sourcing:**
- Stoicism — equanimity under pressure, distinguishing what you can and cannot influence
- Buddhism — attachment and aversion distortions, sitting with uncertainty without forcing resolution
- Confucian ethics — relational situations, obligations, role and responsibility
- Indigenous traditions — long-term thinking, obligations to future generations, community decisions
- Contemplative Abrahamic strands — humility, limits of understanding, acting without certainty
  (Meister Eckhart, Ibn Arabi, Desert Fathers, Maimonides — wisdom literature not institutional dogma)

**Design principles:**
- Real figures at real moments of genuine balanced judgment — not hagiography
- Always acknowledge the shadow side — Marcus Aurelius also persecuted Christians,
  Solomon was wise and later catastrophically unwise. Honesty prevents reverence machine.
- Output develops wisdom in the user rather than replacing it
- Always material for reflection, never instruction
- Consistent with Socratic method — enrich the question, don't answer it

**Status:** Planned. Later phase. Requires careful sourcing and prompt architecture.

---

## Business Model (Revised)

**Core tool: Free**
The base claim assessment tool is free to use.
User brings their own Anthropic API key.
Maximum distribution. Consistent with the platform's values.

**Deeper features: Small one-time unlock (~$5-10)**
Follow-up conversation, research leads, politician module, straw man/steelman buttons.
One-time purchase, not subscription.
Early supporters get full platform upgrade free when it ships.

**Donations: Voluntary, fully transparent**
A visible running total of all donations received.
A visible running total of all revenue from paid features.
Both numbers public.
Self-limiting by design — as the number grows, the perceived need to give decreases.
Consistent with the platform's examined uncertainty philosophy applied to its own finances.

**Why this model:**
- Maximum distribution of a tool that benefits the commons
- Revenue enables geographic freedom, not lifestyle inflation
- Transparency signals values more credibly than any stated mission
- Freemium floor ensures the tool remains sustainable without extraction

**Goal:**
Not wealth. Freedom from geographic constraint.
Enough to travel, explore, build, create.
Respect for having built something genuinely useful.

---

### MODULE 8 — Decision Space Mapper

Helps users think through significant life decisions by surfacing factors,
perspectives, and possibility spaces they may not have considered.
Not an oracle. Not a directive. A structured thinking partner.

**What it does:**
- Takes a decision or situation the user is facing
- Surfaces factors and considerations they may have missed
- Steelmans the paths they are NOT currently considering
- Applies temporal perspective — how does this look from 5 years out, 20 years out?
- Surfaces what the user is actually optimizing for versus what they think they are
- Flags when a decision may already be half-made and the user is seeking confirmation
- Ends with a Socratic question aimed at the deepest assumption underlying the choice

**Core framing:**
Not "here is what you should do."
"Here are perspectives and factors worth considering before you decide."
The decision is always the user's.

**Design principles:**
- Draws on the Phronesis Engine — historical parallels, wisdom traditions, real figures
  at real moments of genuine decision under uncertainty
- Applies examined uncertainty to the decision itself — what would you have to believe
  for each path to be the right one?
- Flags the confirmation bias pattern gently when present — the half-made decision
  seeking ratification rather than genuine exploration
- Applies temporal humility — most decisions that feel irreversible aren't, and most
  that feel low-stakes compound over time
- Never resolves the tension on behalf of the user. Enriches the question, doesn't answer it.

**Prompt anchors:**
- "What are you actually optimizing for here — and is that what you think you're optimizing for?"
- "What's the strongest case for the path you're currently not considering?"
- "How does this decision look from 5 years out? From 20?"
- "What would have to be true for the option that scares you most to be the right one?"

**Status:** Planned. Later phase. Shares architecture with Phronesis Engine (Module 7).

---

### MODULE 9 — Video & Media Bias Analyzer

Analyzes video content, transcripts, speeches, and media segments for:
- Claims taken out of context — flags when a quote or statistic misrepresents
  the source material it comes from
- Selective framing — identifies what was left out that would change the picture
- Populist rhetoric patterns — distinguishes genuine policy argument from
  emotional manipulation techniques
- Misinformation campaign signatures — does this content pattern match known
  disinformation tactics? Who benefits from this narrative?

**Input modes:**
- YouTube URL (transcribed via existing pipeline)
- Pasted transcript
- Live debate feed (eventual real-time goal)

**Output:**
- Claim-by-claim breakdown with context flags
- Overall framing assessment — what picture does this content construct?
- What was not said that would be relevant?
- Ideological direction flag — not as a verdict but as a transparency signal

**Status:** Planned. Requires YouTube transcript pipeline (partially built in roadmap).

---

### MODULE 10 — Political Speech & Debate Analyzer

Real-time and post-hoc analysis of political speeches and debates.

**What it flags:**
- Populist rhetoric versus substantive policy argument
- Clear misinformation versus contested claims versus defensible positions
- Serving narrow interests versus broad public interest — follow the incentive
- Disinformation campaign patterns — coordinated messaging, talking point
  synchronization across sources, narrative designed to destabilize or consolidate

**Useful truth versus useful falsehood detection:**
Some true things are deployed to mislead. Some false things are deployed to
stabilize communities. The app should flag both:
- Useful truth: factually accurate but selectively deployed to create a false picture
- Useful falsehood: factually wrong but serving a stabilizing social function
- Misleading truth: technically correct but designed to imply something false
- Destabilizing falsehood: false and deployed to create division or panic

This is the most politically sensitive module and requires the most careful
neutrality calibration. The goal is not to declare winners and losers in political
debates — it is to make the rhetorical techniques visible so users can evaluate
them for themselves.

**Real-time goal:**
Live debate feed analysis with claim flagging in near-real-time.
This is technically ambitious but increasingly feasible as transcription
APIs improve. Medium-term target rather than immediate build.

**Status:** Planned. Politically sensitive — requires extensive neutrality testing
before release. Build after politician accountability module is stable.

---

### MODULE 11 — News & Narrative Pattern Tracker

Analyzes trends across news sources and flags:
- Coordinated narrative patterns — same framing appearing simultaneously
  across multiple outlets suggesting a campaign rather than independent reporting
- Ideological direction of content clusters — without declaring one direction
  correct, makes the directional pull visible
- Missing story detection — what significant developments are being systematically
  underreported across mainstream sources?
- Source reliability patterns — which outlets have track records of accuracy
  versus correction rates versus ideological consistency versus factual drift

**The useful falsehood problem:**
Some false narratives persist because they serve social stability functions.
Some true narratives are suppressed because they would be destabilizing.
The app should flag both without automatically privileging either disruption
or stability — the user decides what to do with the information.

**Status:** Planned. Overlaps significantly with RSS Content Quality Feed (Module 2).
Build as an extension of that module.
