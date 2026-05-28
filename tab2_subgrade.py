"""
tab2_subgrade.py — Tab 2: Subgrade & k∞
Rigid Pavement Design V7
แก้ไข: DSB round nearest, กรอบ JPCP/CRCP แยกสี,
       กราฟ full width, LS=0 ซ่อน Fig.3.4, checkbox ไม่มีสัญลักษณ์
"""
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from engine import (
    calc_composite_k, calc_odemark, apply_loss_of_support,
    mr_from_cbr, plot_f33, plot_f34, plot_structure, fig_to_bytes,
    MATERIAL_MODULUS,
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

DSB_MIN, DSB_MAX = 6, 20  # มาตรฐาน nomograph

# ============================================================
# DSB rounding
# ============================================================
def _round_dsb(dsb_raw):
    """ปัด DSB เป็น nearest integer พร้อม clamp 6-20"""
    dsb_rounded = round(dsb_raw)
    warn = None
    if dsb_raw < DSB_MIN:
        warn = f'⚠️ DSB จริง ({dsb_raw:.2f} in) น้อยกว่า {DSB_MIN} in — บังคับใช้ {DSB_MIN} in'
        dsb_rounded = DSB_MIN
    elif dsb_raw > DSB_MAX:
        warn = f'⚠️ DSB จริง ({dsb_raw:.2f} in) เกิน {DSB_MAX} in — บังคับใช้ {DSB_MAX} in'
        dsb_rounded = DSB_MAX
    return dsb_rounded, warn

# ============================================================
# Helpers
# ============================================================
def _result_row(label, value, highlight=False):
    color = '#1565C0' if highlight else '#1A237E'
    st.markdown(f'''<div style="display:flex;justify-content:space-between;
        padding:4px 0;border-bottom:1px solid rgba(0,0,0,0.06);font-size:13px;">
        <span style="color:#78909C">{label}</span>
        <span style="font-family:IBM Plex Mono,monospace;font-weight:600;
              color:{color}">{value}</span></div>''', unsafe_allow_html=True)

def _metric_box(label, value, unit='', color='#1565C0', bg='#F0F7FF'):
    st.markdown(f'''<div style="background:{bg};border:1px solid rgba(0,0,0,0.08);
        border-radius:8px;padding:10px;text-align:center;margin-bottom:4px">
        <div style="font-size:11px;color:#78909C;margin-bottom:3px">{label}</div>
        <div style="font-family:IBM Plex Mono,monospace;font-size:22px;
             font-weight:700;color:{color}">{value}</div>
        <div style="font-size:11px;color:#78909C">{unit}</div>
    </div>''', unsafe_allow_html=True)

def _section_title(text, color='#1565C0'):
    st.markdown(f'''<div style="font-size:13px;font-weight:700;color:{color};
        padding:5px 0 5px;border-bottom:2px solid {color};
        margin-bottom:10px;letter-spacing:0.02em">{text}</div>''',
        unsafe_allow_html=True)

# ============================================================
# Layer input block
# ============================================================
def _layer_block(prefix, n_layers, defaults):
    mat_opts = list(MATERIAL_MODULUS.keys())
    layers = []
    ca0, cb0, cc0 = st.columns([3,1,1])
    with ca0: st.markdown('<div style="font-size:10px;color:#90A4AE;font-weight:600;padding-bottom:2px">วัสดุ</div>', unsafe_allow_html=True)
    with cb0: st.markdown('<div style="font-size:10px;color:#90A4AE;font-weight:600;padding-bottom:2px">ความหนา (ซม.)</div>', unsafe_allow_html=True)
    with cc0: st.markdown('<div style="font-size:10px;color:#90A4AE;font-weight:600;padding-bottom:2px">E (MPa)</div>', unsafe_allow_html=True)

    for i in range(n_layers):
        def_name  = st.session_state.get(f'{prefix}_name_{i}',
                    defaults[i]['name'] if i < len(defaults) else 'หินคลุก CBR 80%')
        def_thick = st.session_state.get(f'{prefix}_thick_{i}',
                    defaults[i]['thick'] if i < len(defaults) else 20)
        if def_name not in mat_opts: def_name = mat_opts[-1]
        ca, cb, cc = st.columns([3,1,1])
        with ca:
            name = st.selectbox(f'v{i}', mat_opts,
                                index=mat_opts.index(def_name),
                                key=f'{prefix}_name_{i}',
                                label_visibility='collapsed')
        with cb:
            thick = st.number_input(f't{i}', 0, 200, def_thick, step=5,
                                    key=f'{prefix}_thick_{i}',
                                    label_visibility='collapsed')
        rec_e = MATERIAL_MODULUS.get(name, 100)
        def_e = st.session_state.get(f'{prefix}_E_{i}_{name}', rec_e)
        with cc:
            e_val = st.number_input(f'e{i}', 10, 10000, def_e,
                                    key=f'{prefix}_E_{i}_{name}',
                                    label_visibility='collapsed')
        layers.append({'name':name, 'thickness_cm':thick, 'E_MPa':e_val})
    return layers

# ============================================================
# k∞ calc block (ไม่มีกราฟ — กราฟแสดง full width ด้านล่าง)
# ============================================================
def _calc_k_block(prefix, layers, MR_psi):
    od = calc_odemark([(l['thickness_cm'], l['E_MPa']) for l in layers])
    if od is None:
        st.warning('⚠️ กรุณากรอกความหนาและ E ให้ครบ')
        return None

    DSB_raw, ESB_psi = od

    # ── DSB rounding ──
    DSB_used, dsb_warn = _round_dsb(DSB_raw)
    if dsb_warn:
        st.warning(dsb_warn)

    # คำนวณ k∞ ด้วย DSB ที่ปัดแล้ว
    res = calc_composite_k(MR_psi, ESB_psi, float(DSB_used))
    k_inf = res['k_inf_pci']

    # ── LS input ──
    ls_val = st.number_input(
        'Loss of Support (LS)', 0.0, 3.0,
        st.session_state.get(f'{prefix}_ls', 1.0), 0.5,
        key=f'{prefix}_ls', format='%.1f',
        help='LS = 0: ไม่มี loss of support\nLS = 1.0: subbase granular (ทั่วไป)\nLS = 2.0-3.0: treated/stabilized base'
    )

    # ── k_eff ──
    if ls_val <= 0:
        k_eff = k_inf
    else:
        k_eff = apply_loss_of_support(k_inf, ls_val)

    # ── summary rows ──
    _result_row('DSB (Odemark จริง)', f'{DSB_raw:.2f} in')
    _result_row('DSB (ใช้จริง)', f'{DSB_used} in  ← nearest integer', highlight=True)
    _result_row('ESB equivalent', f'{ESB_psi:,.0f} psi')
    _result_row('MR (subgrade)', f'{MR_psi:,.0f} psi')

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

    if ls_val <= 0:
        # LS=0 แสดงแค่ k∞ เดียว
        _metric_box('Composite k∞ = k_eff (LS = 0)', f'{k_inf:.0f}', 'pci', '#1565C0', '#E3F2FD')
    else:
        c1, c2 = st.columns(2)
        with c1: _metric_box('Composite k∞ (Fig. 3.3)', f'{k_inf:.0f}', 'pci', '#1565C0', '#E3F2FD')
        with c2: _metric_box(f'k_eff (LS = {ls_val:.1f})', f'{k_eff:.0f}', 'pci', '#2E7D32', '#E8F5E9')

    # ── store ──
    st.session_state[f'{prefix}_k_inf']  = k_inf
    st.session_state[f'{prefix}_k_eff']  = k_eff
    st.session_state[f'{prefix}_dsb_raw']= DSB_raw
    st.session_state[f'{prefix}_dsb']    = DSB_used
    st.session_state[f'{prefix}_esb']    = ESB_psi
    st.session_state[f'{prefix}_res33']  = res
    st.session_state[f'{prefix}_ls_val'] = ls_val
    st.session_state[f'{prefix}_layers'] = layers

    # ── ปุ่มกราฟ ──
    if ls_val <= 0:
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button('📊 Fig.3.3 — k∞', key=f'btn_f33_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_f33'] = not st.session_state.get(f'{prefix}_show_f33', False)
        with col_b2:
            if st.button('🏗️ โครงสร้างชั้นทาง', key=f'btn_str_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_str'] = not st.session_state.get(f'{prefix}_show_str', False)
    else:
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            if st.button('📊 Fig.3.3 — k∞', key=f'btn_f33_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_f33'] = not st.session_state.get(f'{prefix}_show_f33', False)
        with col_b2:
            if st.button('📉 Fig.3.4 — LS', key=f'btn_f34_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_f34'] = not st.session_state.get(f'{prefix}_show_f34', False)
        with col_b3:
            if st.button('🏗️ โครงสร้างชั้นทาง', key=f'btn_str_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_str'] = not st.session_state.get(f'{prefix}_show_str', False)

    return (k_inf, k_eff, res, ls_val, layers, DSB_used, ESB_psi)

# ============================================================
# กราฟ full width (แสดงด้านล่าง 2 columns)
# ============================================================
def _render_graphs_full_width(prefix, label, MR_psi):
    res    = st.session_state.get(f'{prefix}_res33')
    ls_val = st.session_state.get(f'{prefix}_ls_val', 0)
    k_inf  = st.session_state.get(f'{prefix}_k_inf')
    k_eff  = st.session_state.get(f'{prefix}_k_eff')
    DSB    = st.session_state.get(f'{prefix}_dsb')
    ESB    = st.session_state.get(f'{prefix}_esb')
    layers = st.session_state.get(f'{prefix}_layers', [])

    if res is None or k_inf is None:
        return

    # Fig.3.3
    if st.session_state.get(f'{prefix}_show_f33'):
        st.markdown(f'<div style="background:#E3F2FD;border:1px solid #90CAF9;'
                    f'border-radius:8px;padding:8px 12px;margin-bottom:4px">'
                    f'<b>📊 AASHTO Fig. 3.3 — Composite k∞ ({label})</b></div>',
                    unsafe_allow_html=True)
        fig = plot_f33(MR_psi, ESB, DSB, res)
        st.pyplot(fig, use_container_width=True)
        st.caption(f'รูปที่ 3.3 ค่า Composite Modulus of Subgrade Reaction, k∞ — {label}')
        col_dl, col_cl = st.columns([1,4])
        with col_dl:
            st.download_button(f'⬇️ ดาวน์โหลด', fig_to_bytes(fig),
                               f'fig33_{prefix}.png', 'image/png',
                               key=f'dl_f33_{prefix}')
        with col_cl:
            if st.button('✕ ปิด Fig.3.3', key=f'close_f33_{prefix}'):
                st.session_state[f'{prefix}_show_f33'] = False
                st.rerun()
        plt.close(fig)

    # Fig.3.4 — แสดงเฉพาะ LS > 0
    if ls_val > 0 and st.session_state.get(f'{prefix}_show_f34'):
        st.markdown(f'<div style="background:#E8F5E9;border:1px solid #81C784;'
                    f'border-radius:8px;padding:8px 12px;margin-bottom:4px">'
                    f'<b>📉 AASHTO Fig. 3.4 — Loss of Support ({label})</b></div>',
                    unsafe_allow_html=True)
        fig = plot_f34(k_inf, ls_val, k_eff)
        st.pyplot(fig, use_container_width=True)
        st.caption(f'รูปที่ 3.4 k ที่ปรับแก้ด้วย Loss of Support — {label}')
        col_dl, col_cl = st.columns([1,4])
        with col_dl:
            st.download_button(f'⬇️ ดาวน์โหลด', fig_to_bytes(fig),
                               f'fig34_{prefix}.png', 'image/png',
                               key=f'dl_f34_{prefix}')
        with col_cl:
            if st.button('✕ ปิด Fig.3.4', key=f'close_f34_{prefix}'):
                st.session_state[f'{prefix}_show_f34'] = False
                st.rerun()
        plt.close(fig)

    # โครงสร้างชั้นทาง
    if st.session_state.get(f'{prefix}_show_str') and layers:
        st.markdown(f'<div style="background:#FFF8E1;border:1px solid #FFECB3;'
                    f'border-radius:8px;padding:8px 12px;margin-bottom:4px">'
                    f'<b>🏗️ โครงสร้างชั้นทาง ({label})</b></div>',
                    unsafe_allow_html=True)
        fig = plot_structure(layers, title=f'Pavement Structure — {label}')
        if fig:
            st.pyplot(fig, use_container_width=True)
            col_dl, col_cl = st.columns([1,4])
            with col_dl:
                st.download_button(f'⬇️ ดาวน์โหลด', fig_to_bytes(fig),
                                   f'structure_{prefix}.png', 'image/png',
                                   key=f'dl_str_{prefix}')
            with col_cl:
                if st.button('✕ ปิด โครงสร้าง', key=f'close_str_{prefix}'):
                    st.session_state[f'{prefix}_show_str'] = False
                    st.rerun()
            plt.close(fig)

# ============================================================
# MAIN TAB 2
# ============================================================
def render_tab2():
    # ── Subgrade card ─────────────────────────────────────────
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
    st.markdown('<div class="rp-card-title">🌍 Subgrade — ดินเดิม (ใช้ร่วมกันทั้ง JPCP และ CRCP)</div>',
                unsafe_allow_html=True)
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
            border-radius:8px;padding:8px;text-align:center;margin-top:4px">
            <div style="font-size:11px;color:#90A4AE">{formula}</div>
            <div style="font-family:IBM Plex Mono,monospace;font-size:20px;
                 font-weight:700;color:#1565C0">{MR_psi:,.0f} psi</div>
            <div style="font-size:11px;color:#90A4AE">({MR_mpa:.1f} MPa)</div>
        </div>''', unsafe_allow_html=True)
    with c3:
        st.info(f'MR = **{MR_psi:,.0f} psi** ใช้กับทั้ง JPCP และ CRCP')
    st.session_state['MR_psi'] = MR_psi
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 2 columns: JPCP (น้ำเงิน) | CRCP (เขียว) ─────────────
    col_j, col_c = st.columns(2)

    # ── JPCP/JRCP ─────────────────────────────────────────────
    with col_j:
        st.markdown('''<div style="background:#F0F7FF;
            border:2px solid #1565C0;border-left:5px solid #1565C0;
            border-radius:10px;padding:12px 14px;margin-bottom:6px">''',
            unsafe_allow_html=True)
        _section_title('🔲  JPCP / JRCP — Subbase Layers', '#1565C0')

        n_jpcp = st.slider('จำนวนชั้น JPCP', 1, 6,
                           st.session_state.get('jpcp_n', 5), key='jpcp_n')
        layers_jpcp = _layer_block('jpcp', n_jpcp, _DEF_JPCP)
        total_jpcp  = sum(l['thickness_cm'] for l in layers_jpcp if l['thickness_cm'] > 0)
        st.caption(f'รวมความหนา subbase = **{total_jpcp} ซม.**')
        st.markdown('<hr style="border:none;border-top:1px solid #BBDEFB;margin:8px 0">',
                    unsafe_allow_html=True)
        result_jpcp = _calc_k_block('jpcp', layers_jpcp, MR_psi)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── CRCP ──────────────────────────────────────────────────
    with col_c:
        st.markdown('''<div style="background:#F1F8E9;
            border:2px solid #2E7D32;border-left:5px solid #2E7D32;
            border-radius:10px;padding:12px 14px;margin-bottom:6px">''',
            unsafe_allow_html=True)
        _section_title('〰️  CRCP — Subbase Layers', '#2E7D32')

        copy_jpcp = st.checkbox(
            'ใช้ค่าเดียวกับ JPCP/JRCP',
            value=st.session_state.get('crcp_copy', False),
            key='crcp_copy',
            help='ติ๊กเพื่อ copy layers จาก JPCP/JRCP มาใช้กับ CRCP'
        )

        if copy_jpcp:
            layers_crcp = layers_jpcp
            st.markdown('<div style="font-size:12px;color:#2E7D32;'
                        'background:#E8F5E9;border-radius:6px;padding:6px 10px;'
                        'margin-bottom:8px">✅ ใช้ชั้นวัสดุเดียวกับ JPCP/JRCP</div>',
                        unsafe_allow_html=True)
        else:
            n_crcp = st.slider('จำนวนชั้น CRCP', 1, 6,
                               st.session_state.get('crcp_n', 3), key='crcp_n')
            layers_crcp = _layer_block('crcp', n_crcp, _DEF_CRCP)

        total_crcp = sum(l['thickness_cm'] for l in layers_crcp if l['thickness_cm'] > 0)
        st.caption(f'รวมความหนา subbase = **{total_crcp} ซม.**')
        st.markdown('<hr style="border:none;border-top:1px solid #A5D6A7;margin:8px 0">',
                    unsafe_allow_html=True)
        result_crcp = _calc_k_block('crcp', layers_crcp, MR_psi)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── กราฟ full width ด้านล่าง ─────────────────────────────
    _render_graphs_full_width('jpcp', 'JPCP/JRCP', MR_psi)
    _render_graphs_full_width('crcp', 'CRCP', MR_psi)

    # ── สรุป k_eff ส่งต่อ Tab 3 ──────────────────────────────
    k_eff_j = st.session_state.get('jpcp_k_eff')
    k_eff_c = st.session_state.get('crcp_k_eff')
    if k_eff_j or k_eff_c:
        st.markdown('''<div style="background:#E8F5E9;border:1.5px solid #A5D6A7;
            border-radius:8px;padding:8px 14px;margin-top:8px">
            <div style="font-size:12px;font-weight:700;color:#2E7D32;
                 margin-bottom:8px">✅ สรุป k_eff → ส่งต่อ Tab 3 Design</div>''',
            unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)
        with sc1:
            if k_eff_j:
                _metric_box('k_eff — JPCP/JRCP', f'{k_eff_j:.0f}', 'pci', '#1565C0', '#E3F2FD')
        with sc2:
            if k_eff_c:
                _metric_box('k_eff — CRCP', f'{k_eff_c:.0f}', 'pci', '#2E7D32', '#E8F5E9')
        st.markdown('</div>', unsafe_allow_html=True)
