"""
tab3_design.py — Tab 3: Design
Rigid Pavement Design V7
AASHTO 1993 — คำนวณความหนาแผ่นคอนกรีต JPCP/JRCP & CRCP
"""
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime

from engine import (
    calc_w18, check_design, find_optimum_k, compare_d,
    convert_cube_to_cyl, calc_ec, calc_sc, get_zr,
    plot_structure, fig_to_bytes,
    D_PAIRS,
)

# ── สีหลัก ───────────────────────────────────────────────────
_JPCP_BD   = '#1565C0'
_JPCP_BDLT = '#90CAF9'
_JPCP_BG   = '#E3F2FD'
_CRCP_BD   = '#2E7D32'
_CRCP_BDLT = '#A5D6A7'
_CRCP_BG   = '#E8F5E9'

SC_FIXED = 600.0   # psi — กรมทางหลวง กำหนด max


# ============================================================
# UI Helpers
# ============================================================
def _card_header(text, color):
    st.markdown(
        f'<div style="background:{color};border-radius:6px 6px 0 0;'
        f'padding:6px 12px;font-size:12px;font-weight:700;color:#fff;'
        f'margin-bottom:0">{text}</div>',
        unsafe_allow_html=True)

def _row(label, value, hi=False):
    c = _JPCP_BD if hi else '#1A237E'
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

def _verdict_bar(d_cm, d_in, w18_cap, w18_req, ratio, passed, bd_color):
    pct_cap   = min(ratio * 100, 100)
    bar_color = '#43A047' if passed else '#E53935'
    label     = f'✅ ผ่าน  (×{ratio:.2f})' if passed else f'❌ ไม่ผ่าน  (×{ratio:.2f})'
    ratio_txt = f'+{(ratio-1)*100:.0f}%' if passed else f'{ratio*100:.0f}%'
    st.markdown(
        f'<div style="background:#F5F5F5;border:1px solid {bd_color}33;'
        f'border-radius:8px;padding:8px 10px;margin-bottom:4px">'
        f'<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">'
        f'<span style="font-family:IBM Plex Mono,monospace;font-weight:700;color:{bd_color}">'
        f'D = {d_in} in ({d_cm} ซม.)</span>'
        f'<span style="font-weight:700;color:{bar_color}">{label}</span></div>'
        f'<div style="position:relative;background:#E0E0E0;border-radius:4px;height:10px">'
        f'<div style="background:{bar_color};width:{pct_cap:.1f}%;height:10px;border-radius:4px;'
        f'opacity:0.85"></div>'
        f'<div style="position:absolute;top:0;left:0;width:100%;height:100%;'
        f'border-right:2px dashed #9E9E9E;border-radius:4px;pointer-events:none"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:10px;'
        f'color:#90A4AE;margin-top:3px">'
        f'<span>W18_cap = {w18_cap:,.0f}</span>'
        f'<span style="color:{bar_color};font-weight:600">{ratio_txt} จาก W18_req</span>'
        f'<span>W18_req = {w18_req:,.0f}</span>'
        f'</div></div>',
        unsafe_allow_html=True)

