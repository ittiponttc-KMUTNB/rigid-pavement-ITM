"""
tab3_design.py — Tab 3: Design
Rigid Pavement Design V7
AASHTO 1993 — คำนวณความหนาแผ่นคอนกรีต JPCP/JRCP & CRCP
Layout: side-by-side เหมือน Tab 2
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

# ── สี card ──────────────────────────────────────────────────
_JPCP_BG   = '#F0F7FF'
_JPCP_BD   = '#1565C0'
_JPCP_BDLT = '#90CAF9'
_CRCP_BG   = '#F1F8E9'
_CRCP_BD   = '#2E7D32'
_CRCP_BDLT = '#A5D6A7'

SC_FIXED   = 600.0   # psi — กรมทางหลวง กำหนด max


# ============================================================
# UI Helpers (เหมือน Tab 2)
# ============================================================
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

def _end():
    st.markdown('</div>', unsafe_allow_html=True)

def _verdict_bar(d_cm, d_in, w18_cap, w18_req, ratio, passed, bd_color):
    pct = min(ratio * 100, 200)
    bar_color = '#43A047' if passed else '#E53935'
    label = f'✅ ผ่าน  (×{ratio:.2f})' if passed else f'❌ ไม่ผ่าน  (×{ratio:.2f})'
    st.markdown(
        f'<div style="background:#F5F5F5;border:1px solid {bd_color}33;'
        f'border-radius:8px;padding:8px 10px;margin-bottom:4px">'
        f'<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">'
        f'<span style="font-family:IBM Plex Mono,monospace;font-weight:700;color:{bd_color}">'
        f'D = {d_in} in ({d_cm} ซม.)</span>'
        f'<span style="font-weight:700;color:{bar_color}">{label}</span></div>'
        f'<div style="background:#E0E0E0;border-radius:4px;height:8px">'
        f'<div style="background:{bar_color};width:{pct:.0f}%;height:8px;border-radius:4px"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:10px;'
        f'color:#90A4AE;margin-top:3px">'
        f'<span>W18_cap = {w18_cap:,.0f}</span>'
        f'<span>W18_req = {w18_req:,.0f}</span>'
        f'</div></div>',
        unsafe_allow_html=True)

def _kopt_box(prefix, rec_d_cm, k_opt, k_eff, bd):
    """แสดง k_opt แบบ B — เฉพาะ D_rec"""
    if k_opt is None:
        return
    delta   = k_eff - k_opt
    ok      = k_eff >= k_opt
    bg      = '#E8F5E9' if ok else '#FFEBEE'
    bc      = '#A5D6A7' if ok else '#EF9A9A'
    vc      = '#2E7D32' if ok else '#C62828'
    symbol  = '✅' if ok else '⚠️'
    margin  = f'{delta:+.0f} pci ({delta/k_opt*100:+.1f}%)'
    st.markdown(
        f'<div style="background:{bg};border:2px solid {bc};border-radius:8px;'
        f'padding:10px 12px;margin-top:6px">'
        f'<div style="font-size:12px;font-weight:700;color:{vc};margin-bottom:6px">'
        f'{symbol} k_opt vs k_eff  —  D = {rec_d_cm} ซม. ({round(rec_d_cm/2.54)} in)</div>'
        f'<div style="display:flex;gap:8px">'
        # k_opt
        f'<div style="flex:1;background:white;border-radius:6px;padding:6px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">k_opt (min required)</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;font-weight:700;color:{bd}">'
        f'{k_opt:.0f} pci</div></div>'
        # k_eff
        f'<div style="flex:1;background:white;border-radius:6px;padding:6px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">k_eff (Tab 2)</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;font-weight:700;color:{vc}">'
        f'{k_eff:.0f} pci</div></div>'
        # delta
        f'<div style="flex:1;background:white;border-radius:6px;padding:6px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">Δk = k_eff − k_opt</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:14px;font-weight:700;color:{vc}">'
        f'{margin}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True)


# ============================================================
# Word Report
# ============================================================
def _create_word_report(ptype, proj_name, params, rows, sel_d_cm,
                        struct_fig_bytes, date_str):
    """สร้าง Word report — TH SarabunPSK + Times New Roman (เหมือน V6)"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        return None

    TH  = 'TH SarabunPSK'
    EQ  = 'Times New Roman'
    TS  = Pt(15)

    doc = Document()
    style = doc.styles['Normal']
    style.font.name = TH
    style.font.size = TS

    # Page A4 + margin
    sec = doc.sections[0]
    sec.page_width  = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin  = sec.bottom_margin = Cm(2.5)

    # ── ชื่อเรื่อง ────────────────────────────────────────────
    h0 = doc.add_heading('รายการคำนวณออกแบบความหนาถนนคอนกรีต', 0)
    h0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph('ตามวิธี AASHTO 1993')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].font.name = TH; p.runs[0].font.size = TS

    # ── 1. ข้อมูลทั่วไป ───────────────────────────────────────
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

    # ── 2. ข้อมูลนำเข้า ───────────────────────────────────────
    doc.add_heading('2. ข้อมูลนำเข้า', level=1)
    t = doc.add_table(rows=1, cols=4)
    t.style = 'Table Grid'
    for i, h in enumerate(['พารามิเตอร์', 'สัญลักษณ์', 'ค่า', 'หน่วย']):
        c = t.rows[0].cells[i]
        r = c.paragraphs[0].add_run(h)
        r.bold = True; r.font.name = TH; r.font.size = TS

    input_rows = [
        ('ESAL ออกแบบ',                'W₁₈',      f"{params['w18']:,.0f}",    'ESALs'),
        ('Terminal Serviceability',    'Pt',        f"{params['pt']:.1f}",      '—'),
        ('Reliability',                'R',         f"{params['R']:.0f}",       '%'),
        ('Standard Deviation',         'So',        f"{params['so']:.2f}",      '—'),
        ('k_eff (Tab 2)',               'k_eff',     f"{params['k_eff']:,.0f}", 'pci'),
        ("กำลังอัด (Cube)",             "f'c",       f"{params['fc_cube']:.0f}",'ksc'),
        ("กำลังอัด (Cylinder)",         "f'c,cyl",   f"{params['fc_cyl']:.0f}",'ksc'),
        ('Modulus of Rupture',          'Sc',        f"{params['sc']:.0f}",     'psi'),
        ('Modulus of Elasticity',       'Ec',        f"{params['ec']:,.0f}",    'psi'),
        ('Load Transfer Coefficient',   'J',         f"{params['j']:.1f}",      '—'),
        ('Drainage Coefficient',        'Cd',        f"{params['cd']:.1f}",     '—'),
        ('ΔPSI',                        'ΔPSI',      f"{params['dpsi']:.1f}",   '—'),
    ]
    for param, sym, val, unit in input_rows:
        row = t.add_row().cells
        for i, txt in enumerate([param, sym, val, unit]):
            r = row[i].paragraphs[0].add_run(txt)
            r.font.name = TH; r.font.size = TS

    # ── 3. สมการ AASHTO 1993 ──────────────────────────────────
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
    sym_data = [
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
    ]
    for sym, meaning, unit in sym_data:
        row = tsym.add_row().cells
        for i, txt in enumerate([sym, meaning, unit]):
            r = row[i].paragraphs[0].add_run(txt)
            r.font.name = TH; r.font.size = TS

    doc.add_paragraph()

    # ── 4. ผลเปรียบเทียบ D ────────────────────────────────────
    doc.add_heading('4. ผลการเปรียบเทียบความหนา', level=1)
    t3 = doc.add_table(rows=1, cols=6)
    t3.style = 'Table Grid'
    for i, h in enumerate(['D (ซม.)', 'D (นิ้ว)', 'log10(W18)',
                            'W18 รองรับได้', 'อัตราส่วน', 'ผล']):
        c = t3.rows[0].cells[i]
        r = c.paragraphs[0].add_run(h)
        r.bold = True; r.font.name = TH; r.font.size = TS
    for rv in rows:
        row = t3.add_row().cells
        vals = [
            f"{rv['d_cm']}",
            f"{rv['d_inch']}",
            f"{rv['log_w18']:.4f}",
            f"{rv['w18_cap']:,.0f}",
            f"{rv['ratio']:.3f}",
            'ผ่าน' if rv['passed'] else 'ไม่ผ่าน',
        ]
        for i, txt in enumerate(vals):
            r = row[i].paragraphs[0].add_run(txt)
            r.font.name = TH; r.font.size = TS

    # ── 5. k_opt vs k_eff ─────────────────────────────────────
    k_opt = params.get('k_opt')
    k_eff = params.get('k_eff')
    if k_opt and k_eff:
        doc.add_heading('5. k_opt vs k_eff', level=1)
        delta = k_eff - k_opt
        verdict = 'เพียงพอ' if delta >= 0 else 'ไม่เพียงพอ'
        krows = [
            (f"D แนะนำ",               f"{sel_d_cm} ซม. ({round(sel_d_cm/2.54)} in)"),
            ("k_opt (minimum required)", f"{k_opt:.0f} pci"),
            ("k_eff (จาก Tab 2)",        f"{k_eff:.0f} pci"),
            (f"Δk = k_eff - k_opt",     f"{delta:+.0f} pci  →  {verdict}"),
        ]
        tk = doc.add_table(rows=1, cols=2)
        tk.style = 'Table Grid'
        for i, h in enumerate(['รายการ', 'ค่า']):
            c = tk.rows[0].cells[i]
            r = c.paragraphs[0].add_run(h)
            r.bold = True; r.font.name = TH; r.font.size = TS
        for lbl, val in krows:
            row = tk.add_row().cells
            for i, txt in enumerate([lbl, val]):
                r = row[i].paragraphs[0].add_run(txt)
                r.font.name = TH; r.font.size = TS

    # ── 6. สรุปผล ─────────────────────────────────────────────
    doc.add_heading('6. สรุปผล', level=1)
    sel_row = next((r for r in rows if r['d_cm'] == sel_d_cm), None)
    summary = [
        f"ความหนาที่เลือก: {sel_d_cm} ซม. ({round(sel_d_cm/2.54)} นิ้ว)",
        f"ESAL ที่ต้องการ: {params['w18']:,.0f} ESALs",
    ]
    if sel_row:
        summary += [
            f"ESAL ที่รองรับได้: {sel_row['w18_cap']:,.0f} ESALs",
            f"อัตราส่วน (capacity/demand): {sel_row['ratio']:.3f}",
            f"ผลการตรวจสอบ: {'ผ่านเกณฑ์' if sel_row['passed'] else 'ไม่ผ่านเกณฑ์'}",
        ]
    for txt in summary:
        p = doc.add_paragraph(txt)
        p.runs[0].font.name = TH; p.runs[0].font.size = TS

    # ── รูปโครงสร้าง ─────────────────────────────────────────
    if struct_fig_bytes:
        doc.add_paragraph()
        p = doc.add_paragraph('รูปตัดโครงสร้างชั้นทาง:')
        p.runs[0].font.name = TH; p.runs[0].font.size = TS
        doc.add_picture(BytesIO(struct_fig_bytes), width=Inches(5.5))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ── อ้างอิง ──────────────────────────────────────────────
    doc.add_paragraph()
    ref = doc.add_paragraph(
        'Reference: AASHTO Guide for Design of Pavement Structures 1993')
    ref.runs[0].font.name = TH; ref.runs[0].font.size = Pt(13)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ============================================================
