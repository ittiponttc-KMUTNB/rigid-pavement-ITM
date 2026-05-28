"""
tab2_subgrade.py — Tab 2: Subgrade & k∞
Rigid Pavement Design V7
Layout: Row A = layers, Row B = k∞/LS/กราฟ (ซ้าย=JPCP, ขวา=CRCP)
"""
import streamlit as st
import matplotlib.pyplot as plt
from engine import (
    calc_composite_k, calc_odemark, apply_loss_of_support,
    mr_from_cbr, plot_f33, plot_f34, plot_structure, fig_to_bytes,
    MATERIAL_MODULUS,
)

DSB_MIN, DSB_MAX = 6, 20

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

# ── CSS card สี ──────────────────────────────────────────────
_JPCP_BG   = '#F0F7FF'
_JPCP_BD   = '#1565C0'
_JPCP_BDLT = '#90CAF9'
_CRCP_BG   = '#F1F8E9'
_CRCP_BD   = '#2E7D32'
_CRCP_BDLT = '#A5D6A7'

# ============================================================
# Helpers
# ============================================================
def _round_dsb(dsb_raw):
    dsb_rounded = round(dsb_raw)
    warn = None
    if dsb_raw < DSB_MIN:
        warn = f'⚠️ DSB จริง ({dsb_raw:.2f} in) น้อยกว่า {DSB_MIN} in — บังคับใช้ {DSB_MIN} in'
        dsb_rounded = DSB_MIN
    elif dsb_raw > DSB_MAX:
        warn = f'⚠️ DSB จริง ({dsb_raw:.2f} in) เกิน {DSB_MAX} in — บังคับใช้ {DSB_MAX} in'
        dsb_rounded = DSB_MAX
    return dsb_rounded, warn

def _row(label, value, hi=False):
    c = '#1565C0' if hi else '#1A237E'
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;'
        f'padding:3px 0;border-bottom:1px solid rgba(0,0,0,0.06);font-size:12px">'
        f'<span style="color:#78909C">{label}</span>'
        f'<span style="font-family:IBM Plex Mono,monospace;font-weight:600;color:{c}">'
        f'{value}</span></div>', unsafe_allow_html=True)

def _mbox(label, value, unit='', vc='#1565C0', bg='#E3F2FD'):
    st.markdown(
        f'<div style="background:{bg};border:1px solid rgba(0,0,0,0.08);'
        f'border-radius:7px;padding:8px;text-align:center;margin-bottom:4px">'
        f'<div style="font-size:10px;color:#78909C;margin-bottom:2px">{label}</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
        f'font-weight:700;color:{vc}">{value}</div>'
        f'<div style="font-size:10px;color:#78909C">{unit}</div></div>',
        unsafe_allow_html=True)

def _title(text, color, border):
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{color};'
        f'padding:4px 0 5px;border-bottom:2px solid {border};'
        f'margin-bottom:8px">{text}</div>', unsafe_allow_html=True)

def _card(bg, bd):
    st.markdown(
        f'<div style="background:{bg};border:2px solid {bd};'
        f'border-left:5px solid {bd};border-radius:10px;'
        f'padding:10px 12px;margin-bottom:6px">', unsafe_allow_html=True)

def _end(): st.markdown('</div>', unsafe_allow_html=True)

def _hr(color): st.markdown(
    f'<hr style="border:none;border-top:1px solid {color};margin:6px 0">',
    unsafe_allow_html=True)

