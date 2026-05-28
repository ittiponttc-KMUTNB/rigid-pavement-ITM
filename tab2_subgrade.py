"""
tab2_subgrade.py — Tab 2: Subgrade & k∞
Rigid Pavement Design V7
"""
import streamlit as st
import numpy as np
from engine import (
    calc_composite_k, calc_odemark, apply_loss_of_support,
    mr_from_cbr, plot_f33, plot_f34, plot_structure, fig_to_bytes,
    MATERIAL_MODULUS, LAYER_COLORS, LAYER_NAMES_EN,
)

# ── default layer presets ────────────────────────────────────
_DEF_JPCP = [
    {'name':'รองผิวทางคอนกรีตด้วย AC',                   'thick':5},
    {'name':'หินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (CTB)', 'thick':20},
    {'name':'หินคลุก CBR 80%',                            'thick':15},
    {'name':'รองพื้นทางวัสดุมวลรวม CBR 25%',             'thick':25},
    {'name':'วัสดุคัดเลือก ก',                            'thick':30},
]
_DEF_CRCP = [
    {'name':'หินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (CTB)', 'thick':10},
    {'name':'รองพื้นทางวัสดุมวลรวม CBR 25%',             'thick':15},
    {'name':'วัสดุคัดเลือก ก',                            'thick':20},
]

# ── helpers ──────────────────────────────────────────────────
def _result_row(label, value):
    st.markdown(f'''<div style="display:flex;justify-content:space-between;
        padding:4px 0;border-bottom:1px solid #FFF3CD;font-size:13px;">
        <span style="color:#90A4AE">{label}</span>
        <span style="font-family:IBM Plex Mono,monospace;font-weight:600;
              color:#1A237E">{value}</span></div>''', unsafe_allow_html=True)

def _metric_box(label, value, unit='', color='#1565C0'):
    st.markdown(f'''<div style="background:#FFF3CD;border:1px solid #FFECB3;
        border-radius:8px;padding:10px;text-align:center;margin-bottom:6px">
        <div style="font-size:11px;color:#90A4AE;margin-bottom:3px">{label}</div>
        <div style="font-family:IBM Plex Mono,monospace;font-size:22px;
             font-weight:700;color:{color}">{value}</div>
        <div style="font-size:11px;color:#90A4AE">{unit}</div>
    </div>''', unsafe_allow_html=True)

def _section_title(text, icon=''):
    st.markdown(f'''<div style="font-size:13px;font-weight:600;color:#1565C0;
        padding:6px 0 4px;border-bottom:1px solid #FFECB3;margin-bottom:8px">
        {icon} {text}</div>''', unsafe_allow_html=True)

def _card_open(border_color='#FFECB3'):
    st.markdown(f'<div style="background:#FFF8E1;border:1px solid {border_color};'
                f'border-radius:8px;padding:8px 12px;margin-bottom:6px">',
                unsafe_allow_html=True)

def _card_close():
    st.markdown('</div>', unsafe_allow_html=True)

