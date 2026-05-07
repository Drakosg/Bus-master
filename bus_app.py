import streamlit as st
import pandas as pd
import random
import hashlib
import base64
import os
import json
import pdfplumber
from io import BytesIO

# 1. ΡΥΘΜΙΣΗ ΣΕΛΙΔΑΣ
st.set_page_config(page_title="Bus Master Pro", layout="wide")

# --- Συναρτήσεις Βοήθειας ---
def get_color_for_code(code):
    if code == "GAP": return "#ffffff"
    if code == "LOCKED": return "#ef5350"
    if code in ["Empty", None]: return "#9ccc65"
    hash_object = hashlib.md5(str(code).encode())
    hex_hash = hash_object.hexdigest()
    r = int(hex_hash[:2], 16) % 128 + 127
    g = int(hex_hash[2:4], 16) % 128 + 127
    b = int(hex_hash[4:6], 16) % 128 + 127
    return f"#{r:02x}{g:02x}{b:02x}"

def get_image_base64(image_input):
    if not image_input: return ""
    try:
        if isinstance(image_input, str):
            with open(image_input, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        return f"data:image/png;base64,{base64.b64encode(image_input.getvalue()).decode()}"
    except: return ""

def allocate_seats_rotation(raw_data, total_seats, locked_seats, priority_codes, day_index, priority_days, links={}):
    groups = {}
    lines = [l.strip() for l in raw_data.split('\n') if l.strip()]
    for line in lines:
        parts = line.replace('-', ' ').split(maxsplit=1)
        code = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else "Unknown"
        target_code = links.get(code, code)
        if target_code not in groups: groups[target_code] = []
        groups[target_code].append(name)
    
    group_codes = sorted(list(groups.keys()))
    is_prio_day = day_index in priority_days
    prio = [c for c in group_codes if c in priority_codes] if is_prio_day else []
    norm = [c for c in group_codes if c not in prio]
    
    if day_index > 1:
        shift = (day_index - 1) * 2
        norm = norm[shift % len(norm):] + norm[:shift % len(norm)]
    else: random.shuffle(norm)
    
    all_pairs = []
    for r in range((total_seats // 4) + 1):
        s = r * 4 + 1
        if s + 1 <= total_seats: all_pairs.append((s, s + 1))
        if s + 3 <= total_seats: all_pairs.append((s + 2, s + 3))
        elif s + 2 <= total_seats: all_pairs.append((s + 2, None))
    
    avail_p = [p for p in all_pairs if p[0] not in locked_seats and (p[1] is None or p[1] not in locked_seats)]
    mapping, pair_idx = {s: "LOCKED" for s in locked_seats}, 0
    assigned_codes = set()
    
    for code in (prio + norm):
        mems = groups[code]
        num, m_i = len(mems), 0
        needed = (num + 1) // 2
        if pair_idx + needed <= len(avail_p):
            while m_i < num:
                if pair_idx >= len(avail_p): break
                s1, s2 = avail_p[pair_idx]
                mapping[s1] = {"code": code, "name": mems[m_i], "pax": num}
                if num - m_i == 1:
                    if s2: mapping[s2] = "GAP"
                    m_i += 1
                else:
                    if s2: mapping[s2] = {"code": code, "name": mems[m_i+1], "pax": num}
                    m_i += 2
                pair_idx += 1
            assigned_codes.add(code)
    
    unassigned = [f"{c} ({len(groups[c])} pax)" for c in group_codes if c not in assigned_codes]
    total_pax_in_list = sum(len(v) for v in groups.values())
    return mapping, unassigned, total_pax_in_list

# --- SIDEBAR ---
with st.sidebar:
    st.header("🏢 Στοιχεία Γραφείου")
    found_logo_path = next((n for n in ["Logo.png", "logo.png", "Logo.PNG", "logo.PNG"] if os.path.exists(n)), None)
    office_logo = found_logo_path if found_logo_path else st.file_uploader("Ανεβάστε Logo.png", type=['png', 'jpg'])
    if found_logo_path: st.image(found_logo_path, width=150)
    
    package_name = st.text_input("Όνομα Πακέτου", "Πανόραμα Ιταλίας")
    travel_date = st.text_input("Ημερομηνία Αναχώρησης", "15/07/2025")
    
    st.divider()
    st.header("📂 Εισαγωγή Λίστας")
    file_input = st.file_uploader("PDF ή Excel", type=['pdf', 'xlsx', 'xls'])
    extracted_text = ""
    if file_input:
        if file_input.name.endswith('.pdf'):
            with pdfplumber.open(file_input) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text: extracted_text += text + "\n"
        else:
            try:
                df_file = pd.read_excel(file_input)
                for _, row in df_file.iterrows():
                    extracted_text += f"{str(row.iloc[0])} {str(row.iloc[1])}\n"
            except: st.error("Σφάλμα ανάγνωσης. Χρησιμοποιήστε τον 'Καθαρισμό Athos'.")
        st.success("Επιτυχής εισαγωγή!")

    st.divider()
    st.header("⚙️ Ρυθμίσεις")
    total_s = st.number_input("Θέσεις", 10, 80, 52)
    num_days = st.number_input("Ημέρες", 1, 15, 4)
    locked_in = st.text_input("LOCKED", "1,2")
    locked_list = [int(x.strip()) for x in locked_in.split(",") if x.strip().isdigit()]
    input_text = st.text_area("Λίστα Επιβατών:", value=extracted_text, height=150)
    codes = sorted(list(set([l.split()[0] for l in input_text.split('\n') if l.strip()]))) if input_text else []
    prio_sel = st.multiselect("Προτεραιότητα", codes)
    prio_days = st.multiselect("Ημέρες Προτεραιότητας", range(1, num_days + 1), default=[1])

    st.divider()
    st.header("🔗 Σύνδεση Κωδικών")
    linked_input = st.text_input("Σύνδεση (π.χ. 101+102)", help="Γράψτε τους κωδικούς χωρισμένους με +")
    links = {}
    if linked_input:
        pairs = [p.strip() for p in linked_input.split(",")]
        for p in pairs:
            if "+" in p:
                parts = [x.strip() for x in p.split("+")]
                main_code = parts[0]
                for other in parts[1:]: links[other] = main_code

    if st.button("🔄 Δημιουργία Πλάνου"):
        st.session_state.full_plans = {}
        for d in range(1, num_days+1):
            m, u, t = allocate_seats_rotation(input_text, total_s, locked_list, prio_sel, d, prio_days, links)
            st.session_state.full_plans[d] = m
        st.session_state.day_now = 1
        st.session_state.swap_src = None
        st.session_state.active_links = links

# --- MAIN ---
tab_cleaner, tab1, tab2, tab3 = st.tabs(["🧹 Καθαρισμός Athos", "🖼️ Πλάνο & Έλεγχος", "📇 Καρτέλες", "📊 Εξαγωγή"])

# 1. ΚΑΡΤΕΛΑ: ΚΑΘΑΡΙΣΜΟΣ ATHOS
with tab_cleaner:
    st.subheader("Μετατροπή packnam7 (Athos) -> Bus Master")
    athos_files = st.file_uploader("Επιλέξτε αρχεία packnam", type=['xls', 'xlsx'], accept_multiple_files=True, key="athos_up")
    
    if athos_files:
        all_cleaned = []
        for f in athos_files:
            try:
                engine = 'xlrd' if f.name.endswith('.xls') else None
                df_athos = pd.read_excel(f, header=None, engine=engine)
                current_c = None
                for idx, row in df_athos.iterrows():
                    c0 = str(row[0]).strip() if pd.notna(row[0]) else ""
                    c4 = str(row[4]).strip() if pd.notna(row[4]) else ""
                    c5 = str(row[5]).strip() if pd.notna(row[5]) else ""
                    clean_c = c0.replace('.0', '')
                    if clean_c.isdigit():
                        current_c = clean_c
                        if c5 and c5 not in ["nan", "ΌνομαΕπιβάτη", "¼íïìáÅðéâÜôç"]:
                            all_cleaned.append([current_c, c5])
                    elif current_c and c4 and c4 != "nan":
                        if any(char.isalpha() for char in c4) and "Σελίδα" not in c4 and "Óåëßäá" not in c4:
                            if "Τηλέφωνο" not in c4 and "ÔçëÝöùíï" not in c4:
                                all_cleaned.append([current_c, c4])
            except Exception as e: st.error(f"Σφάλμα: {e}")
        
        if all_cleaned:
            df_final = pd.DataFrame(all_cleaned, columns=["Κωδικός", "Ονοματεπώνυμο"])
            out_athos = BytesIO()
            with pd.ExcelWriter(out_athos, engine='xlsxwriter') as writer: df_final.to_excel(writer, index=False)
            st.download_button("📥 Λήψη Καθαρής Λίστας (.xlsx)", out_athos.getvalue(), "Clean_Athos_List.xlsx")
            st.dataframe(df_final, use_container_width=True, hide_index=True)
            txt_res = ""
            for _, r in df_final.iterrows(): txt_res += f"{r['Κωδικός']} {r['Ονοματεπώνυμο']}\n"
            st.text_area("Αντιγράψτε το κείμενο:", value=txt_res, height=200)

# ΥΠΟΛΟΙΠΕΣ ΚΑΡΤΕΛΕΣ
if 'full_plans' in st.session_state:
    logo_data = get_image_base64(office_logo)
    active_links = st.session_state.get('active_links', {})
    
    with tab1:
        d = st.session_state.get('day_now', 1)
        day_map = st.session_state.full_plans[d]
        all_pax_in_list = []
        for line in input_text.split('\n'):
            if line.strip():
                parts = line.replace('-', ' ').split(maxsplit=1)
                p_code = parts[0].strip(); p_name = parts[1].strip() if len(parts) > 1 else "Unknown"
                effective_code = active_links.get(p_code, p_code)
                all_pax_in_list.append({"code": effective_code, "name": p_name})
        
        seated_names = [v['name'] for v in day_map.values() if isinstance(v, dict)]
        missing_pax = [p for p in all_pax_in_list if p['name'] not in seated_names]
        c_p1, c_p2, c_p3 = st.columns(3)
        c_p1.metric("Σύνολο", f"{len(all_pax_in_list)} άτομα")
        c_p2.metric("Στο Πλάνο", f"{len(seated_names)} άτομα")
        c_p3.metric("Εκτός", f"{len(missing_pax)} άτομα")
        
        if missing_pax:
            st.error(f"⚠️ Λείπουν {len(missing_pax)} επιβάτες.")
            m_cols = st.columns(4)
            for idx, m in enumerate(missing_pax):
                with m_cols[idx % 4]:
                    if st.button(f"👤 {m['code']} {m['name']}", key=f"miss_{idx}_{d}"):
                        st.session_state.swap_src = ("EXT", m['code'], m['name']); st.toast(f"Επιλέχθηκε: {m['name']}")

        st.divider()
        cx1, cx2, cx3 = st.columns([1,2,1])
        with cx1:
            if st.button("⬅️ Πίσω", key="prev_day") and d > 1: st.session_state.day_now -= 1; st.rerun()
        with cx2: st.markdown(f"<h2 style='text-align:center;'>ΗΜΕΡΑ {d}</h2>", unsafe_allow_html=True)
        with cx3:
            if st.button("Εμπρός ➡️", key="next_day") and d < num_days: st.session_state.day_now += 1; st.rerun()

        for r in range(1, total_s + 1, 4):
            cols = st.columns([1, 1, 0.2, 1, 1])
            for i, pos_val in enumerate([r, r+1, None, r+2, r+3]):
                if pos_val and pos_val <= total_s:
                    pos = pos_val; val = day_map.get(pos); bg = "#9ccc65"; txt = str(pos)
                    if isinstance(val, dict):
                        txt = f"<b>{val['code']}</b><br>{val['name']}<br><small>Pax: {val.get('pax', '?')}</small>"
                        bg = get_color_for_code(val['code'])
                    elif val == "GAP": txt = "<i>Κενό</i>"; bg = "#ffffff"
                    elif val == "LOCKED": txt = "🔒"; bg = "#ef5350"
                    with cols[i]:
                        st.markdown(f'<div style="background-color:{bg}; padding:5px; border-radius:5px; text-align:center; height:100px; font-size:11px; color:black; border:1px solid #333; margin-bottom:5px;"><b>{pos}</b><br>{txt}</div>', unsafe_allow_html=True)
                        if st.button("🎯", key=f"target_{pos}_{d}", use_container_width=True):
                            src = st.session_state.swap_src
                            if src is None: st.session_state.swap_src = pos; st.rerun()
                            elif isinstance(src, tuple) and src[0] == "EXT":
                                p_pax = sum(1 for x in all_pax_in_list if x['code'] == src[1])
                                day_map[pos] = {"code": src[1], "name": src[2], "pax": p_pax}
                                st.session_state.swap_src = None; st.rerun()
                            else:
                                day_map[src], day_map[pos] = day_map.get(pos), day_map.get(src)
                                st.session_state.swap_src = None; st.rerun()

    with tab2:
        summary = {}
        for d_idx, m_plan in st.session_state.full_plans.items():
            for seat, info in m_plan.items():
                if isinstance(info, dict):
                    uid = f"{info['code']}_{info['name']}"
                    if uid not in summary: summary[uid] = {"code": info['code'], "name": info['name'], "pax": info['pax'], "days": {}}
                    summary[uid]["days"][d_idx] = seat
        st.subheader("🖨️ Καρτέλες")
        st.markdown(f"<style>@media print {{ header, [data-testid='stSidebar'], .stButton, [data-testid='stTabList'] {{ display: none !important; }} .card {{ width: 95% !important; border: 1px dashed #666 !important; break-inside: avoid; margin: 15px auto !important; height: 250px !important; }} }} .card {{ width: 95%; border: 2px solid #333; padding: 15px; border-radius: 10px; background: white; color: black; margin-bottom: 20px; }}</style>", unsafe_allow_html=True)
        for key in sorted(summary.keys()):
            p = summary[key]
            st.markdown(f"""<div class="card"><img src="{logo_data}" style="height:45px; float:right;">
                <div style="font-size:12px; color:#666;">{package_name} | {travel_date}</div>
                <h2 style="margin:5px 0; color:#1f77b4; font-size:22px;">{p['name']}</h2>
                <div style="display:flex; justify-content:space-between; border-bottom: 1px solid #eee; padding-bottom:5px;">
                    <span>Κωδικός: <b>{p['code']}</b></span><span>Άτομα: <b>{p['pax']}</b></span>
                </div>
                <table style="width:100%; margin-top:10px; font-size:18px;"><tr>
                    {"".join([f'<td style="border-right:1px solid #eee;">Ημ.{d}: <b>{s}</b></td>' for d, s in p['days'].items()])}
                </tr></table></div>""", unsafe_allow_html=True)

    with tab3:
        data_list = []
        for i, (uid, data) in enumerate(sorted(summary.items()), 1):
            row = {"Α/Α": i, "Κωδικός": data['code'], "Ονοματεπώνυμο": data['name'], "Pax": data['pax']}
            for d_idx in range(1, num_days + 1): row[f"Ημέρα {d_idx}"] = data['days'].get(d_idx, "-")
            data_list.append(row)
        df = pd.DataFrame(data_list)
        
        # ΕΠΕΝΑΦΟΡΑ ΣΥΝΑΡΤΗΣΗΣ ΕΠΙΣΗΜΑΝΣΗΣ
        def highlight_repeats(row):
            day_cols = [c for c in df.columns if "Ημέρα" in c]
            seats = [row[c] for c in day_cols if row[c] != "-"]
            styles = ['' for _ in row]
            if len(seats) > 1 and len(set(seats)) < len(seats):
                for i, col in enumerate(df.columns):
                    if "Ημέρα" in col and row[col] != "-":
                        if seats.count(row[col]) > 1:
                            styles[i] = 'background-color: #ffeb3b; color: black; font-weight: bold'
            return styles

        st.subheader("📊 Εξαγωγή Πλάνου & Έλεγχος")
        # ΕΔΩ ΕΠΕΝΑΦΕΡΘΗΚΕ Η ΕΠΙΣΗΜΑΝΣΗ ΣΤΟ ΠΡΟΒΟΛΕΑ
        st.dataframe(df.style.apply(highlight_repeats, axis=1), use_container_width=True, hide_index=True)
        
        out_plan = BytesIO()
        with pd.ExcelWriter(out_plan, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
        st.download_button("📥 Λήψη Πλάνου Excel", out_plan.getvalue(), f"Plan_{package_name}.xlsx")