# ============================================================
# Layer block
# ============================================================
def _layers(prefix, n, defaults):
    mat = list(MATERIAL_MODULUS.keys())
    result = []
    c0,c1,c2 = st.columns([3,1,1])
    with c0: st.markdown('<div style="font-size:10px;color:#90A4AE;font-weight:600">วัสดุ</div>', unsafe_allow_html=True)
    with c1: st.markdown('<div style="font-size:10px;color:#90A4AE;font-weight:600">ซม.</div>', unsafe_allow_html=True)
    with c2: st.markdown('<div style="font-size:10px;color:#90A4AE;font-weight:600">E (MPa)</div>', unsafe_allow_html=True)
    for i in range(n):
        dn = st.session_state.get(f'{prefix}_name_{i}',
             defaults[i]['name'] if i<len(defaults) else 'หินคลุก CBR 80%')
        dt = st.session_state.get(f'{prefix}_thick_{i}',
             defaults[i]['thick'] if i<len(defaults) else 20)
        if dn not in mat: dn = mat[-1]
        ca,cb,cc = st.columns([3,1,1])
        with ca:
            nm = st.selectbox(f'n{prefix}{i}', mat, index=mat.index(dn),
                              key=f'{prefix}_name_{i}', label_visibility='collapsed')
        with cb:
            th = st.number_input(f't{prefix}{i}', 0, 200, dt, step=5,
                                 key=f'{prefix}_thick_{i}', label_visibility='collapsed')
        de = st.session_state.get(f'{prefix}_E_{i}_{nm}', MATERIAL_MODULUS.get(nm,100))
        with cc:
            ev = st.number_input(f'e{prefix}{i}', 10, 10000, de,
                                 key=f'{prefix}_E_{i}_{nm}', label_visibility='collapsed')
        result.append({'name':nm,'thickness_cm':th,'E_MPa':ev})
    return result

# ============================================================
# k∞ block (Row B) — แสดงผลใน column ที่เรียก
# ============================================================
def _kblock(prefix, layers, MR_psi):
    od = calc_odemark([(l['thickness_cm'],l['E_MPa']) for l in layers])
    if od is None:
        st.warning('⚠️ กรุณากรอกความหนาและ E ให้ครบ')
        return None

    DSB_raw, ESB_psi = od
    DSB_used, warn   = _round_dsb(DSB_raw)
    if warn: st.warning(warn)

    res   = calc_composite_k(MR_psi, ESB_psi, float(DSB_used))
    k_inf = res['k_inf_pci']

    ls_val = st.number_input(
        'Loss of Support (LS)', 0.0, 3.0,
        st.session_state.get(f'{prefix}_ls', 1.0), 0.5,
        key=f'{prefix}_ls', format='%.1f',
        help='LS=0: ไม่มี | LS=1: granular | LS=2-3: stabilized')

    k_eff = k_inf if ls_val <= 0 else apply_loss_of_support(k_inf, ls_val)

    _row('DSB (Odemark จริง)', f'{DSB_raw:.2f} in')
    _row('DSB (ใช้จริง)', f'{DSB_used} in  ← nearest', hi=True)
    _row('ESB equivalent', f'{ESB_psi:,.0f} psi')
    _row('MR (subgrade)',  f'{MR_psi:,.0f} psi')
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    if ls_val <= 0:
        _mbox('k∞ = k_eff (LS=0)', f'{k_inf:.0f}', 'pci', '#1565C0', '#E3F2FD')
    else:
        ca,cb = st.columns(2)
        with ca: _mbox('k∞ (Fig.3.3)', f'{k_inf:.0f}', 'pci', '#1565C0', '#E3F2FD')
        with cb: _mbox(f'k_eff (LS={ls_val:.1f})', f'{k_eff:.0f}', 'pci', '#2E7D32', '#E8F5E9')

    # store
    st.session_state[f'{prefix}_k_inf']   = k_inf
    st.session_state[f'{prefix}_k_eff']   = k_eff
    st.session_state[f'{prefix}_dsb_raw'] = DSB_raw
    st.session_state[f'{prefix}_dsb']     = DSB_used
    st.session_state[f'{prefix}_esb']     = ESB_psi
    st.session_state[f'{prefix}_res33']   = res
    st.session_state[f'{prefix}_ls_val']  = ls_val
    st.session_state[f'{prefix}_layers']  = layers

    # ปุ่ม toggle
    if ls_val <= 0:
        b1,b2 = st.columns(2)
        with b1:
            if st.button('📊 Fig.3.3', key=f'bf33_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_f33'] = not st.session_state.get(f'{prefix}_show_f33',False)
        with b2:
            if st.button('🏗️ โครงสร้าง', key=f'bstr_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_str'] = not st.session_state.get(f'{prefix}_show_str',False)
    else:
        b1,b2,b3 = st.columns(3)
        with b1:
            if st.button('📊 Fig.3.3', key=f'bf33_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_f33'] = not st.session_state.get(f'{prefix}_show_f33',False)
        with b2:
            if st.button('📉 Fig.3.4', key=f'bf34_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_f34'] = not st.session_state.get(f'{prefix}_show_f34',False)
        with b3:
            if st.button('🏗️ โครงสร้าง', key=f'bstr_{prefix}', use_container_width=True):
                st.session_state[f'{prefix}_show_str'] = not st.session_state.get(f'{prefix}_show_str',False)

    # กราฟอยู่ใน column เดียวกัน (ซ้าย=JPCP ขวา=CRCP)
    _graphs(prefix, MR_psi)
    return (k_inf, k_eff)

