"""
RSS Content Quality Feed — Streamlit UI module.
Import and call render_rss_tab() from app.py inside a st.tab block.
All API calls go to SERVER_URL (shared with BTL assessor).
"""

import requests
import streamlit as st
from assessor import SERVER_URL

CATEGORIES = [
    "General", "Science", "Philosophy", "Technology",
    "Art & Design", "Music", "Craft", "Entertainment", "News"
]

INTENT_OPTIONS = {
    "mix":        "Mix — everything, no priority",
    "learning":   "Learning — Science, Philosophy, Technology first",
    "creating":   "Creating — Art, Music, Craft first",
    "background": "Background — Entertainment, General first",
    "news":       "News — last 7 days only",
}

TREND_PRESETS = [
    "AI replacing jobs",
    "Social media causing depression",
    "Dating apps ruining relationships",
    "Declining male mental health",
    "AI existential risk",
    "Political polarization getting worse",
    "Declining birth rates",
    "Loneliness epidemic",
    "Economic collapse",
    "Climate tipping points",
    "Misinformation destroying democracy",
    "Attention spans shrinking",
    "Trust in institutions collapsing",
    "Drug-resistant bacteria",
    "Automation displacing workers",
    "Teenage mental health crisis",
]

VERDICT_COLORS = {
    "Pass":  "#2d7a2d",
    "Watch": "#a67c00",
    "Skip":  "#b03030",
}

CONCERN_COLORS = {
    "Well-founded":             "#b03030",
    "Mixed evidence":           "#a67c00",
    "Overblown":                "#2d7a2d",
    "Algorithmically amplified": "#555599",
}


# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{SERVER_URL}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_post(path: str, body: dict, timeout: int = 120) -> dict | list | None:
    try:
        r = requests.post(f"{SERVER_URL}{path}", json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_delete(path: str) -> bool:
    try:
        r = requests.delete(f"{SERVER_URL}{path}", timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False


# ── Rendering helpers ─────────────────────────────────────────────────────────

def render_score_card(item: dict, idx: int):
    """Render a single scored content card."""
    verdict = item.get("verdict", "")
    title = item.get("title") or item.get("url", "Untitled")
    url = item.get("url", "")
    color = VERDICT_COLORS.get(verdict, "#888")
    reason = item.get("verdict_reason", "")
    scores = item.get("scores") or {}
    rep = item.get("creator_reputation")
    rep_note = item.get("reputation_note")
    error = item.get("error")

    with st.container():
        st.markdown(
            f'<span style="color:{color}; font-weight:700; font-size:1.1em;">{verdict or "—"}</span> '
            f'<a href="{url}" target="_blank" style="font-size:0.95em;">{title[:90]}</a>',
            unsafe_allow_html=True
        )

        if error:
            st.caption(f"⚠ {error}")
        elif reason:
            st.caption(reason)

        if rep and rep.get("total_ratings", 0) >= 3:
            tier = rep.get("human_trust_tier", "")
            tier_color = {"High": "#2d7a2d", "Medium": "#a67c00", "Low": "#b03030"}.get(tier, "#888")
            st.markdown(
                f'<span style="font-size:0.8em; color:{tier_color};">👥 Human trust: {tier} '
                f'({rep["total_ratings"]} ratings)</span>',
                unsafe_allow_html=True
            )

        if rep_note:
            st.caption(f"⚡ {rep_note}")

        if scores:
            with st.expander("Signal breakdown"):
                labels = {
                    "signal_to_noise": "Signal-to-Noise",
                    "evergreen_value": "Evergreen Value",
                    "audience_respect": "Audience Respect",
                    "padding_vs_craft": "Padding vs Craft",
                }
                for key, label in labels.items():
                    s = scores.get(key, {})
                    tier = s.get("tier", "")
                    tier_color = {"High": "#2d7a2d", "Medium": "#a67c00", "Low": "#b03030"}.get(tier, "#888")
                    st.markdown(
                        f'**{label}** — <span style="color:{tier_color};">{tier}</span>',
                        unsafe_allow_html=True
                    )
                    st.caption(s.get("reason", ""))

        col_q, col_r = st.columns([1, 1])
        with col_q:
            if st.button("＋ Watch queue", key=f"queue_{idx}_{url[:20]}"):
                result = api_post("/queue/add", {
                    "url": url,
                    "title": title,
                    "verdict": verdict,
                })
                if result:
                    st.success("Added to queue")

        with col_r:
            with st.popover("Rate this"):
                wt = st.radio("Worth your time?", ["Yes", "No", "Skip"], key=f"wt_{idx}", horizontal=True)
                dp = st.radio("Delivered its promise?", ["Yes", "No", "Skip"], key=f"dp_{idx}", horizontal=True)
                rl = st.radio("Recommend for learning?", ["Yes", "No", "Skip"], key=f"rl_{idx}", horizontal=True)
                if st.button("Save rating", key=f"rate_{idx}"):
                    def to_bool(v):
                        return True if v == "Yes" else (False if v == "No" else None)
                    api_post("/rate", {
                        "url": url,
                        "worth_time": to_bool(wt),
                        "delivered_promise": to_bool(dp),
                        "recommend_learning": to_bool(rl),
                    })
                    st.success("Rated")

        st.markdown("---")


def render_trend_result(data: dict):
    """Render a trend assessment result."""
    if "error" in data:
        st.error(data["error"])
        return

    concern = data.get("concern_tier", "")
    color = CONCERN_COLORS.get(concern, "#888")
    confidence = data.get("confidence", "")

    st.markdown(
        f'<span style="color:{color}; font-weight:700; font-size:1.2em;">{concern}</span> '
        f'<span style="color:#888; font-size:0.9em;">· Confidence: {confidence}</span>',
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)
    st.write(data.get("summary", ""))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-label">What evidence supports this</div>', unsafe_allow_html=True)
        st.write(data.get("what_evidence_supports", ""))
    with col2:
        st.markdown('<div class="section-label">What evidence doesn\'t support this</div>', unsafe_allow_html=True)
        st.write(data.get("what_evidence_doesnt_support", ""))

    st.markdown('<div class="section-label">Real signal vs amplification</div>', unsafe_allow_html=True)
    st.write(data.get("genuine_vs_amplified", ""))

    useful = data.get("useful_action", "")
    if useful:
        st.markdown('<div class="section-label">What a reasonable person should do</div>', unsafe_allow_html=True)
        st.info(useful)

    socratic = data.get("socratic_question", "")
    if socratic:
        st.markdown('<div class="section-label">A question worth sitting with</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="socratic">{socratic}</div>',
            unsafe_allow_html=True
        )


# ── Main tab renderer ─────────────────────────────────────────────────────────

def render_rss_tab():
    """Main entry point — call this inside a st.tab('RSS Feed') block."""

    st.markdown(
        "The anti-algorithm. Scores content for epistemic quality — "
        "signal-to-noise, evergreen value, respect for your intelligence. "
        "Recency-neutral by default."
    )
    st.divider()

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    sub = st.tabs(["📡 Feed", "🔍 Score URL", "📈 Trend Check", "🎯 Skills", "⏱ Watch Queue", "⚙ Manage Feeds"])

    # ═══════════════════════════════════════════════════════════════════════════
    # FEED TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with sub[0]:
        st.markdown("**Session intent**")
        intent_label = st.selectbox(
            "What are you here to do?",
            options=list(INTENT_OPTIONS.keys()),
            format_func=lambda k: INTENT_OPTIONS[k],
            label_visibility="collapsed"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            limit_per = st.slider("Items per feed", 5, 30, 15)
        with col_b:
            total_limit = st.slider("Total items", 10, 100, 40)

        filter_skip = st.toggle("Hide Skip verdicts", value=True)

        if st.button("Load feed", type="primary"):
            with st.spinner("Fetching and scoring — this takes a moment..."):
                results = api_post("/feed", {
                    "feed_urls": [],
                    "filter_skip": filter_skip,
                    "limit_per_feed": limit_per,
                    "total_limit": total_limit,
                    "intent": intent_label,
                    "use_saved_feeds": True,
                }, timeout=180)

            if results is not None:
                if not results:
                    st.info("No results — add some feeds in the Manage Feeds tab first.")
                else:
                    passes = [r for r in results if r.get("verdict") == "Pass"]
                    watches = [r for r in results if r.get("verdict") == "Watch"]
                    skips = [r for r in results if r.get("verdict") == "Skip"]

                    st.markdown(
                        f'<span style="color:#2d7a2d;">✓ {len(passes)} Pass</span> &nbsp; '
                        f'<span style="color:#a67c00;">◎ {len(watches)} Watch</span> &nbsp; '
                        f'<span style="color:#888;">✕ {len(skips)} Skip (hidden)</span>',
                        unsafe_allow_html=True
                    )
                    st.markdown("<br>", unsafe_allow_html=True)

                    for i, item in enumerate(results):
                        render_score_card(item, i)

    # ═══════════════════════════════════════════════════════════════════════════
    # SCORE URL TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with sub[1]:
        st.markdown("Score any article or YouTube video directly.")
        url_input = st.text_input(
            "URL",
            placeholder="https://www.youtube.com/watch?v=... or https://article-url.com/..."
        )

        if st.button("Score", type="primary", disabled=not url_input.strip()):
            with st.spinner("Fetching and scoring..."):
                result = api_post("/score", {"url": url_input.strip()}, timeout=120)
            if result:
                render_score_card(result, 9999)

    # ═══════════════════════════════════════════════════════════════════════════
    # TREND CHECK TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with sub[2]:
        st.markdown(
            "Calibrated assessment of things people are worried about. "
            "Well-founded vs overblown vs algorithmically amplified."
        )
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("**Quick picks:**")
        cols = st.columns(4)
        for i, preset in enumerate(TREND_PRESETS):
            with cols[i % 4]:
                if st.button(preset, key=f"trend_preset_{i}"):
                    st.session_state["trend_topic"] = preset

        st.markdown("<br>", unsafe_allow_html=True)
        topic_input = st.text_input(
            "Or enter your own topic",
            value=st.session_state.get("trend_topic", ""),
            placeholder="e.g. AI replacing creative jobs"
        )
        context_input = st.text_area(
            "Additional context (optional)",
            placeholder="Any specific angle or framing you want considered",
            height=80
        )

        if st.button("Assess trend", type="primary", disabled=not topic_input.strip()):
            with st.spinner("Assessing..."):
                result = api_post("/assess-trend", {
                    "topic": topic_input.strip(),
                    "context": context_input.strip() or None,
                }, timeout=120)
            if result:
                st.divider()
                render_trend_result(result)

    # ═══════════════════════════════════════════════════════════════════════════
    # SKILLS TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with sub[3]:
        skill_sub = st.tabs(["Due Today", "Tag New Skill", "All Skills"])

        with skill_sub[0]:
            if st.button("Refresh", key="refresh_skills"):
                st.session_state.pop("skills_due_cache", None)

            if "skills_due_cache" not in st.session_state:
                data = api_get("/skills/due")
                st.session_state["skills_due_cache"] = data

            data = st.session_state.get("skills_due_cache", {})
            due = (data or {}).get("due_today", [])

            if not due:
                st.info("Nothing due today. Tag content as a skill to start tracking it.")
            else:
                for item in due:
                    skill_name = item.get("skill_name", "")
                    item_type = item.get("type", "")
                    days_over = item.get("days_overdue", 0)
                    source = item.get("source_url", "")
                    prompt = item.get("practice_prompt", "")
                    skill_id = item.get("skill_id")

                    overdue_label = f" — {days_over}d overdue" if days_over > 0 else ""
                    type_icon = "▶" if item_type == "rewatch" else "✎"

                    st.markdown(
                        f'**{type_icon} {skill_name}** '
                        f'<span style="color:#888; font-size:0.85em;">{item_type}{overdue_label}</span>',
                        unsafe_allow_html=True
                    )

                    if prompt:
                        st.markdown(
                            f'<div style="background:#f7f7f2; border-left:3px solid #bbb; '
                            f'padding:8px 12px; font-size:0.9em; margin:4px 0;">{prompt}</div>',
                            unsafe_allow_html=True
                        )

                    if source:
                        st.markdown(f'[Source]({source})', unsafe_allow_html=False)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✓ Retained", key=f"ret_{skill_id}_{item_type}"):
                            api_post("/skills/complete", {
                                "skill_id": skill_id,
                                "type": item_type,
                                "retained": True,
                            })
                            st.session_state.pop("skills_due_cache", None)
                            st.rerun()
                    with col2:
                        if st.button("✗ Not retained", key=f"notret_{skill_id}_{item_type}"):
                            api_post("/skills/complete", {
                                "skill_id": skill_id,
                                "type": item_type,
                                "retained": False,
                            })
                            st.session_state.pop("skills_due_cache", None)
                            st.rerun()
                    with col3:
                        if st.button("Skip today", key=f"skip_{skill_id}_{item_type}"):
                            api_post("/skills/skip-today", {
                                "skill_id": skill_id,
                                "type": item_type,
                            })
                            st.session_state.pop("skills_due_cache", None)
                            st.rerun()

                    st.markdown("---")

        with skill_sub[1]:
            st.markdown("Tag a piece of content as a skill to track with spaced repetition.")
            sk_url = st.text_input("Content URL", key="skill_url")
            sk_name = st.text_input("Skill name", placeholder="e.g. Bayesian reasoning, Python decorators")
            sk_notes = st.text_area("Practice notes (optional)", height=80)
            sk_diff = st.selectbox("Difficulty", ["", "beginner", "intermediate", "advanced"])

            if st.button("Tag as skill", type="primary", disabled=not (sk_url.strip() and sk_name.strip())):
                with st.spinner("Creating skill and generating practice prompt..."):
                    result = api_post("/skills/tag", {
                        "url": sk_url.strip(),
                        "skill_name": sk_name.strip(),
                        "practice_notes": sk_notes.strip() or None,
                        "difficulty": sk_diff or None,
                    })
                if result:
                    st.success(f"Skill tagged. First review due: {result.get('next_due', 'soon')}")

        with skill_sub[2]:
            skills = api_get("/skills/all") or []
            if not skills:
                st.info("No skills tagged yet.")
            else:
                for sk in skills:
                    completed = sum(1 for s in sk.get("schedule", []) if s.get("completed_at"))
                    total_sched = len(sk.get("schedule", []))
                    st.markdown(
                        f'**{sk["skill_name"]}** '
                        f'<span style="color:#888; font-size:0.85em;">· {completed}/{total_sched} sessions done</span>',
                        unsafe_allow_html=True
                    )
                    if sk.get("source_url"):
                        st.caption(sk["source_url"])

    # ═══════════════════════════════════════════════════════════════════════════
    # WATCH QUEUE TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with sub[4]:
        col_refresh, col_clear = st.columns([1, 1])
        with col_refresh:
            if st.button("Refresh queue"):
                st.session_state.pop("queue_cache", None)
        with col_clear:
            if st.button("Clear all", type="secondary"):
                api_post("/queue/clear", {})
                st.session_state.pop("queue_cache", None)
                st.rerun()

        if "queue_cache" not in st.session_state:
            st.session_state["queue_cache"] = api_get("/queue") or []

        queue = st.session_state["queue_cache"]

        if not queue:
            st.info("Queue is empty. Add items from the Feed or Score URL tabs.")
        else:
            for item in queue:
                item_id = item.get("id")
                title = item.get("title") or item.get("url", "Untitled")
                url = item.get("url", "")
                verdict = item.get("verdict", "")
                color = VERDICT_COLORS.get(verdict, "#888")

                col_t, col_rm = st.columns([5, 1])
                with col_t:
                    st.markdown(
                        f'<span style="color:{color}; font-size:0.85em;">{verdict}</span> '
                        f'<a href="{url}" target="_blank">{title[:80]}</a>',
                        unsafe_allow_html=True
                    )
                with col_rm:
                    if st.button("✕", key=f"rm_queue_{item_id}"):
                        if api_delete(f"/queue/{item_id}"):
                            st.session_state.pop("queue_cache", None)
                            st.rerun()

    # ═══════════════════════════════════════════════════════════════════════════
    # MANAGE FEEDS TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with sub[5]:
        st.markdown("**Add a feed**")

        add_col1, add_col2 = st.columns(2)
        with add_col1:
            new_feed_url = st.text_input(
                "RSS feed URL or YouTube channel",
                placeholder="https://... or @channelname or channel name"
            )
        with add_col2:
            new_feed_label = st.text_input("Label (optional)", placeholder="e.g. Quanta Magazine")

        col_cat, col_add = st.columns([2, 1])
        with col_cat:
            new_feed_cat = st.selectbox("Category", CATEGORIES)
        with col_add:
            st.markdown("<br>", unsafe_allow_html=True)
            add_clicked = st.button("Add feed", type="primary", disabled=not new_feed_url.strip())

        if add_clicked:
            url_to_add = new_feed_url.strip()

            # YouTube channel resolver
            if (
                "youtube.com" in url_to_add or
                "youtu.be" in url_to_add or
                url_to_add.startswith("@") or
                ("youtube" not in url_to_add and "http" not in url_to_add)
            ):
                with st.spinner("Resolving YouTube channel..."):
                    resolved = api_post("/resolve-channel", {"query": url_to_add})
                if resolved and resolved.get("found"):
                    url_to_add = resolved["rss_url"]
                    if not new_feed_label:
                        new_feed_label = resolved.get("channel_name", url_to_add)
                    st.success(f"Resolved: {resolved.get('channel_name')}")
                elif resolved:
                    st.error(resolved.get("error", "Could not resolve channel"))
                    url_to_add = None

            if url_to_add:
                result = api_post("/feeds/save", {
                    "url": url_to_add,
                    "label": new_feed_label or url_to_add,
                    "category": new_feed_cat,
                })
                if result and result.get("saved"):
                    st.success("Feed saved.")
                    st.session_state.pop("feeds_cache", None)
                    st.rerun()

        st.divider()
        st.markdown("**Saved feeds**")

        if st.button("Refresh list"):
            st.session_state.pop("feeds_cache", None)

        if "feeds_cache" not in st.session_state:
            st.session_state["feeds_cache"] = api_get("/feeds/saved") or []

        feeds = st.session_state["feeds_cache"]

        if not feeds:
            st.info("No feeds saved yet. Add one above.")
        else:
            # Group by category
            by_cat: dict[str, list] = {}
            for f in feeds:
                cat = f.get("category", "General")
                by_cat.setdefault(cat, []).append(f)

            for cat, items in sorted(by_cat.items()):
                st.markdown(f"**{cat}**")
                for f in items:
                    col_l, col_d = st.columns([5, 1])
                    with col_l:
                        label = f.get("label") or f.get("url", "")
                        st.caption(f"{label}  —  {f.get('url', '')[:60]}")
                    with col_d:
                        if st.button("✕", key=f"del_feed_{f['id']}"):
                            if api_delete(f"/feeds/saved/{f['id']}"):
                                st.session_state.pop("feeds_cache", None)
                                st.rerun()
