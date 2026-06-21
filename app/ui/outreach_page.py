"""Outreach expander widget — used inside profile tabs and competitor cards."""

import streamlit as st

from app.agents.outreach_agent import (
    generate_email_draft,
    generate_enhanced_draft,
    generate_followup_sequence,
    generate_linkedin_message,
    generate_objection_prep,
    parse_email,
)
from app.db import (
    delete_email_draft,
    load_drafts_for_company,
    save_email_draft,
)

from .badges import render_diff


def render_email_expander(profile: dict, key_prefix: str):
    company = profile.get("company_name", "unknown")
    with st.expander("✉️ Outreach & Email Drafts"):

        tab_single, tab_sequence, tab_linkedin, tab_objections = st.tabs(
            ["📧 Cold Email", "🔁 Follow-up Sequence", "💼 LinkedIn DM", "🛡 Objection Prep"]
        )

        # ── Tab 1: Cold Email ─────────────────────────────
        with tab_single:
            st.markdown("#### ✏️ Generate Draft")
            tone = st.radio("Tone", ["formal","friendly","bold"], horizontal=True, key=f"tone_{key_prefix}")
            if st.button("Generate Email", key=f"gen_email_{key_prefix}"):
                with st.spinner("Writing…"):
                    try:
                        raw = generate_email_draft(profile, tone)
                        subj, body = parse_email(raw)
                        st.session_state[f"draft_subject_{key_prefix}"] = subj
                        st.session_state[f"draft_body_{key_prefix}"]    = body
                    except Exception as e:
                        st.error(f"Failed: {e}")

            subj_val = st.session_state.get(f"draft_subject_{key_prefix}", "")
            body_val = st.session_state.get(f"draft_body_{key_prefix}", "")
            if body_val:
                if subj_val: st.markdown(f"**Subject:** {subj_val}")
                edited = st.text_area("Body", value=body_val, height=200, key=f"email_body_{key_prefix}")
                if st.button("💾 Save", key=f"save_draft_{key_prefix}"):
                    save_email_draft(company, subj_val, edited, tone)
                    st.success("Draft saved")
                    st.rerun()

            saved_rows = load_drafts_for_company(company)
            if saved_rows:
                st.divider()
                st.markdown("#### 📂 Saved Drafts")
                opts = {f"#{r['id']} · {r['tone']} · {'⚡' if r['is_enhanced'] else '🖊'} · {r['created_at']}": r
                        for r in saved_rows}
                sel_label = st.selectbox("Base draft", list(opts.keys()), key=f"base_select_{key_prefix}")
                sel       = dict(opts[sel_label])
                with st.container(border=True):
                    st.caption(f"Subject: {sel.get('subject','—')}")
                    st.text(sel["body"])
                col_del, _ = st.columns([1,4])
                with col_del:
                    if st.button("🗑 Delete", key=f"del_draft_{key_prefix}"):
                        delete_email_draft(sel["id"]); st.rerun()
                st.divider()
                st.markdown("#### 🚀 Enhance from Base")
                enh_tone = st.radio("Tone", ["formal","friendly","bold"], horizontal=True, key=f"enh_tone_{key_prefix}")
                instr = st.text_area("Instructions", placeholder="e.g. More urgent opening, add a stat…",
                                     height=80, key=f"enh_instr_{key_prefix}")
                if st.button("✨ Enhance", key=f"enh_btn_{key_prefix}") and instr.strip():
                    with st.spinner("Enhancing…"):
                        try:
                            raw_enh = generate_enhanced_draft(profile, sel.get("subject",""), sel["body"], instr, enh_tone)
                            es, eb  = parse_email(raw_enh)
                            st.session_state[f"enh_subject_{key_prefix}"] = es
                            st.session_state[f"enh_body_{key_prefix}"]    = eb
                            st.session_state[f"enh_base_{key_prefix}"]    = sel["id"]
                        except Exception as e:
                            st.error(f"Failed: {e}")
                eb_val = st.session_state.get(f"enh_body_{key_prefix}", "")
                es_val = st.session_state.get(f"enh_subject_{key_prefix}", "")
                if eb_val:
                    st.markdown("##### 🔍 Diff")
                    render_diff(sel["body"], eb_val)
                    st.markdown(f"**Subject:** {es_val}")
                    eb_edit = st.text_area("Enhanced body", value=eb_val, height=180, key=f"enh_edit_{key_prefix}")
                    if st.button("💾 Save enhanced", key=f"save_enh_{key_prefix}"):
                        save_email_draft(company, es_val, eb_edit, enh_tone, is_enhanced=True,
                                         base_draft_id=st.session_state.get(f"enh_base_{key_prefix}"))
                        st.success("Enhanced draft saved!")
                        for k in (f"enh_body_{key_prefix}", f"enh_subject_{key_prefix}", f"enh_base_{key_prefix}"):
                            st.session_state.pop(k, None)
                        st.rerun()

        # ── Tab 2: Follow-up Sequence ─────────────────────
        with tab_sequence:
            st.markdown("#### 🔁 3-Touch Follow-up Sequence")
            seq_tone = st.radio("Tone", ["formal","friendly","bold"], horizontal=True, key=f"seq_tone_{key_prefix}")
            if st.button("Generate Sequence", key=f"gen_seq_{key_prefix}"):
                with st.spinner("Writing 3-email sequence…"):
                    try:
                        seq = generate_followup_sequence(profile, seq_tone)
                        st.session_state[f"sequence_{key_prefix}"] = seq
                    except Exception as e:
                        st.error(f"Failed: {e}")
            seq = st.session_state.get(f"sequence_{key_prefix}", [])
            if seq:
                for email in seq:
                    with st.container(border=True):
                        st.markdown(f"**Touch {email.get('touch')} — {email.get('send_gap')}**")
                        st.markdown(f"*Subject: {email.get('subject','')}*")
                        st.text_area("Body", value=email.get("body",""), height=140,
                                     key=f"seq_body_{key_prefix}_{email.get('touch')}")
                        if st.button(f"💾 Save touch {email.get('touch')}", key=f"save_seq_{key_prefix}_{email.get('touch')}"):
                            save_email_draft(company, email.get("subject",""), email.get("body",""),
                                             seq_tone + f"_touch{email.get('touch')}")
                            st.success(f"Touch {email.get('touch')} saved")

        # ── Tab 3: LinkedIn DM ────────────────────────────
        with tab_linkedin:
            st.markdown("#### 💼 LinkedIn Connection Note")
            st.caption("Max 300 characters — optimised for LinkedIn DMs.")
            if st.button("Generate LinkedIn Message", key=f"gen_li_{key_prefix}"):
                with st.spinner("Writing…"):
                    try:
                        msg = generate_linkedin_message(profile)
                        st.session_state[f"li_msg_{key_prefix}"] = msg
                    except Exception as e:
                        st.error(f"Failed: {e}")
            li_msg = st.session_state.get(f"li_msg_{key_prefix}", "")
            if li_msg:
                edited_li = st.text_area("Message", value=li_msg, height=100, key=f"li_edit_{key_prefix}")
                char_count = len(edited_li)
                color = "green" if char_count <= 300 else "red"
                st.markdown(f'<span style="color:{color};font-size:.8rem;">{char_count}/300 characters</span>',
                            unsafe_allow_html=True)
                if st.button("💾 Save LinkedIn message", key=f"save_li_{key_prefix}"):
                    save_email_draft(company, "LinkedIn DM", edited_li, "linkedin")
                    st.success("Saved")

        # ── Tab 4: Objection Prep ─────────────────────────
        with tab_objections:
            st.markdown("#### 🛡 Objection Handling Prep")
            if st.button("Generate Objections & Rebuttals", key=f"gen_obj_{key_prefix}"):
                with st.spinner("Generating…"):
                    try:
                        objs = generate_objection_prep(profile)
                        st.session_state[f"objections_{key_prefix}"] = objs
                    except Exception as e:
                        st.error(f"Failed: {e}")
            objs = st.session_state.get(f"objections_{key_prefix}", [])
            if objs:
                for i, item in enumerate(objs, 1):
                    with st.container(border=True):
                        st.markdown(f"**Objection {i}:** {item.get('objection','')}")
                        st.markdown(f"**Rebuttal:** {item.get('rebuttal','')}")