# ============================================================
# กราฟ — แสดงใน column ที่เรียก (ซ้ายหรือขวา)
# ============================================================
def _graphs(prefix, MR_psi):
    res    = st.session_state.get(f'{prefix}_res33')
    ls_val = st.session_state.get(f'{prefix}_ls_val', 0)
    k_inf  = st.session_state.get(f'{prefix}_k_inf')
    k_eff  = st.session_state.get(f'{prefix}_k_eff')
    DSB    = st.session_state.get(f'{prefix}_dsb')
    ESB    = st.session_state.get(f'{prefix}_esb')
    layers = st.session_state.get(f'{prefix}_layers', [])
    if res is None: return

    # save Fig.3.3 bytes เสมอ (ใช้ใน Word report Tab 3)
    fig33 = plot_f33(MR_psi, ESB, DSB, res)
    st.session_state[f'{prefix}_fig33_bytes'] = fig_to_bytes(fig33)
    if st.session_state.get(f'{prefix}_show_f33'):
        st.pyplot(fig33, use_container_width=True)
        st.download_button('⬇️ Fig.3.3', st.session_state[f'{prefix}_fig33_bytes'],
                           f'fig33_{prefix}.png','image/png',
                           key=f'dl33_{prefix}')
    plt.close(fig33)

    if ls_val > 0:
        # save Fig.3.4 bytes เสมอ
        fig34 = plot_f34(k_inf, ls_val, k_eff)
        st.session_state[f'{prefix}_fig34_bytes'] = fig_to_bytes(fig34)
        if st.session_state.get(f'{prefix}_show_f34'):
            st.pyplot(fig34, use_container_width=True)
            st.download_button('⬇️ Fig.3.4', st.session_state[f'{prefix}_fig34_bytes'],
                               f'fig34_{prefix}.png','image/png',
                               key=f'dl34_{prefix}')
        plt.close(fig34)

    if st.session_state.get(f'{prefix}_show_str') and layers:
        fig = plot_structure(layers)
        if fig:
            st.pyplot(fig, use_container_width=True)
            st.download_button('⬇️ โครงสร้าง', fig_to_bytes(fig),
                               f'str_{prefix}.png','image/png',
                               key=f'dlstr_{prefix}')
            plt.close(fig)

