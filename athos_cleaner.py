import streamlit as st
import pandas as pd
from io import BytesIO
import json

st.set_page_config(page_title="Athos List Cleaner v1", layout="wide")

st.title("🧹 Athos Cleaner (packnam -> Bus Master)")
st.write("Μετατρέπει τα αρχεία του Athos στην καθαρή μορφή 'Κωδικός Ονοματεπώνυμο'")

uploaded_files = st.file_uploader("Ανεβάστε τα αρχεία .xls (packnam)", type=['xls', 'xlsx'], accept_multiple_files=True)

if uploaded_files:
    all_data = []
    
    for file in uploaded_files:
        # Διαβάζουμε το Excel
        df = pd.read_excel(file, header=None)
        
        current_code = None
        
        for index, row in df.iterrows():
            # Μετατροπή σε string και καθαρισμός κενών
            col_0 = str(row[0]).strip() if pd.notna(row[0]) else "" # Κωδικός
            col_4 = str(row[4]).strip() if pd.notna(row[4]) else "" # Τηλέφωνο/Extra Ονόματα
            col_5 = str(row[5]).strip() if pd.notna(row[5]) else "" # Πρώτο Όνομα
            
            # 1. Έλεγχος αν η γραμμή έχει νέο κωδικό (Παραγγελία)
            clean_code = col_0.replace('.0', '')
            if clean_code.isdigit():
                current_code = clean_code
                # Αν υπάρχει όνομα στη στήλη 5, το κρατάμε
                if col_5 and col_5 not in ["nan", "ΌνομαΕπιβάτη", "¼íïìáÅðéâÜôç"]:
                    all_data.append([current_code, col_5])
            
            # 2. Έλεγχος για τα επόμενα ονόματα στην ίδια κράτηση (στήλη 4)
            elif current_code and col_4 and col_4 != "nan":
                # Αν το κελί έχει γράμματα (είναι όνομα) και δεν είναι τηλέφωνο ή header
                if any(c.isalpha() for c in col_4) and "Σελίδα" not in col_4 and "Óåëßäá" not in col_4:
                    # Αν δεν είναι το header "Τηλέφωνο Πελάτη"
                    if "Τηλέφωνο" not in col_4 and "ÔçëÝöùíï" not in col_4:
                        all_data.append([current_code, col_4])

    # Δημιουργία πίνακα
    clean_df = pd.DataFrame(all_data, columns=["Κωδικός", "Ονοματεπώνυμο"])
    
    if not clean_df.empty:
        st.success(f"Εξήχθησαν {len(clean_df)} επιβάτες!")
        
        # Προβολή
        st.subheader("📊 Προεπισκόπηση")
        st.dataframe(clean_df, use_container_width=True, hide_index=True)
        
        # Κείμενο για το Bus Master
        bus_text = ""
        for _, r in clean_df.iterrows():
            bus_text += f"{r['Κωδικός']} {r['Ονοματεπώνυμο']}\n"
        
        st.subheader("📋 Έτοιμο για Αντιγραφή (Bus Master)")
        st.text_area("Κάντε αντιγραφή από εδώ:", value=bus_text, height=300)
        
        # Λήψη Excel (Μορφή DOUBROVNIC)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            clean_df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Λήψη σε Excel (.xlsx)",
            data=output.getvalue(),
            file_name="Clean_Athos_List.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Δεν βρέθηκαν δεδομένα. Σιγουρευτείτε ότι το αρχείο είναι το σωστό .xls από το Athos.")