def _kopt_box(prefix, rec_d_cm, k_opt, k_eff, bd):
    if k_opt is None:
        return
    delta  = k_eff - k_opt
    ok     = k_eff >= k_opt
    bg     = _CRCP_BG if ok else '#FFEBEE'
    bc     = _CRCP_BDLT if ok else '#EF9A9A'
    vc     = _CRCP_BD if ok else '#C62828'
    symbol = '✅' if ok else '⚠️'
    margin = f'{delta:+.0f} pci ({delta/k_opt*100:+.1f}%)'
    st.markdown(
        f'<div style="background:{bg};border:2px solid {bc};border-radius:8px;'
        f'padding:10px 12px;margin-top:6px">'
        f'<div style="font-size:12px;font-weight:700;color:{vc};margin-bottom:6px">'
        f'{symbol} k_opt vs k_eff  —  D = {rec_d_cm} ซม. ({round(rec_d_cm/2.54)} in)</div>'
        f'<div style="display:flex;gap:8px">'
        f'<div style="flex:1;background:white;border-radius:6px;padding:6px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">k_opt (min required)</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;font-weight:700;color:{bd}">'
        f'{k_opt:.0f} pci</div></div>'
        f'<div style="flex:1;background:white;border-radius:6px;padding:6px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">k_eff (Tab 2)</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;font-weight:700;color:{vc}">'
        f'{k_eff:.0f} pci</div></div>'
        f'<div style="flex:1;background:white;border-radius:6px;padding:6px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">Δk = k_eff − k_opt</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:14px;font-weight:700;color:{vc}">'
        f'{margin}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True)


# ============================================================
# Word Report (ไม่เปลี่ยน logic)
# ============================================================
def _create_word_report(ptype, proj_name, params, rows, sel_d_cm,
                        struct_fig_bytes, date_str,
                        fig33_bytes=None, fig34_bytes=None):
    try:
        from docx import Document
        from docx.shared import Inches, Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        return None

    TH = 'TH SarabunPSK'
    EQ = 'Times New Roman'
    TS = Pt(15)

    doc = Document()
    style = doc.styles['Normal']
    style.font.name = TH
    style.font.size = TS

    sec = doc.sections[0]
    sec.page_width  = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin  = sec.bottom_margin = Cm(2.5)

    h0 = doc.add_heading('รายการคำนวณออกแบบความหนาถนนคอนกรีต', 0)
    h0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph('ตามวิธี AASHTO 1993')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].font.name = TH; p.runs[0].font.size = TS

    doc.add_heading('1. ข้อมูลทั่วไป', level=1)
    w18_src = '(กรอกเอง)' if params.get('w18_manual') else '(จาก ESAL JSON)'
    for txt in [
        f'ชื่อโครงการ: {proj_name or "—"}',
        f'ประเภทถนน: {ptype}',
        f'วันที่คำนวณ: {date_str}',
        f'แหล่งข้อมูล W18: {w18_src}',
    ]:
        p = doc.add_paragraph(txt)
        p.runs[0].font.name = TH; p.runs[0].font.size = TS

    doc.add_heading('2. ข้อมูลนำเข้า', level=1)
    t = doc.add_table(rows=1, cols=4)
    t.style = 'Table Grid'
    for i, h in enumerate(['พารามิเตอร์', 'สัญลักษณ์', 'ค่า', 'หน่วย']):
        c = t.rows[0].cells[i]
        r = c.paragraphs[0].add_run(h)
        r.bold = True; r.font.name = TH; r.font.size = TS

    input_rows = [
        ('ESAL ออกแบบ',              'W₁₈',    f"{params['w18']:,.0f}",    'ESALs'),
        ('Terminal Serviceability',  'Pt',      f"{params['pt']:.1f}",      '—'),
        ('Reliability',              'R',       f"{params['R']:.0f}",       '%'),
        ('Standard Deviation',       'So',      f"{params['so']:.2f}",      '—'),
        ('k_eff (Tab 2)',             'k_eff',   f"{params['k_eff']:,.0f}", 'pci'),
        ("กำลังอัด (Cube)",           "f'c",     f"{params['fc_cube']:.0f}",'ksc'),
        ("กำลังอัด (Cylinder)",       "f'c,cyl", f"{params['fc_cyl']:.0f}",'ksc'),
        ('Modulus of Rupture',        'Sc',      f"{params['sc']:.0f}",     'psi'),
        ('Modulus of Elasticity',     'Ec',      f"{params['ec']:,.0f}",    'psi'),
        ('Load Transfer Coefficient', 'J',       f"{params['j']:.1f}",      '—'),
        ('Drainage Coefficient',      'Cd',      f"{params['cd']:.1f}",     '—'),
        ('ΔPSI',                      'ΔPSI',    f"{params['dpsi']:.1f}",   '—'),
    ]
    for param, sym, val, unit in input_rows:
        row = t.add_row().cells
        for i, txt in enumerate([param, sym, val, unit]):
            r = row[i].paragraphs[0].add_run(txt)
            r.font.name = TH; r.font.size = TS

    doc.add_heading('3. สมการออกแบบ AASHTO 1993', level=1)

    def _add_eq(document, parts):
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pPr = p._p.get_or_add_pPr()
        ind = OxmlElement('w:ind')
        ind.set(qn('w:left'), '360')
        pPr.append(ind)
        for text, is_sub, is_sup in parts:
            run = p.add_run(text)
            run.font.name = EQ; run.font.size = Pt(13)
            if is_sub or is_sup:
                rPr = run._r.get_or_add_rPr()
                va = OxmlElement('w:vertAlign')
                va.set(qn('w:val'), 'subscript' if is_sub else 'superscript')
                rPr.append(va)
        return p

    _add_eq(doc, [
        ('log', False, False), ('10', True, False),
        ('(W', False, False),  ('18', True, False),
        (') = Z', False, False), ('R', False, False),
        (' \u00d7 S', False, False), ('o', True, False),
        (' + 7.35 \u00d7 log', False, False), ('10', True, False),
        ('(D+1) \u2212 0.06', False, False),
    ])
    _add_eq(doc, [
        ('        + log', False, False), ('10', True, False),
        ('(\u0394PSI/3.0) / (1 + 1.624\u00d710', False, False),
        ('7', False, True), ('/(D+1)', False, False),
        ('8.46', False, True), (')', False, False),
    ])
    _add_eq(doc, [
        ('        + (4.22 \u2212 0.32\u00d7P', False, False),
        ('t', True, False), (') \u00d7 log', False, False),
        ('10', True, False), ('[(S', False, False),
        ('c', True, False), ('\u00d7C', False, False),
        ('d', True, False), ('\u00d7(D', False, False),
        ('0.75', False, True), ('\u22121.132))/(215.63\u00d7J\u00d7(D', False, False),
        ('0.75', False, True), ('\u221218.42/(E', False, False),
        ('c', True, False), ('/k)', False, False),
        ('0.25', False, True), (')]', False, False),
    ])

    p = doc.add_paragraph('โดยที่:')
    p.runs[0].font.name = TH; p.runs[0].font.size = TS
    tsym = doc.add_table(rows=1, cols=3)
    tsym.style = 'Table Grid'
    for i, h in enumerate(['สัญลักษณ์', 'ความหมาย', 'หน่วย']):
        c = tsym.rows[0].cells[i]
        r = c.paragraphs[0].add_run(h)
        r.bold = True; r.font.name = TH; r.font.size = TS
    for sym, meaning, unit in [
        ('W18',  'จำนวน ESAL ที่รองรับได้',                       'ESALs'),
        ('ZR',   'Standard Normal Deviate',                        '-'),
        ('So',   'Overall Standard Deviation',                     '-'),
        ('D',    'ความหนาแผ่นคอนกรีต',                             'in'),
        ('DPSI', 'การสูญเสีย Serviceability (4.5 - Pt)',           '-'),
        ('Sc',   'Modulus of Rupture',                             'psi'),
        ('Cd',   'Drainage Coefficient',                           '-'),
        ('J',    'Load Transfer Coefficient',                      '-'),
        ('Ec',   'Modulus of Elasticity of Concrete',              'psi'),
        ('k',    'Effective Modulus of Subgrade Reaction (k_eff)', 'pci'),
    ]:
        row = tsym.add_row().cells
        for i, txt in enumerate([sym, meaning, unit]):
            r = row[i].paragraphs[0].add_run(txt)
            r.font.name = TH; r.font.size = TS

    doc.add_paragraph()
    doc.add_heading('4. ผลการเปรียบเทียบความหนา', level=1)
    t3 = doc.add_table(rows=1, cols=7)
    t3.style = 'Table Grid'
    for i, h in enumerate(['D (ซม.)', 'D (นิ้ว)', 'W18 ต้องการ',
                            'log10(W18_cap)', 'W18 รองรับได้', 'อัตราส่วน', 'ผล']):
        c = t3.rows[0].cells[i]
        r = c.paragraphs[0].add_run(h)
        r.bold = True; r.font.name = TH; r.font.size = TS
    for rv in rows:
        row = t3.add_row().cells
        for i, txt in enumerate([
            f"{rv['d_cm']}",
            f"{rv['d_inch']}",
            f"{rv.get('w18_req', params['w18']):,.0f}",
            f"{rv['log_w18']:.4f}",
            f"{rv['w18_cap']:,.0f}",
            f"{rv['ratio']:.3f}",
            'ผ่าน' if rv['passed'] else 'ไม่ผ่าน',
        ]):
            r = row[i].paragraphs[0].add_run(txt)
            r.font.name = TH; r.font.size = TS

    k_opt = params.get('k_opt')
    k_eff = params.get('k_eff')
    if k_opt and k_eff:
        doc.add_heading('5. k_opt vs k_eff', level=1)
        delta   = k_eff - k_opt
        verdict = 'เพียงพอ' if delta >= 0 else 'ไม่เพียงพอ'
        tk = doc.add_table(rows=1, cols=2)
        tk.style = 'Table Grid'
        for i, h in enumerate(['รายการ', 'ค่า']):
            c = tk.rows[0].cells[i]
            r = c.paragraphs[0].add_run(h)
            r.bold = True; r.font.name = TH; r.font.size = TS
        for lbl, val in [
            (f"D แนะนำ",                f"{sel_d_cm} ซม. ({round(sel_d_cm/2.54)} in)"),
            ("k_opt (minimum required)", f"{k_opt:.0f} pci"),
            ("k_eff (จาก Tab 2)",        f"{k_eff:.0f} pci"),
            (f"Δk = k_eff - k_opt",     f"{delta:+.0f} pci  →  {verdict}"),
        ]:
            row = tk.add_row().cells
            for i, txt in enumerate([lbl, val]):
                r = row[i].paragraphs[0].add_run(txt)
                r.font.name = TH; r.font.size = TS

    doc.add_heading('6. สรุปผล', level=1)
    sel_row = next((r for r in rows if r['d_cm'] == sel_d_cm), None)
    summary = [f"ความหนาที่เลือก: {sel_d_cm} ซม. ({round(sel_d_cm/2.54)} นิ้ว)",
               f"ESAL ที่ต้องการ: {params['w18']:,.0f} ESALs"]
    if sel_row:
        w18_req_sel = sel_row.get('w18_req', params['w18'])
        summary += [
            f"ESAL ที่ต้องการ (D={sel_d_cm} ซม.): {w18_req_sel:,.0f} ESALs",
            f"ESAL ที่รองรับได้: {sel_row['w18_cap']:,.0f} ESALs",
            f"อัตราส่วน (capacity/demand): {sel_row['ratio']:.3f}",
            f"ผลการตรวจสอบ: {'ผ่านเกณฑ์' if sel_row['passed'] else 'ไม่ผ่านเกณฑ์'}",
        ]
    for txt in summary:
        p = doc.add_paragraph(txt)
        p.runs[0].font.name = TH; p.runs[0].font.size = TS

    if fig33_bytes:
        doc.add_heading('7. AASHTO Figure 3.3 — Composite k_inf', level=1)
        p = doc.add_paragraph('ผลการหาค่า Composite Modulus of Subgrade Reaction (k_inf) จาก Nomograph:')
        p.runs[0].font.name = TH; p.runs[0].font.size = TS
        doc.add_picture(BytesIO(fig33_bytes), width=Inches(5.0))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    if fig34_bytes:
        doc.add_heading('8. AASHTO Figure 3.4 — Loss of Support', level=1)
        p = doc.add_paragraph('ผลการปรับแก้ k_eff ตาม Loss of Support (LS):')
        p.runs[0].font.name = TH; p.runs[0].font.size = TS
        doc.add_picture(BytesIO(fig34_bytes), width=Inches(5.0))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    if struct_fig_bytes:
        doc.add_heading('9. รูปตัดโครงสร้างชั้นทาง', level=1)
        p = doc.add_paragraph('รูปตัดโครงสร้างชั้นทางที่ออกแบบ:')
        p.runs[0].font.name = TH; p.runs[0].font.size = TS
        doc.add_picture(BytesIO(struct_fig_bytes), width=Inches(5.5))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()
    ref = doc.add_paragraph('Reference: AASHTO Guide for Design of Pavement Structures 1993')
    ref.runs[0].font.name = TH; ref.runs[0].font.size = Pt(13)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ============================================================