# ============================================================
# MAIN
# ============================================================
def render_tab2():
    # ── Subgrade ─────────────────────────────────────────────
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
    st.markdown('<div class="rp-card-title">🌍 Subgrade — ดินเดิม (ใช้ร่วมกันทั้ง JPCP และ CRCP)</div>',
                unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        cbr = st.number_input('CBR (%)', 1.0, 30.0,
                              st.session_state.get('cbr',4.0), 0.5,
                              key='cbr', format='%.1f')
    MR_psi = mr_from_cbr(cbr)
    formula = 'MR = 1,500 × CBR' if cbr < 10 else 'MR = 1,000 + 555 × CBR'
    with c2:
        st.markdown(
            f'<div style="background:#FFF3CD;border:1px solid #FFECB3;'
            f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
            f'<div style="font-size:11px;color:#90A4AE">{formula}</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
            f'font-weight:700;color:#1565C0">{MR_psi:,.0f} psi</div>'
            f'<div style="font-size:11px;color:#90A4AE">({MR_psi/145.038:.1f} MPa)</div>'
            f'</div>', unsafe_allow_html=True)
    with c3:
        st.info(f'MR = **{MR_psi:,.0f} psi** ใช้กับทั้ง JPCP และ CRCP')
    st.session_state['MR_psi'] = MR_psi
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Row A: Layers ─────────────────────────────────────────
    col_j, col_c = st.columns(2)

    with col_j:
        _card(_JPCP_BG, _JPCP_BD)
        _title('🔲  JPCP / JRCP — Subbase Layers', _JPCP_BD, _JPCP_BDLT)
        n_j = st.slider('จำนวนชั้น JPCP', 1, 6,
                        st.session_state.get('jpcp_n',5), key='jpcp_n')
        layers_jpcp = _layers('jpcp', n_j, _DEF_JPCP)
        tot_j = sum(l['thickness_cm'] for l in layers_jpcp if l['thickness_cm']>0)
        st.caption(f'รวม = **{tot_j} ซม.**')
        _end()

    with col_c:
        _card(_CRCP_BG, _CRCP_BD)
        _title('〰️  CRCP — Subbase Layers', _CRCP_BD, _CRCP_BDLT)
        copy_jpcp = st.checkbox(
            'ใช้ค่าเดียวกับ JPCP/JRCP',
            value=st.session_state.get('crcp_copy',False),
            key='crcp_copy',
            help='ติ๊กเพื่อ copy layers จาก JPCP/JRCP มาใช้กับ CRCP')
        if copy_jpcp:
            layers_crcp = layers_jpcp
            st.markdown(
                '<div style="font-size:12px;color:#2E7D32;background:#E8F5E9;'
                'border-radius:6px;padding:5px 10px;margin-bottom:6px">'
                '✅ ใช้ชั้นวัสดุเดียวกับ JPCP/JRCP</div>',
                unsafe_allow_html=True)
        else:
            n_c = st.slider('จำนวนชั้น CRCP', 1, 6,
                            st.session_state.get('crcp_n',3), key='crcp_n')
            layers_crcp = _layers('crcp', n_c, _DEF_CRCP)
        tot_c = sum(l['thickness_cm'] for l in layers_crcp if l['thickness_cm']>0)
        st.caption(f'รวม = **{tot_c} ซม.**')
        _end()

    # ── Row B: k∞ / LS / กราฟ ────────────────────────────────
    col_j2, col_c2 = st.columns(2)

    with col_j2:
        _card(_JPCP_BG, _JPCP_BD)
        _title('🔲  JPCP / JRCP — k∞ & Loss of Support', _JPCP_BD, _JPCP_BDLT)
        _kblock('jpcp', layers_jpcp, MR_psi)
        _end()

    with col_c2:
        _card(_CRCP_BG, _CRCP_BD)
        _title('〰️  CRCP — k∞ & Loss of Support', _CRCP_BD, _CRCP_BDLT)
        _kblock('crcp', layers_crcp, MR_psi)
        _end()

    # ── สรุป k_eff ──────────────────────────────────────────
    kj = st.session_state.get('jpcp_k_eff')
    kc = st.session_state.get('crcp_k_eff')
    if kj or kc:
        st.markdown(
            '<div style="background:#E8F5E9;border:1.5px solid #A5D6A7;'
            'border-radius:8px;padding:8px 14px;margin-top:6px">'
            '<div style="font-size:12px;font-weight:700;color:#2E7D32;'
            'margin-bottom:6px">✅ สรุป k_eff → ส่งต่อ Tab 3 Design</div>',
            unsafe_allow_html=True)
        s1,s2 = st.columns(2)
        with s1:
            if kj: _mbox('k_eff — JPCP/JRCP', f'{kj:.0f}', 'pci', '#1565C0', '#E3F2FD')
        with s2:
            if kc: _mbox('k_eff — CRCP', f'{kc:.0f}', 'pci', '#2E7D32', '#E8F5E9')
        st.markdown('</div>', unsafe_allow_html=True)
