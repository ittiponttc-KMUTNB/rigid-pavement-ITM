"""
app.py — Rigid Pavement Design V7
AASHTO 1993 — JPCP/JRCP & CRCP
พัฒนาโดย รศ.ดร.อิทธิพล มีผล · ภาควิชาครุศาสตร์โยธา · มจพ.

Run: streamlit run app.py
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from tab1_traffic import render_tab1
from tab2_subgrade import render_tab2
from tab3_design import render_tab3
from tab4_report import render_tab4

# ============================================================
# CSS
# ============================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Sarabun:wght@300;400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #EEF2F7 !important;
    font-family: 'Sarabun', sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 0.5rem; }

/* ── Header ── */
.rp-header {
    background: #1565C0;
    border-radius: 10px;
    padding: 14px 20px 10px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.rp-header-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 15px; color: #FFFFFF;
    font-weight: 600; letter-spacing: 0.05em;
}
.rp-header-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; color: #BBDEFB; margin-top: 3px;
}
.rp-badge {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 6px; padding: 4px 12px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; color: #FFFFFF;
}

/* ── st.container(border=True) → style เป็น rp-card ── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border: 0.5px solid #E0E0E0 !important;
    border-left: 4px solid #1565C0 !important;
    border-radius: 0 8px 8px 0 !important;
    padding: 2px 6px !important;
    margin-bottom: 8px !important;
}

/* ── Card title (ใช้ใน _card_title helper) ── */
.rp-card-title {
    font-size: 13px; font-weight: 600; color: #1565C0;
    margin-bottom: 10px; padding-bottom: 6px;
    border-bottom: 0.5px solid #E0E0E0;
}

/* ── Metrics ── */
.rp-metric {
    background: #E3F2FD;
    border: 0.5px solid #90CAF9;
    border-radius: 8px;
    padding: 8px 10px; text-align: center;
}
.rp-metric-label { font-size: 11px; color: #546E7A; margin-bottom: 3px; }
.rp-metric-val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 18px; font-weight: 600; color: #1565C0;
}

/* ── Status ── */
.rp-status-ok {
    background: #E8F5E9; border: 1px solid #A5D6A7;
    border-radius: 8px; padding: 7px 12px;
    font-size: 13px; color: #2E7D32; font-weight: 600;
}
.rp-status-warn {
    background: #FFF8E1; border: 1px solid #FFD54F;
    border-radius: 8px; padding: 7px 12px;
    font-size: 13px; color: #E65100; font-weight: 600;
}
.rp-status-info {
    background: #E3F2FD; border: 1px solid #90CAF9;
    border-radius: 8px; padding: 7px 12px;
    font-size: 13px; color: #1565C0;
}

/* ── Tabs ── */
div[data-testid="stTabs"] button {
    font-weight: 600 !important; color: #546E7A !important;
    font-size: 13px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #1565C0 !important;
    border-bottom: 3px solid #1565C0 !important;
}

/* ── Section label ── */
.rp-section-label {
    font-size: 11px; font-weight: 600; color: #90A4AE;
    letter-spacing: 0.07em; text-transform: uppercase;
    margin-bottom: 6px; margin-top: 8px;
}
</style>
"""

# ============================================================
# MAIN
# ============================================================
def main():
    st.set_page_config(
        page_title='Rigid Pavement Design V7 — AASHTO 1993',
        page_icon='🛣️', layout='wide'
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Session State Init ───────────────────────────────────
    defaults = {
        'project_name': '',
        'esal_data': None, 'esal_file_id': None,
        'cbr': 4.0, 'MR_psi': 6000,
        'pt': 2.0, 'reliability': 90, 'so': 0.35,
        'jpcp_k_inf': None, 'jpcp_k_eff': None, 'jpcp_ls': 1.0,
        'crcp_k_inf': None, 'crcp_k_eff': None, 'crcp_ls': 1.0,
        'crcp_copy': False,
        'jpcp_d_cm': 30, 'crcp_d_cm': 25,
        '_do_reset_pt': False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Header ───────────────────────────────────────────────
    proj = st.session_state.get('project_name', '') or '— ยังไม่ระบุโครงการ'
    st.markdown(f'''
    <div class="rp-header">
        <div>
            <div class="rp-header-title">🛣️ Rigid Pavement Design — AASHTO 1993</div>
            <div class="rp-header-sub">ภาควิชาครุศาสตร์โยธา · มจพ. · Version 7.0</div>
        </div>
        <div class="rp-badge">📁 {proj}</div>
    </div>''', unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        '🚦 Tab 1 — Traffic & ESAL',
        '🪨 Tab 2 — Subgrade & k∞',
        '🏗️ Tab 3 — Design',
        '📄 Tab 4 — Report',
    ])

    with tab1:
        render_tab1()

    with tab2:
        render_tab2()

    with tab3:
        render_tab3()

    with tab4:
        render_tab4()

    st.markdown('---')
    st.caption('พัฒนาโดย รศ.ดร.อิทธิพล มีผล · ภาควิชาครุศาสตร์โยธา · มจพ.')

if __name__ == '__main__':
    main()