# Design Block
# ============================================================
def _design_block(prefix, ptype, fc_cyl, ec_psi, cd, w18_req, pt, zr, so, bd, bdlt):
    dpsi  = 4.5 - pt
    k_eff = st.session_state.get(f'{prefix}_k_eff')

    if w18_req is None:
        st.markdown(
            '<div style="background:#FFF3E0;border:1px solid #FFB74D;border-radius:8px;'
            'padding:8px 12px;font-size:12px;color:#E65100">'
            '⚠️ ยังไม่มีข้อมูล W18 — กรุณากรอก W18 ในช่องด้านบน'
            '</div>', unsafe_allow_html=True)
        return None

    if k_eff is None:
        st.markdown(
            '<div style="background:#FFF3E0;border:1px solid #FFB74D;border-radius:8px;'
            'padding:8px 12px;font-size:12px;color:#E65100">'
            f'⚠️ ยังไม่มีค่า k_eff ({ptype}) — กรุณาคำนวณใน Tab 2 ก่อน'
            '</div>', unsafe_allow_html=True)
        return None

    if prefix == 'jpcp':
        j_opts  = [2.5, 2.6, 2.7, 2.8]
        j_def   = st.session_state.get('jpcp_j', 2.8)
        j_label = 'J — Load Transfer Coefficient (JPCP/JRCP)'
    else:
        j_opts  = [2.3, 2.4, 2.5, 2.6]
        j_def   = st.session_state.get('crcp_j', 2.6)
        j_label = 'J — Load Transfer Coefficient (CRCP)'

    if j_def not in j_opts:
        j_def = j_opts[-1]

    j_val = st.select_slider(
        j_label, options=j_opts,
        value=j_def,
        key=f'{prefix}_j',
        format_func=lambda x: f'{x:.1f}')

    ed = st.session_state.get('esal_data')
    w18_manual_mode = st.session_state.get('w18_manual_mode', False)

    w18_per_d = {}
    if ed and not w18_manual_mode:
        from engine import compute_esal_for_d
        for d_in, d_cm in D_PAIRS:
            w18_d, _, _ = compute_esal_for_d(
                ed['traffic_data'], pt,
                ed['lane_factor'], ed['direction_factor'], d_cm)
            w18_per_d[d_cm] = w18_d
    else:
        for d_in, d_cm in D_PAIRS:
            w18_per_d[d_cm] = w18_req
        st.markdown(
            '<div style="background:#FFF8E1;border:1px solid #FFD54F;'
            'border-radius:7px;padding:6px 10px;font-size:11px;color:#E65100;margin-bottom:4px">'
            '⚠️ W18 กรอกเอง — ใช้ค่าเดียวกันทุก D (conservative)'
            '</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    w18_note = 'แยกตาม D' if (ed and not w18_manual_mode) else 'ค่าเดียว (manual)'
    _row(f'W18 ({w18_note})', f'{w18_req:,.0f} ESALs (ref D=30)')
    _row('k_eff (Tab 2)',  f'{k_eff:.0f} pci')
    _row("f'c (cube)", f"{st.session_state.get('fc_cube', fc_cube):.0f} ksc")
    _row('Ec',             f'{ec_psi:,.0f} psi')
    _row('Sc (ทล. lock)', f'{SC_FIXED:.0f} psi')
    _row('J',              f'{j_val:.1f}', hi=True)
    _row('Cd',             f'{cd:.1f}',    hi=True)
    _row('Pt / ΔPSI',      f'{pt:.1f} / {dpsi:.1f}')
    _row('ZR / So',        f'{zr:.3f} / {so:.2f}')
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

    from engine import calc_w18 as _calc_w18
    rows = []
    for d_in, d_cm in D_PAIRS:
        w18_d  = w18_per_d[d_cm]
        lw, wc = _calc_w18(d_in, dpsi, pt, zr, so,
                           SC_FIXED, cd, j_val, ec_psi, k_eff)
        passed = wc >= w18_d
        ratio  = round(wc / w18_d, 3) if w18_d > 0 else 0
        rows.append({
            'd_cm':    d_cm,
            'd_inch':  d_in,
            'log_w18': round(lw, 4),
            'w18_cap': round(wc, 0),
            'w18_req': w18_d,
            'passed':  passed,
            'ratio':   ratio,
        })
    st.session_state[f'{prefix}_design_rows'] = rows

    passed_rows = [r for r in rows if r['passed']]
    for r in rows:
        _verdict_bar(r['d_cm'], r['d_inch'],
                     r['w18_cap'], r['w18_req'],
                     r['ratio'], r['passed'], bd)

    if passed_rows:
        rec = min(passed_rows, key=lambda r: r['d_cm'])
        _mbox(f'✅ D แนะนำ ({ptype})',
              f"{rec['d_inch']} in ({rec['d_cm']} ซม.)",
              f"W18 capacity = {rec['w18_cap']:,.0f}",
              _CRCP_BD if prefix == 'crcp' else _JPCP_BD,
              _CRCP_BG if prefix == 'crcp' else _JPCP_BG)
        st.session_state[f'{prefix}_rec_d_cm'] = rec['d_cm']
    else:
        st.markdown(
            '<div style="background:#FFEBEE;border:1px solid #EF9A9A;'
            'border-radius:8px;padding:8px 12px;font-size:12px;color:#C62828">'
            '❌ ไม่มี D ที่ผ่านเกณฑ์ในช่วง 25–35 ซม. — พิจารณาเพิ่ม k_eff หรือลด J'
            '</div>', unsafe_allow_html=True)
        st.session_state[f'{prefix}_rec_d_cm'] = None

    sel_d_cm = st.session_state.get(f'{prefix}_rec_d_cm') or 30
    sel_d_in = round(sel_d_cm / 2.54)
    k_opt    = find_optimum_k(w18_req, sel_d_in, dpsi, pt, zr, so,
                               SC_FIXED, cd, j_val, ec_psi)
    _kopt_box(prefix, sel_d_cm, k_opt, k_eff, bd)

    st.session_state[f'{prefix}_design_params'] = {
        'w18':        w18_req,
        'w18_manual': st.session_state.get('w18_manual_mode', False),
        'pt':         pt,
        'R':          st.session_state.get('reliability', 90),
        'so':         so,
        'k_eff':      k_eff,
        'fc_cube':    st.session_state.get('fc_cube', 350),
        'fc_cyl':     fc_cyl,
        'sc':         SC_FIXED,
        'ec':         ec_psi,
        'j':          j_val,
        'cd':         cd,
        'dpsi':       dpsi,
        'k_opt':      k_opt,
    }

    return {'rows': rows, 'j': j_val, 'k_eff': k_eff, 'k_opt': k_opt}


# ============================================================
# MAIN RENDER
# ============================================================
def render_tab3():
    ed = st.session_state.get('esal_data')
    pt = st.session_state.get('pt',  2.0)
    so = st.session_state.get('so',  0.35)
    R  = st.session_state.get('reliability', 90)
    zr = get_zr(R)

    w18_from_json = None
    if ed:
        from engine import compute_esal_for_d
        w18_from_json, _, _ = compute_esal_for_d(
            ed['traffic_data'], pt,
            ed['lane_factor'], ed['direction_factor'], 30)

    kj = st.session_state.get('jpcp_k_eff')
    kc = st.session_state.get('crcp_k_eff')

    # ════════════════════════════════════════════════════════
    # Card 1 — Status bar
    # ════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown('<div class="rp-card-title">📋 สถานะข้อมูลจาก Tab 1-2</div>',
                    unsafe_allow_html=True)
        s1, s2, s3 = st.columns(3)
        with s1:
            if ed:
                st.markdown(
                    f'<div class="rp-status-ok">✅ W18 = {w18_from_json:,.0f} (จาก JSON)</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="rp-status-warn">⚠️ ไม่มี JSON — กรอก W18 เองด้านล่าง</div>',
                    unsafe_allow_html=True)
        with s2:
            if kj:
                st.markdown(
                    f'<div class="rp-status-ok">✅ k_eff JPCP = {kj:.0f} pci</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="rp-status-warn">⚠️ ยังไม่มี k_eff JPCP (Tab 2)</div>',
                    unsafe_allow_html=True)
        with s3:
            if kc:
                st.markdown(
                    f'<div class="rp-status-ok">✅ k_eff CRCP = {kc:.0f} pci</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="rp-status-warn">⚠️ ยังไม่มี k_eff CRCP (Tab 2)</div>',
                    unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # Card 2 — W18 Input
    # ════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown('<div class="rp-card-title">🔢 W18 — ESAL ออกแบบ</div>',
                    unsafe_allow_html=True)
        if ed:
            use_manual = st.checkbox(
                'กรอก W18 เองแทน (override จาก JSON)',
                value=st.session_state.get('w18_manual_mode', False),
                key='w18_manual_mode')
            if use_manual:
                w18_req = st.number_input(
                    'W18 (ESALs)', min_value=100_000, max_value=500_000_000,
                    value=st.session_state.get('w18_manual', int(w18_from_json)),
                    step=100_000, key='w18_manual', format='%d')
                st.caption(f'W18 จาก JSON = {w18_from_json:,.0f} ESALs (ไม่ได้ใช้)')
            else:
                w18_req = w18_from_json
                st.markdown(
                    f'<div class="rp-status-ok">'
                    f'✅ ใช้ W18 = <b>{w18_req:,.0f} ESALs</b> จาก ESAL JSON (D = 30 ซม.)'
                    f'</div>', unsafe_allow_html=True)
        else:
            st.session_state['w18_manual_mode'] = True
            w18_req = st.number_input(
                'W18 (ESALs) — กรอกเอง', min_value=100_000, max_value=500_000_000,
                value=st.session_state.get('w18_manual', 5_000_000),
                step=100_000, key='w18_manual', format='%d',
                help='กรอก ESAL ออกแบบโดยตรง (ไม่มี JSON)')

    # ════════════════════════════════════════════════════════
    # Card 3 — Shared Parameters
    # ════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown('<div class="rp-card-title">⚙️ พารามิเตอร์ร่วม (JPCP & CRCP)</div>',
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            fc_cube = st.number_input(
                "f'c กำลังคอนกรีต Cube (ksc)", 280, 600,
                st.session_state.get('fc_cube', 350), step=10,
                key='fc_cube',
                help='กรมทางหลวง กำหนดไม่ต่ำกว่า 350 ksc')
            if fc_cube < 350:
                st.warning('⚠️ ต่ำกว่า 350 ksc — ไม่เป็นไปตามมาตรฐาน ทล.')
        fc_cyl = convert_cube_to_cyl(fc_cube)
        ec_psi = calc_ec(fc_cyl)
        with c2:
            st.markdown(
                f'<div style="background:{_JPCP_BG};border:1px solid {_JPCP_BDLT};'
                f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
                f'<div style="font-size:10px;color:#78909C">f\'c,cyl = 0.8 × f\'c,cube = {fc_cyl:.0f} ksc</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
                f'font-weight:700;color:{_JPCP_BD}">{ec_psi:,.0f} psi</div>'
                f'<div style="font-size:10px;color:#78909C">Modulus of Elasticity (Ec)</div></div>',
                unsafe_allow_html=True)
        with c3:
            st.markdown(
                f'<div style="background:{_CRCP_BG};border:1px solid {_CRCP_BDLT};'
                f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
                f'<div style="font-size:10px;color:#78909C">Sc — ทล. กำหนด (lock)</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
                f'font-weight:700;color:{_CRCP_BD}">{SC_FIXED:.0f} psi</div>'
                f'<div style="font-size:10px;color:#78909C">Modulus of Rupture</div></div>',
                unsafe_allow_html=True)
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:12px;color:#546E7A;margin-bottom:2px">'
                    'Cd — Drainage Coefficient (ใช้ร่วมกัน)</div>',
                    unsafe_allow_html=True)
        cd_str = st.radio(
            'Cd',
            options=['1.0 — ระบายน้ำปกติ', '1.1 — ระบายน้ำดี', '1.2 — ระบายน้ำดีมาก'],
            index=[1.0, 1.1, 1.2].index(st.session_state.get('cd', 1.0)),
            key='cd_radio',
            horizontal=True,
            label_visibility='collapsed')
        cd = float(cd_str.split(' — ')[0])
        st.session_state['cd'] = cd

    # ════════════════════════════════════════════════════════
    # Side-by-side Design (JPCP | CRCP)
    # ════════════════════════════════════════════════════════
    col_j, col_c = st.columns(2)

    with col_j:
        _card_header('🔲  JPCP / JRCP — Design', _JPCP_BD)
        with st.container(border=True):
            res_j = _design_block('jpcp', 'JPCP/JRCP',
                                  fc_cyl, ec_psi, cd,
                                  w18_req, pt, zr, so,
                                  _JPCP_BD, _JPCP_BDLT)
            if res_j and st.session_state.get('jpcp_layers'):
                if st.button('🏗️ โครงสร้าง JPCP', key='str_j', use_container_width=True):
                    st.session_state['jpcp_show_str3'] = \
                        not st.session_state.get('jpcp_show_str3', False)
                if st.session_state.get('jpcp_show_str3'):
                    rec_cm = st.session_state.get('jpcp_rec_d_cm')
                    fig = plot_structure(
                        st.session_state['jpcp_layers'],
                        concrete_cm=rec_cm,
                        title=f'JPCP  D = {rec_cm} cm' if rec_cm else 'JPCP Structure')
                    if fig:
                        st.pyplot(fig, use_container_width=True)
                        st.session_state['jpcp_struct_bytes'] = fig_to_bytes(fig)
                        st.download_button('⬇️ PNG โครงสร้าง JPCP',
                                           st.session_state['jpcp_struct_bytes'],
                                           'struct_jpcp.png', 'image/png',
                                           key='dl_str_j')
                        plt.close(fig)

    with col_c:
        _card_header('〰️  CRCP — Design', _CRCP_BD)
        with st.container(border=True):
            res_c = _design_block('crcp', 'CRCP',
                                  fc_cyl, ec_psi, cd,
                                  w18_req, pt, zr, so,
                                  _CRCP_BD, _CRCP_BDLT)
            if res_c and st.session_state.get('crcp_layers'):
                if st.button('🏗️ โครงสร้าง CRCP', key='str_c', use_container_width=True):
                    st.session_state['crcp_show_str3'] = \
                        not st.session_state.get('crcp_show_str3', False)
                if st.session_state.get('crcp_show_str3'):
                    rec_cm = st.session_state.get('crcp_rec_d_cm')
                    fig = plot_structure(
                        st.session_state['crcp_layers'],
                        concrete_cm=rec_cm,
                        title=f'CRCP  D = {rec_cm} cm' if rec_cm else 'CRCP Structure')
                    if fig:
                        st.pyplot(fig, use_container_width=True)
                        st.session_state['crcp_struct_bytes'] = fig_to_bytes(fig)
                        st.download_button('⬇️ PNG โครงสร้าง CRCP',
                                           st.session_state['crcp_struct_bytes'],
                                           'struct_crcp.png', 'image/png',
                                           key='dl_str_c')
                        plt.close(fig)

    # ════════════════════════════════════════════════════════
    # Card 4 — Word Report Export
    # ════════════════════════════════════════════════════════
    st.markdown('---')
    with st.container(border=True):
        st.markdown('<div class="rp-card-title">📄 Export รายงาน Word (.docx)</div>',
                    unsafe_allow_html=True)
        date_str  = datetime.now().strftime('%d/%m/%Y %H:%M')
        proj_name = st.session_state.get('project_name', '')
        rc1, rc2  = st.columns(2)

        def _export_btn(prefix, ptype, res, key):
            rows_key   = f'{prefix}_design_rows'
            params_key = f'{prefix}_design_params'
            rec_key    = f'{prefix}_rec_d_cm'
            sbytes_key = f'{prefix}_struct_bytes'

            if res is None or st.session_state.get(rows_key) is None:
                st.markdown(
                    '<div style="background:#F5F5F5;border:1px solid #E0E0E0;'
                    'border-radius:8px;padding:8px 12px;font-size:12px;color:#90A4AE;'
                    'text-align:center">'
                    f'📋 คำนวณ {ptype} ก่อนเพื่อ export</div>',
                    unsafe_allow_html=True)
                return

            try:
                buf = _create_word_report(
                    ptype, proj_name,
                    st.session_state.get(params_key, {}),
                    st.session_state.get(rows_key, []),
                    st.session_state.get(rec_key) or 30,
                    st.session_state.get(sbytes_key),
                    date_str,
                    fig33_bytes=st.session_state.get(f'{prefix}_fig33_bytes'),
                    fig34_bytes=st.session_state.get(f'{prefix}_fig34_bytes'))
            except Exception as e:
                st.error(f'❌ สร้างรายงานไม่สำเร็จ: {e}')
                return

            if buf is None:
                st.error('❌ ไม่พบ python-docx — กรุณาเพิ่ม python-docx ใน requirements.txt')
                return

            fname = f'Report_{prefix.upper()}_{datetime.now().strftime("%Y%m%d_%H%M")}.docx'
            st.download_button(
                f'📥 Report {ptype} (.docx)', buf, fname,
                'application/vnd.openxmlformats-officedocument'
                '.wordprocessingml.document',
                key=key, use_container_width=True)

        with rc1:
            _export_btn('jpcp', 'JPCP/JRCP', res_j, 'dl_word_j')
        with rc2:
            _export_btn('crcp', 'CRCP', res_c, 'dl_word_c')
