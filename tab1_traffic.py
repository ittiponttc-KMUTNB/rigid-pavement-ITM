"""
tab1_traffic.py — Tab 1: Traffic & ESAL
Rigid Pavement Design V7
"""
import streamlit as st
import pandas as pd
import json
from engine import compute_esal_for_d, get_zr

D_CARDS = [(10,25),(11,28),(12,30),(13,32),(14,35)]  # (inch, cm)

def render_tab1():
    # ── reset pt flag (ต้องทำก่อน widget render) ────────────
    ed_pre = st.session_state.get('esal_data')
    if st.session_state.pop('_do_reset_pt', False) and ed_pre:
        st.session_state['pt'] = float(ed_pre.get('pt', 2.0))

    # ── ชื่อโครงการ ──────────────────────────────────────────
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
    st.markdown('<div class="rp-card-title">📋 ข้อมูลโครงการ</div>', unsafe_allow_html=True)
    proj = st.text_input('ชื่อโครงการ',
                         value=st.session_state.get('project_name', ''),
                         key='project_name',
                         placeholder='เช่น ทางหลวงหมายเลข 1 ตอน กรุงเทพ-สระบุรี')
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Upload ESAL JSON ─────────────────────────────────────
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
    st.markdown('<div class="rp-card-title">📊 นำเข้า ESAL จาก ESAL Calculator</div>',
                unsafe_allow_html=True)
    st.caption('อัปโหลดไฟล์ .json ที่ Save จาก ESAL Calculator (Rigid)')

    esal_file = st.file_uploader('เลือกไฟล์ ESAL Project (.json)',
                                 type=['json'], key='esal_uploader',
                                 help='ไฟล์ที่ได้จากปุ่ม บันทึก Project ใน ESAL Calculator')
    if esal_file is not None:
        fid = f'{esal_file.name}_{esal_file.size}'
        if st.session_state.get('esal_file_id') != fid:
            st.session_state['esal_file_id'] = fid
            try:
                raw = json.load(esal_file)
                if raw.get('pavement_type') != 'rigid':
                    st.error('❌ ไฟล์นี้เป็น Flexible Pavement — กรุณาใช้ไฟล์ Rigid')
                    st.session_state['esal_data'] = None
                elif 'traffic_data' not in raw:
                    st.error('❌ ไฟล์ JSON ไม่ถูกต้อง (ขาด traffic_data)')
                    st.session_state['esal_data'] = None
                else:
                    st.session_state['esal_data'] = {
                        'traffic_data':     raw['traffic_data'],
                        'pt':               float(raw.get('pt', 2.0)),
                        'lane_factor':      raw.get('lane_factor', 0.9),
                        'direction_factor': raw.get('direction_factor', 0.5),
                        'filename':         esal_file.name,
                        'num_years':        len(raw['traffic_data']),
                    }
                    st.rerun()
            except Exception as ex:
                st.error(f'❌ อ่านไฟล์ไม่ได้: {ex}')

    ed = st.session_state.get('esal_data')
    if ed:
        st.markdown(f'''<div class="rp-status-ok">
            ✅ นำเข้าสำเร็จ: {ed["filename"]} &nbsp;|&nbsp;
            ระยะออกแบบ {ed["num_years"]} ปี &nbsp;|&nbsp;
            pt = {ed["pt"]} &nbsp;|&nbsp;
            Lane Factor = {ed["lane_factor"]} &nbsp;|&nbsp;
            Dir. Factor = {ed["direction_factor"]}
        </div>''', unsafe_allow_html=True)
        st.markdown('')
        with st.expander('📋 ดูข้อมูลจราจร', expanded=False):
            df = pd.DataFrame(ed['traffic_data'])
            st.dataframe(df, use_container_width=True, hide_index=True)
        if st.button('🗑️ ล้างข้อมูล ESAL', key='clear_esal'):
            st.session_state['esal_data'] = None
            st.session_state['esal_file_id'] = None
            st.rerun()
    else:
        st.markdown('<div class="rp-status-info">⚪ ยังไม่ได้นำเข้าข้อมูล ESAL</div>',
                    unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Serviceability & Reliability ─────────────────────────
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
    st.markdown('<div class="rp-card-title">📉 Serviceability & Reliability</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        pt = st.slider('Terminal Serviceability (Pt)', 1.5, 3.0,
                       st.session_state.get('pt', 2.0), 0.1, key='pt')
        dpsi = 4.5 - pt
        st.caption(f'ΔPSI = 4.5 − {pt:.1f} = **{dpsi:.1f}**')
        # warning pt
        if ed:
            pt_json = ed.get('pt', pt)
            if abs(pt - pt_json) > 0.01:
                st.warning(f'⚠️ pt ที่ใช้ ({pt:.1f}) ต่างจาก ESAL JSON ({pt_json:.1f})\n\n'
                           f'W18 จะถูกคำนวณใหม่ด้วย pt = {pt:.1f}')
                if st.button(f'↩️ ใช้ค่าจาก ESAL JSON (pt = {pt_json:.1f})',
                             key='reset_pt'):
                    st.session_state['_do_reset_pt'] = True
                    st.rerun()
            else:
                st.success('✅ pt สอดคล้องกับ ESAL JSON')
    with c2:
        reliability = st.select_slider('Reliability (%)',
                      options=[80, 85, 90, 95],
                      value=st.session_state.get('reliability', 90),
                      key='reliability')
        zr = get_zr(reliability)
        st.caption(f'ZR = **{zr:.3f}**')
    with c3:
        so = st.number_input('Overall Std. Deviation (So)', 0.30, 0.45,
                             st.session_state.get('so', 0.35), 0.01,
                             format='%.2f', key='so')
    st.markdown('</div>', unsafe_allow_html=True)

    # ── W18 Summary Cards ─────────────────────────────────────
    if ed:
        st.markdown('<div class="rp-card">', unsafe_allow_html=True)
        st.markdown('<div class="rp-card-title">🔢 W18 ตามความหนาคอนกรีต D</div>',
                    unsafe_allow_html=True)
        st.caption('W18 ขึ้นกับ D และ pt — แสดง 5 ค่า D ตามมาตรฐาน กรมทางหลวง')
        pt_val = st.session_state.get('pt', 2.0)
        cols   = st.columns(5)
        for i, (d_in, d_cm) in enumerate(D_CARDS):
            w18, _, _ = compute_esal_for_d(
                ed['traffic_data'], pt_val,
                ed['lane_factor'], ed['direction_factor'], d_cm)
            with cols[i]:
                st.markdown(f'''<div class="rp-metric">
                    <div class="rp-metric-label">D = {d_in} in ({d_cm} ซม.)</div>
                    <div class="rp-metric-val" style="font-size:15px">{w18:,}</div>
                    <div style="font-size:11px;color:#90A4AE;margin-top:2px">
                        {w18/1e6:.2f} ล้าน
                    </div>
                </div>''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