# ── layer input block ─────────────────────────────────────────
def _layer_block(prefix, n_layers, defaults):
    mat_opts = list(MATERIAL_MODULUS.keys())
    layers = []
    col_h1, col_h2, col_h3 = st.columns([3,1,1])
    with col_h1: st.markdown('<div style="font-size:11px;color:#90A4AE;font-weight:600">วัสดุ</div>', unsafe_allow_html=True)
    with col_h2: st.markdown('<div style="font-size:11px;color:#90A4AE;font-weight:600">ความหนา (ซม.)</div>', unsafe_allow_html=True)
    with col_h3: st.markdown('<div style="font-size:11px;color:#90A4AE;font-weight:600">E (MPa)</div>', unsafe_allow_html=True)

    for i in range(n_layers):
        def_name  = st.session_state.get(f'{prefix}_name_{i}',
                    defaults[i]['name'] if i < len(defaults) else 'หินคลุก CBR 80%')
        def_thick = st.session_state.get(f'{prefix}_thick_{i}',
                    defaults[i]['thick'] if i < len(defaults) else 20)
        if def_name not in mat_opts: def_name = mat_opts[-1]
        idx = mat_opts.index(def_name)
        ca, cb, cc = st.columns([3,1,1])
        with ca:
            name = st.selectbox(f'วัสดุ {i+1}', mat_opts, index=idx,
                                key=f'{prefix}_name_{i}', label_visibility='collapsed')
        with cb:
            thick = st.number_input(f'ซม. {i+1}', 0, 200, def_thick, step=5,
                                    key=f'{prefix}_thick_{i}', label_visibility='collapsed')
        rec_e = MATERIAL_MODULUS.get(name, 100)
        def_e = st.session_state.get(f'{prefix}_E_{i}_{name}', rec_e)
        with cc:
            e_val = st.number_input(f'E {i+1}', 10, 10000, def_e,
                                    key=f'{prefix}_E_{i}_{name}', label_visibility='collapsed')
        layers.append({'name':name, 'thickness_cm':thick, 'E_MPa':e_val})
    return layers

# ── k∞ calculation block (Fig3.3 + Fig3.4) ──────────────────
def _calc_k_block(prefix, layers, MR_psi, label):
    """คำนวณ k∞ และ k_eff — returns (k_inf, k_eff) หรือ None"""
    od = calc_odemark([(l['thickness_cm'], l['E_MPa']) for l in layers])
    if od is None:
        st.warning('⚠️ กรุณากรอกความหนาและ E ให้ครบ')
        return None

    DSB_in, ESB_psi = od
    res = calc_composite_k(MR_psi, ESB_psi, DSB_in)
    k_inf = res['k_inf_pci']

    # ── LS input ──
    ls_val = st.number_input(
        'Loss of Support (LS)', 0.0, 3.0,
        st.session_state.get(f'{prefix}_ls', 1.0), 0.5,
        key=f'{prefix}_ls', format='%.1f',
        help='LS = 0: ไม่มี loss | LS = 1: subbase granular | LS = 2-3: treated base'
    )
    k_eff = apply_loss_of_support(k_inf, ls_val)

    # ── summary rows ──
    _result_row('DSB equivalent', f'{DSB_in:.2f} in')
    _result_row('ESB equivalent', f'{ESB_psi:,.0f} psi')
    _result_row('MR (subgrade)', f'{MR_psi:,.0f} psi')

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1: _metric_box('Composite k∞ (Fig. 3.3)', f'{k_inf:.0f}', 'pci', '#1565C0')
    with c2: _metric_box(f'k_eff (LS = {ls_val:.1f})', f'{k_eff:.0f}', 'pci', '#2E7D32')

    # ── store ──
    st.session_state[f'{prefix}_k_inf'] = k_inf
    st.session_state[f'{prefix}_k_eff'] = k_eff
    st.session_state[f'{prefix}_dsb']   = DSB_in
    st.session_state[f'{prefix}_esb']   = ESB_psi
    st.session_state[f'{prefix}_res33'] = res

    # ── nomograph buttons ──
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button(f'📊 Fig.3.3 — k∞', key=f'btn_f33_{prefix}', use_container_width=True):
            st.session_state[f'{prefix}_show_f33'] = True
    with col_b2:
        if st.button(f'📉 Fig.3.4 — LS', key=f'btn_f34_{prefix}', use_container_width=True):
            st.session_state[f'{prefix}_show_f34'] = True
    with col_b3:
        if st.button(f'🏗️ โครงสร้างชั้นทาง', key=f'btn_str_{prefix}', use_container_width=True):
            st.session_state[f'{prefix}_show_str'] = True

    # ── แสดง Fig.3.3 ──
    if st.session_state.get(f'{prefix}_show_f33'):
        with st.expander('📊 AASHTO Fig. 3.3 — Composite k∞', expanded=True):
            fig = plot_f33(MR_psi, ESB_psi, DSB_in, res)
            st.pyplot(fig, use_container_width=True)
            st.caption(f'รูปที่ 3.3 ค่า Composite Modulus of Subgrade Reaction, k∞ — {label}')
            plt_bytes = fig_to_bytes(fig)
            st.download_button(f'⬇️ ดาวน์โหลด Fig.3.3 ({label})', plt_bytes,
                               f'fig33_{prefix}.png', 'image/png',
                               key=f'dl_f33_{prefix}')
            if st.button('✕ ปิด', key=f'close_f33_{prefix}'):
                st.session_state[f'{prefix}_show_f33'] = False
                st.rerun()
            import matplotlib.pyplot as plt
            plt.close(fig)

    # ── แสดง Fig.3.4 ──
    if st.session_state.get(f'{prefix}_show_f34'):
        with st.expander('📉 AASHTO Fig. 3.4 — Loss of Support', expanded=True):
            fig = plot_f34(k_inf, ls_val, k_eff)
            st.pyplot(fig, use_container_width=True)
            st.caption(f'รูปที่ 3.4 ค่า k ที่ปรับแก้ด้วย Loss of Support — {label}')
            plt_bytes = fig_to_bytes(fig)
            st.download_button(f'⬇️ ดาวน์โหลด Fig.3.4 ({label})', plt_bytes,
                               f'fig34_{prefix}.png', 'image/png',
                               key=f'dl_f34_{prefix}')
            if st.button('✕ ปิด', key=f'close_f34_{prefix}'):
                st.session_state[f'{prefix}_show_f34'] = False
                st.rerun()
            import matplotlib.pyplot as plt
            plt.close(fig)

    # ── แสดงโครงสร้างชั้นทาง ──
    if st.session_state.get(f'{prefix}_show_str'):
        with st.expander('🏗️ โครงสร้างชั้นทาง', expanded=True):
            fig = plot_structure(layers, concrete_cm=None,
                                 title=f'Pavement Structure — {label}')
            if fig:
                st.pyplot(fig, use_container_width=True)
                plt_bytes = fig_to_bytes(fig)
                st.download_button(f'⬇️ ดาวน์โหลดรูป ({label})', plt_bytes,
                                   f'structure_{prefix}.png', 'image/png',
                                   key=f'dl_str_{prefix}')
                if st.button('✕ ปิด', key=f'close_str_{prefix}'):
                    st.session_state[f'{prefix}_show_str'] = False
                    st.rerun()
                import matplotlib.pyplot as plt
                plt.close(fig)

    return (k_inf, k_eff)