# Design Block — รับ prefix (jpcp / crcp) + ค่าร่วม
# ============================================================
def _design_block(prefix, ptype, fc_cyl, ec_psi, cd, w18_req, pt, zr, so, bd, bdlt):
    """คำนวณและแสดงผล Design สำหรับ JPCP หรือ CRCP"""

    dpsi  = 4.5 - pt
    k_eff = st.session_state.get(f'{prefix}_k_eff')

    # ── ตรวจสอบ prerequisites ─────────────────────────────────
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

    # ── J Selector ───────────────────────────────────────────
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

    # ── แสดง parameters summary ──────────────────────────────
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    _row('W18 (required)',  f'{w18_req:,.0f} ESALs')
    _row('k_eff (Tab 2)',   f'{k_eff:.0f} pci')
    _row("f'c (cylinder)", f"{fc_cyl:.1f} ksc")
    _row('Ec',             f'{ec_psi:,.0f} psi')
    _row('Sc (ทล. lock)',  f'{SC_FIXED:.0f} psi')
    _row('J',              f'{j_val:.1f}', hi=True)
    _row('Cd',             f'{cd:.1f}',    hi=True)
    _row('Pt / ΔPSI',      f'{pt:.1f} / {dpsi:.1f}')
    _row('ZR / So',        f'{zr:.3f} / {so:.2f}')
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

    # ── คำนวณ compare_d ──────────────────────────────────────
    rows = compare_d(D_PAIRS, dpsi, pt, zr, so,
                     SC_FIXED, cd, j_val, ec_psi, k_eff, w18_req)
    st.session_state[f'{prefix}_design_rows'] = rows

    # ── Verdict bars ─────────────────────────────────────────
    passed_rows = [r for r in rows if r['passed']]
    for r in rows:
        _verdict_bar(r['d_cm'], r['d_inch'],
                     r['w18_cap'], w18_req,
                     r['ratio'], r['passed'], bd)

    # ── Recommended D ─────────────────────────────────────────
    if passed_rows:
        rec = min(passed_rows, key=lambda r: r['d_cm'])
        _mbox(f'✅ D แนะนำ ({ptype})',
              f"{rec['d_inch']} in ({rec['d_cm']} ซม.)",
              f"W18 capacity = {rec['w18_cap']:,.0f}",
              '#2E7D32' if prefix == 'crcp' else '#1565C0',
              '#E8F5E9' if prefix == 'crcp' else '#E3F2FD')
        st.session_state[f'{prefix}_rec_d_cm'] = rec['d_cm']
    else:
        st.markdown(
            '<div style="background:#FFEBEE;border:1px solid #EF9A9A;'
            'border-radius:8px;padding:8px 12px;font-size:12px;color:#C62828">'
            '❌ ไม่มี D ที่ผ่านเกณฑ์ในช่วง 25–35 ซม. — พิจารณาเพิ่ม k_eff หรือลด J'
            '</div>', unsafe_allow_html=True)
        st.session_state[f'{prefix}_rec_d_cm'] = None

    # ── k_opt แบบ B (เฉพาะ D_rec) ────────────────────────────
    sel_d_cm = st.session_state.get(f'{prefix}_rec_d_cm') or 30
    sel_d_in = round(sel_d_cm / 2.54)
    k_opt = find_optimum_k(w18_req, sel_d_in, dpsi, pt, zr, so,
                           SC_FIXED, cd, j_val, ec_psi)
    _kopt_box(prefix, sel_d_cm, k_opt, k_eff, bd)

    # ── store params for report ───────────────────────────────
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
# MAIN
# ============================================================
def render_tab3():
    ed   = st.session_state.get('esal_data')
    pt   = st.session_state.get('pt',   2.0)
    so   = st.session_state.get('so',   0.35)
    R    = st.session_state.get('reliability', 90)
    zr   = get_zr(R)

    # W18 — จาก JSON หรือ manual
    w18_from_json = None
    if ed:
        from engine import compute_esal_for_d
        w18_from_json, _, _ = compute_esal_for_d(
            ed['traffic_data'], pt,
            ed['lane_factor'], ed['direction_factor'], 30)

    kj = st.session_state.get('jpcp_k_eff')
    kc = st.session_state.get('crcp_k_eff')

    # ── Status bar ───────────────────────────────────────────
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

    # ── W18 Input ─────────────────────────────────────────────
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
    st.markdown('<div class="rp-card-title">🔢 W18 — ESAL ออกแบบ</div>',
                unsafe_allow_html=True)

    if ed:
        # มี JSON → ใช้อัตโนมัติ แต่ให้ override ได้
        use_manual = st.checkbox(
            'กรอก W18 เองแทน (override จาก JSON)',
            value=st.session_state.get('w18_manual_mode', False),
            key='w18_manual_mode')
        if use_manual:
            w18_req = st.number_input(
                'W18 (ESALs)', min_value=100_000, max_value=500_000_000,
                value=st.session_state.get('w18_manual', int(w18_from_json)),
                step=100_000, key='w18_manual',
                format='%d')
            st.caption(f'W18 จาก JSON = {w18_from_json:,.0f} ESALs (ไม่ได้ใช้)')
        else:
            w18_req = w18_from_json
            st.markdown(
                f'<div class="rp-status-ok" style="font-size:13px">'
                f'✅ ใช้ W18 = <b>{w18_req:,.0f} ESALs</b> จาก ESAL JSON (D = 30 ซม.)'
                f'</div>', unsafe_allow_html=True)
    else:
        # ไม่มี JSON → กรอกเอง
        st.session_state['w18_manual_mode'] = True
        w18_req = st.number_input(
            'W18 (ESALs) — กรอกเอง', min_value=100_000, max_value=500_000_000,
            value=st.session_state.get('w18_manual', 5_000_000),
            step=100_000, key='w18_manual',
            format='%d',
            help='กรอก ESAL ออกแบบโดยตรง (ไม่มี JSON)')
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Shared Parameters ─────────────────────────────────────
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
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
    fc_cyl = convert_cube_to_cyl(fc_cube)   # ksc
    ec_psi = calc_ec(fc_cyl)                # psi
    with c2:
        st.markdown(
            f'<div style="background:#FFF3CD;border:1px solid #FFECB3;'
            f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
            f'<div style="font-size:10px;color:#90A4AE">f\'c,cyl = 0.8 × f\'c,cube</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
            f'font-weight:700;color:#1565C0">{fc_cyl:.0f} ksc</div>'
            f'<div style="font-size:10px;color:#90A4AE">Ec = {ec_psi:,.0f} psi</div></div>',
            unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div style="background:#E8F5E9;border:1px solid #A5D6A7;'
            f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
            f'<div style="font-size:10px;color:#90A4AE">Sc — ทล. กำหนด (lock)</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
            f'font-weight:700;color:#2E7D32">{SC_FIXED:.0f} psi</div>'
            f'<div style="font-size:10px;color:#90A4AE">Modulus of Rupture</div></div>',
            unsafe_allow_html=True)

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    cd = st.select_slider(
        'Cd — Drainage Coefficient (ใช้ร่วมกัน)',
        options=[1.0, 1.1, 1.2],
        value=st.session_state.get('cd', 1.0),
        key='cd',
        format_func=lambda x: f'{x:.1f}',
        help='1.0 = ระบายน้ำปกติ | 1.2 = ระบายน้ำดีมาก')
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Side-by-side Design ───────────────────────────────────
    col_j, col_c = st.columns(2)

    with col_j:
        _card(_JPCP_BG, _JPCP_BD)
        _title('🔲  JPCP / JRCP — Design', _JPCP_BD, _JPCP_BDLT)
        res_j = _design_block('jpcp', 'JPCP/JRCP',
                              fc_cyl, ec_psi, cd,
                              w18_req, pt, zr, so,
                              _JPCP_BD, _JPCP_BDLT)
        # ปุ่ม plot structure
        if res_j and st.session_state.get('jpcp_layers'):
            if st.button('🏗️ โครงสร้าง JPCP', key='str_j',
                         use_container_width=True):
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
        _end()

    with col_c:
        _card(_CRCP_BG, _CRCP_BD)
        _title('〰️  CRCP — Design', _CRCP_BD, _CRCP_BDLT)
        res_c = _design_block('crcp', 'CRCP',
                              fc_cyl, ec_psi, cd,
                              w18_req, pt, zr, so,
                              _CRCP_BD, _CRCP_BDLT)
        # ปุ่ม plot structure
        if res_c and st.session_state.get('crcp_layers'):
            if st.button('🏗️ โครงสร้าง CRCP', key='str_c',
                         use_container_width=True):
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
        _end()

    # ── Word Report Export ────────────────────────────────────
    st.markdown('---')
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
    st.markdown('<div class="rp-card-title">📄 Export รายงาน Word (.docx)</div>',
                unsafe_allow_html=True)

    date_str  = datetime.now().strftime('%d/%m/%Y %H:%M')
    proj_name = st.session_state.get('project_name', '')

    rc1, rc2 = st.columns(2)
    with rc1:
        can_j = (res_j is not None and
                 st.session_state.get('jpcp_design_rows') is not None)
        if can_j:
            buf = _create_word_report(
                'JPCP/JRCP', proj_name,
                st.session_state.get('jpcp_design_params', {}),
                st.session_state.get('jpcp_design_rows', []),
                st.session_state.get('jpcp_rec_d_cm') or 30,
                st.session_state.get('jpcp_struct_bytes'),
                date_str)
            if buf:
                st.download_button(
                    '📥 Report JPCP/JRCP (.docx)', buf,
                    f'Report_JPCP_{datetime.now().strftime("%Y%m%d_%H%M")}.docx',
                    'application/vnd.openxmlformats-officedocument'
                    '.wordprocessingml.document',
                    key='dl_word_j', use_container_width=True)
        else:
            st.info('คำนวณ JPCP ก่อนเพื่อ export report')

    with rc2:
        can_c = (res_c is not None and
                 st.session_state.get('crcp_design_rows') is not None)
        if can_c:
            buf = _create_word_report(
                'CRCP', proj_name,
                st.session_state.get('crcp_design_params', {}),
                st.session_state.get('crcp_design_rows', []),
                st.session_state.get('crcp_rec_d_cm') or 30,
                st.session_state.get('crcp_struct_bytes'),
                date_str)
            if buf:
                st.download_button(
                    '📥 Report CRCP (.docx)', buf,
                    f'Report_CRCP_{datetime.now().strftime("%Y%m%d_%H%M")}.docx',
                    'application/vnd.openxmlformats-officedocument'
                    '.wordprocessingml.document',
                    key='dl_word_c', use_container_width=True)
        else:
            st.info('คำนวณ CRCP ก่อนเพื่อ export report')

    st.markdown('</div>', unsafe_allow_html=True)
