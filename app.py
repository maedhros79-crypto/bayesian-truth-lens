import streamlit as st
from assessor import assess_claim
from followup import get_followup_response

st.set_page_config(
    page_title="Bayesian Truth Lens",
    page_icon="🔍",
    layout="centered",
)

st.markdown("""
<style>
    .main { max-width: 720px; }
    .tier-HIGH    { color: #2d7a2d; font-weight: 600; font-size: 1.3em; }
    .tier-MEDIUM  { color: #a67c00; font-weight: 600; font-size: 1.3em; }
    .tier-LOW     { color: #b03030; font-weight: 600; font-size: 1.3em; }
    .section-label {
        font-size: 0.75em;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #888;
        margin-bottom: 2px;
    }
    .assumption-item {
        padding: 4px 0;
        border-bottom: 1px solid #f0f0f0;
        font-size: 0.95em;
    }
    .disclaimer {
        font-size: 0.8em;
        color: #999;
        border-top: 1px solid #eee;
        padding-top: 8px;
        margin-top: 24px;
    }
    .socratic {
        font-style: italic;
        color: #444;
        padding: 10px 14px;
        border-left: 3px solid #ccc;
        margin-top: 8px;
    }
    .kernel-box {
        background: #f7f7f2;
        border-left: 3px solid #bbb;
        padding: 10px 14px;
        font-size: 0.95em;
    }
    .flag-box {
        background: #fff8f0;
        border-left: 3px solid #e0a040;
        padding: 10px 14px;
        font-size: 0.95em;
    }
    .shift-box {
        background: #f5f5ff;
        border-left: 3px solid #8888cc;
        padding: 10px 14px;
        font-size: 0.95em;
    }
    .chat-user {
        background: #f0f0f0;
        border-radius: 6px;
        padding: 8px 12px;
        margin: 6px 0;
        font-size: 0.95em;
    }
    .chat-assistant {
        background: #fff;
        border-left: 3px solid #8888cc;
        padding: 8px 12px;
        margin: 6px 0;
        font-size: 0.95em;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Bayesian Truth Lens")
st.markdown(
    "A structured judgment aid. Not an oracle. "
    "Returns a probabilistic confidence assessment and surfaces "
    "the assumptions underneath any claim — so you can examine your own reasoning."
)
st.divider()

# ── API Key ───────────────────────────────────────────────────────────────────

with st.expander("⚙️ License Key", expanded=not st.session_state.get("license_key")):
    license_key_input = st.text_input(
        "License Key",
        type="password",
        value=st.session_state.get("license_key", ""),
        placeholder="BTL-XXXX-XXXX-XXXX",
        help="Your license key from purchase. Never stored beyond this session."
    )
    if license_key_input:
        st.session_state["license_key"] = license_key_input.strip()
        st.success("License key set.")

# ── Plain language toggle ────────────────────────────────────────────────────

plain_language = st.toggle(
    "Plain language mode",
    value=False,
    help="Simpler explanations — less jargon, more concrete examples. Same depth, more accessible."
)
st.session_state["plain_language"] = plain_language

# ── Claim input ───────────────────────────────────────────────────────────────

claim = st.text_area(
    "Enter a claim to assess",
    height=100,
    placeholder=(
        "e.g. 'Senator X promised to lower taxes but voted for bill Y which contained a hidden tax loophole.' "
        "Or: 'A secret global cabal controls all world governments.' "
        "Or: 'Consciousness is a fundamental feature of the universe, not an emergent property of matter.'"
    )
)

run = st.button("Assess", type="primary", disabled=not claim.strip())

# ── Helper: fire a followup question immediately ──────────────────────────────

def fire_followup(question: str):
    """Send a followup question immediately and store result in session."""
    license_key = st.session_state.get("license_key", "")
    if not license_key:
        st.session_state["followup_error"] = "License key needed for follow-up questions."
        return
    with st.spinner("Researching..."):
        response = get_followup_response(
            claim=st.session_state["current_claim"],
            result=st.session_state["current_result"],
            conversation_history=st.session_state.get("followup_history", []),
            user_message=question,
            license_key=license_key
        )
    if response.startswith("ERROR:"):
        st.session_state["followup_error"] = response
    else:
        st.session_state.setdefault("followup_history", []).append(
            {"role": "user", "content": question}
        )
        st.session_state["followup_history"].append(
            {"role": "assistant", "content": response}
        )

# ── Assessment output ─────────────────────────────────────────────────────────

if run:
    license_key = st.session_state.get("license_key", "")
    if not license_key:
        st.error("Please enter your license key above.")
        st.stop()

    with st.spinner("Assessing..."):
        result = assess_claim(
            claim.strip(),
            license_key=license_key,
            plain_language=st.session_state.get("plain_language", False)
        )

    if "error" in result:
        st.error(result["error"])
        if "raw_response" in result:
            with st.expander("Raw model response"):
                st.code(result["raw_response"])
        st.stop()

    # Store in session for follow-up
    st.session_state["current_result"] = result
    st.session_state["current_claim"] = claim.strip()
    st.session_state["followup_history"] = []
    st.session_state.pop("followup_error", None)

    st.divider()

    st.markdown('<div class="section-label">Claim Type</div>', unsafe_allow_html=True)
    st.markdown(f"**{result.get('claim_type_label', 'Unknown')}** — {result.get('claim_type_explanation', '')}")
    st.markdown("<br>", unsafe_allow_html=True)

    tier = result.get("confidence_tier", "MEDIUM")
    st.markdown('<div class="section-label">Confidence</div>', unsafe_allow_html=True)
    st.markdown(f'<span class="tier-{tier}">{tier}</span>', unsafe_allow_html=True)
    st.markdown(f"*{result.get('confidence_description', '')}*")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Web search indicator ──
    if result.get("web_search_used"):
        st.info("🔍 **Web search used** — Current information was retrieved to supplement this assessment.")
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Temporal flag ──
    temporal_flag = result.get("temporal_flag")
    temporal_note = result.get("temporal_note")
    if str(temporal_flag).lower() == "true" and temporal_note:
        st.warning(
            f"⏱ **Temporal Limitation** — This claim involves recent or ongoing events "
            f"that may postdate the model's training data (approximately early 2024). "
            f"{temporal_note}"
        )
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">Reasoning</div>', unsafe_allow_html=True)
    st.write(result.get("confidence_reasoning", ""))
    st.markdown("<br>", unsafe_allow_html=True)

    kernel = result.get("kernel_of_truth")
    if kernel:
        st.markdown('<div class="section-label">What This Claim Gets Right</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kernel-box">{kernel}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    defection = result.get("clever_defection_flag")
    if defection:
        st.markdown('<div class="section-label">⚠ Clever Defection Flag</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="flag-box">{defection}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    moral_arc = result.get("moral_arc")
    if moral_arc:
        st.markdown('<div class="section-label">Moral Arc</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kernel-box">{moral_arc}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    evaluative_map = result.get("evaluative_map")
    if evaluative_map:
        st.markdown('<div class="section-label">Territory This Question Opens</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kernel-box">{evaluative_map}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    subclaims = result.get("subclaim_decomposition")
    if subclaims:
        st.markdown('<div class="section-label">Subclaim Breakdown</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kernel-box">{subclaims}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    shared_ground = result.get("shared_ground")
    if shared_ground:
        st.markdown('<div class="section-label">Shared Ground</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="shift-box">{shared_ground}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    assumptions = result.get("key_assumptions", [])
    if assumptions:
        st.markdown('<div class="section-label">This Assessment Assumes</div>', unsafe_allow_html=True)
        for a in assumptions:
            st.markdown(f'<div class="assumption-item">→ {a}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    evidence_avail = result.get("evidence_availability", "")
    evidence_note = result.get("evidence_note", "")
    if evidence_note:
        label_map = {
            "AVAILABLE": "Evidence",
            "PARTIAL":   "Evidence (Partial)",
            "ABSENT":    "Evidence — Research Lead",
        }
        label = label_map.get(evidence_avail, "Evidence")
        st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)
        if evidence_avail == "ABSENT":
            st.info(f"🔍 {evidence_note}")
        else:
            st.write(evidence_note)
    st.markdown("<br>", unsafe_allow_html=True)

    shift = result.get("confidence_shift_note")
    if shift:
        st.markdown('<div class="section-label">What Would Change This Assessment</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="shift-box">{shift}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    socratic = result.get("socratic_question")
    if socratic:
        st.markdown('<div class="section-label">A Question Worth Sitting With</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="socratic">{socratic}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="disclaimer">'
        'This assessment is a thinking aid, not a verdict. '
        'It draws on the model\'s training data, which has limits, biases, and a knowledge cutoff. '
        'Verify independently. Check your own assumptions. This tool is not the last word — it is a first pass.'
        '</div>',
        unsafe_allow_html=True
    )

# ── Follow-up conversation ────────────────────────────────────────────────────

if st.session_state.get("current_result"):
    st.divider()
    st.markdown('<div class="section-label">Go Deeper</div>', unsafe_allow_html=True)
    st.markdown(
        "Ask focused questions about this assessment. "
        "Request research leads, sources, counter-arguments, or clarification on assumptions."
    )

    # Show any error from last fire
    if st.session_state.get("followup_error"):
        st.error(st.session_state.pop("followup_error"))

    # Display conversation history
    history = st.session_state.get("followup_history", [])
    for msg in history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">You: {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-assistant">{msg["content"]}</div>', unsafe_allow_html=True)

    # Contextual straw man button — appears after a steelman response
    if history:
        last_assistant_msgs = [m for m in history if m["role"] == "assistant"]
        if last_assistant_msgs:
            last_response = last_assistant_msgs[-1]["content"].lower()
            last_user_msgs = [m for m in history if m["role"] == "user"]
            last_question = last_user_msgs[-1]["content"].lower() if last_user_msgs else ""
            is_steelman = (
                "steelman" in last_question or
                "counter-argument" in last_question or
                "strongest" in last_question
            )
            already_has_strawman = "straw man" in last_response or "strawman" in last_response
            if is_steelman and not already_has_strawman:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("↳ Now show me the straw man versions"):
                    fire_followup(
                        "Now show me the straw man versions of both sides — "
                        "the brittle, easily collapsed versions argued in bad faith or intellectual laziness. "
                        "For each side contrast it directly with the steelman you just gave. "
                        "The goal is to help the user recognize weak or dishonest reasoning when they encounter it."
                    )
                    st.rerun()

    # Suggestion buttons — fire immediately on click
    if not history:
        st.markdown("**Quick starts — click to get an immediate answer:**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Best sources on this"):
                fire_followup("What are the best sources to read on this claim — both supporting and opposing? Include author names, publication names, and why each is credible.")
                st.rerun()
        with col2:
            if st.button("Strongest counter-argument"):
                fire_followup("What is the strongest counter-argument to this assessment? Steelman the opposing view as clearly as possible.")
                st.rerun()
        col3, col4 = st.columns(2)
        with col3:
            if st.button("Where to research this"):
                fire_followup("Where would I go to research this claim further? Name specific search terms, databases, institutions, or researchers I should look into.")
                st.rerun()
        with col4:
            if st.button("Show straw man versions"):
                fire_followup(
                    "Show me the straw man versions of both sides of this claim — "
                    "the brittle, easily collapsed versions that get argued in bad faith or intellectual laziness. "
                    "For each side: first give the steel man (strongest honest version) then immediately contrast it "
                    "with the straw man (weakest caricature version). "
                    "The goal is to help the user recognize bad faith or lazy reasoning when they encounter it in the wild."
                )
                st.rerun()
        col5, _ = st.columns(2)
        with col5:
            if st.button("What reasoning patterns are present?"):
                fire_followup(
                    "Identify any cognitive biases or logical fallacies that may be present in this claim. "
                    "For each pattern: name it, explain when it is a valid useful heuristic, explain when it "
                    "distorts reasoning, then assess which situation applies here. "
                    "Present these as possibilities worth examining — not as accusations. "
                    "Remember the claim as typed may not represent the full extent of the person's thinking."
                )
                st.rerun()

    # Manual input for custom questions
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form(key="followup_form", clear_on_submit=True):
        user_input = st.text_input(
            "Or ask your own question",
            placeholder="e.g. What are the strongest sources on the opposing view?"
        )
        submitted = st.form_submit_button("Ask")

    if submitted and user_input.strip():
        fire_followup(user_input.strip())
        st.rerun()

    # Clear conversation
    if history:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear conversation"):
            st.session_state["followup_history"] = []
            st.rerun()