# ============================================================
# MAIN TAB 2 FUNCTION
# ============================================================
def render_tab2():
    # ── Subgrade ─────────────────────────────────────────────
    _card_open()
    _section_title('Subgrade — ดินเดิม', '🌍')
    c1, c2, c3 = st.columns(3)
    with c1:
        cbr = st.number_input('CBR (%)', 1.0, 30.0,
                              st.session_state.get('cbr', 4.0), 0.5,
                              key='cbr', format='%.1f')
    MR_psi = mr_from_cbr(cbr)
    MR_mpa = MR_psi / 145.038
    formula = 'MR = 1,500 × CBR' if cbr < 10 else 'MR = 1,000 + 555 × CBR'
    with c2:
        st.markdown(f'''<div style="background:#FFF3CD;border:1px solid #FFECB3;
            border-radius:8px;padding:8px;text-align:center;margin-top:8px">
            <div style="font-size:11px;color:#90A4AE">{formula}</div>
            <div style="font-family:IBM Plex Mono,monospace;font-size:20px;
                 font-weight:700;color:#1565C0">{MR_psi:,.0f} psi</div>
            <div style="font-size:11px;color:#90A4AE">({MR_mpa:.1f} MPa)</div>
        </div>''', unsafe_allow_html=True)
    with c3:
        st.info(f'MR ที่ใช้ในทั้ง JPCP และ CRCP = **{MR_psi:,.0f} psi**')
    st.session_state['MR_psi'] = MR_psi
    _card_close()

    # ── JPCP/JRCP & CRCP — 2 columns ─────────────────────────
    col_j, col_c = st.columns(2)

    # ── JPCP/JRCP ────────────────────────────────────────────
    with col_j:
        st.markdown('''<div style="background:#F5F9FE;border:1.5px solid #90CAF9;
            border-radius:10px;padding:10px 14px;margin-bottom:6px">''',
            unsafe_allow_html=True)
        _section_title('JPCP / JRCP — Subbase Layers', '🔲')

        n_jpcp = st.slider('จำนวนชั้น', 1, 6,
                           st.session_state.get('jpcp_n', 5),
                           key='jpcp_n', help='JPCP/JRCP')
        layers_jpcp = _layer_block('jpcp', n_jpcp, _DEF_JPCP)
        total_jpcp  = sum(l['thickness_cm'] for l in layers_jpcp)
        st.caption(f'รวมความหนา subbase = **{total_jpcp} ซม.**')

        st.markdown('<hr style="border:none;border-top:1px solid #BBDEFB;margin:6px 0">', unsafe_allow_html=True)
        _calc_k_block('jpcp', layers_jpcp, MR_psi, 'JPCP/JRCP')
        st.markdown('</div>', unsafe_allow_html=True)

    # ── CRCP ─────────────────────────────────────────────────
    with col_c:
        st.markdown('''<div style="background:#F5F9FE;border:1.5px solid #90CAF9;
            border-radius:10px;padding:10px 14px;margin-bottom:6px">''',
            unsafe_allow_html=True)
        _section_title('CRCP — Subbase Layers', '〰️')

        # checkbox copy จาก JPCP
        copy_jpcp = st.checkbox('☑ ใช้ค่าเดียวกับ JPCP/JRCP',
                                value=st.session_state.get('crcp_copy', False),
                                key='crcp_copy')

        if copy_jpcp:
            # copy layers จาก JPCP
            layers_crcp = layers_jpcp
            st.info('ใช้ชั้นวัสดุเดียวกับ JPCP/JRCP')
            # sync layer session state
            for i, l in enumerate(layers_crcp):
                st.session_state[f'crcp_name_{i}']  = l['name']
                st.session_state[f'crcp_thick_{i}'] = l['thickness_cm']
                st.session_state[f'crcp_E_{i}_{l["name"]}'] = l['E_MPa']
            n_crcp = len(layers_crcp)
        else:
            n_crcp = st.slider('จำนวนชั้น', 1, 6,
                               st.session_state.get('crcp_n', 3),
                               key='crcp_n', help='CRCP')
            layers_crcp = _layer_block('crcp', n_crcp, _DEF_CRCP)

        total_crcp = sum(l['thickness_cm'] for l in layers_crcp)
        st.caption(f'รวมความหนา subbase = **{total_crcp} ซม.**')

        st.markdown('<hr style="border:none;border-top:1px solid #BBDEFB;margin:6px 0">', unsafe_allow_html=True)
        _calc_k_block('crcp', layers_crcp, MR_psi, 'CRCP')
        st.markdown('</div>', unsafe_allow_html=True)

    # ── สรุป k_eff ส่งต่อ Tab 3 ──────────────────────────────
    k_eff_j = st.session_state.get('jpcp_k_eff')
    k_eff_c = st.session_state.get('crcp_k_eff')
    if k_eff_j or k_eff_c:
        _card_open('#A5D6A7')
        _section_title('สรุป k_eff → ส่งต่อ Tab 3 Design', '✅')
        sc1, sc2 = st.columns(2)
        with sc1:
            if k_eff_j:
                _metric_box('k_eff — JPCP/JRCP', f'{k_eff_j:.0f}', 'pci', '#1565C0')
        with sc2:
            if k_eff_c:
                _metric_box('k_eff — CRCP', f'{k_eff_c:.0f}', 'pci', '#2E7D32')
        _card_close()
