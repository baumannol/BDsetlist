
import streamlit as st
from datetime import timedelta

# ========== INIT PDF ==========
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="Setlist", layout="wide")
st.title("🎼 Setlist")

# ========== STYLES ==========
st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root { --ink:#0f172a; --muted:#475569; --brand:#004D59; --row:#ffffff; --rowAlt:#f6f7fb; }
html, body, [class*="css"]  { font-family:'Space Mono', monospace; font-size:15px; }
h1,h2,h3,.stButton>button { font-family:'Montserrat', sans-serif; font-weight:700; }
.stButton>button { background:var(--brand); color:#fff; border:none; border-radius:8px; padding:2px 8px; font-size:12px; }
.stButton>button:hover { background:#0d6b7a; }
.small { font-size:12px; color:var(--muted); }
.rowhdr { font-weight:700; }
.setbar { position:sticky; top:0; z-index:20; background:#ffffffd9; border-bottom:1px solid #e5e7eb; padding:4px 6px 8px; }
.badge { padding:2px 6px; border-radius:6px; background:#eef2f7; }
</style>
''', unsafe_allow_html=True)

# ========== HELPER FUNCTIONS ==========
def latin1_safe(s):
    if not s: return ''
    rep = {"–": "-", "—": "-", "’": "'", "“": '"', "”": '"', "…": "..."}
    for k,v in rep.items():
        s = s.replace(k, v)
    return s.encode('latin-1','replace').decode('latin-1')

def pdf_bytes(pdf):
    out = pdf.output(dest='S')
    if isinstance(out, bytearray): return bytes(out)
    if isinstance(out, str): return out.encode('latin-1','replace')
    return out

def seconds_to_mmss(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{int(s):02d}"

def total_duration(ids):
    return sum(st.session_state['songs'][sid]['duration_s'] for sid in ids)

# ========== INITIAL STATE ==========
if 'songs' not in st.session_state:
    st.session_state['songs'] = {
        1: {'title': "Alors, dont start the blinding lights", 'duration_s': 326, 'key': "C-Dur", 'tempo': "120", 'artist': "Dua Lipa, Stromae, The Weeknd"},
        2: {'title': "Avicii", 'duration_s': 250, 'key': "C-Dur", 'tempo': "120", 'artist': "Avicii"},
        3: {'title': "Carmabesque", 'duration_s': 360, 'key': "C-Dur", 'tempo': "120", 'artist': "Coldplay, Stromae, Bizet"},
        4: {'title': "Hip Hop Mix 2", 'duration_s': 372, 'key': "C-Dur", 'tempo': "120", 'artist': "Diverse"},
        5: {'title': "Let's Get Bad", 'duration_s': 305, 'key': "C-Dur", 'tempo': "120", 'artist': "J. Lo / Billie Eilish"}
    }

if 'pool' not in st.session_state:
    st.session_state['pool'] = list(st.session_state['songs'].keys())

if 'sets' not in st.session_state:
    st.session_state['sets'] = {0: [], 1: [], 2: []}

if 'targets' not in st.session_state:
    st.session_state['targets'] = [0,0,0]

if 'sel' not in st.session_state:
    st.session_state['sel'] = {}

# ========== SONG ADD ==========
with st.expander("➕ Neuen Song anlegen", expanded=False):
    cols = st.columns([3,1,1,1])
    with cols[0]:
        title = st.text_input("Titel")
    with cols[1]:
        duration_min = st.number_input("Minuten", 0, 20, 4)
    with cols[2]:
        duration_sec = st.number_input("Sekunden", 0, 59, 0)
    with cols[3]:
        artist = st.text_input("Interpret")
    if st.button("Hinzufügen"):
        if title:
            sid = max(st.session_state['songs']) + 1
            st.session_state['songs'][sid] = {'title': title, 'duration_s': duration_min*60+duration_sec, 'key': "C-Dur", 'tempo': "120", 'artist': artist}
            st.session_state['pool'].append(sid)
            st.success(f"Song '{title}' hinzugefügt")

# ========== SET ANZAHL ==========
st.header("Anzahl Sets")
num_sets = st.radio("Wähle Anzahl Sets", [1,2,3], horizontal=True)
for i in range(3):
    if i >= num_sets:
        st.session_state['sets'][i] = []

# ========== REPERTOIRE & ADD =========
st.header("Repertoire")
cols = st.columns([4,2,1])
with cols[0]:
    selection = st.multiselect("Songs auswählen", [st.session_state['songs'][sid]['title'] for sid in st.session_state['pool']])
with cols[1]:
    target_set = st.selectbox("Ziel Set", [f"Set {i+1}" for i in range(num_sets)])
with cols[2]:
    if st.button("Hinzufügen"):
        if selection:
            for name in selection:
                sid = next((k for k,v in st.session_state['songs'].items() if v['title']==name), None)
                if sid:
                    st.session_state['sets'][int(target_set.split()[-1])-1].append(sid)
                    st.session_state['pool'].remove(sid)
            st.rerun()

# ========== SETS =========
st.header("Sets")
set_names = [f"Set {i+1}" for i in range(num_sets)]

for i in range(num_sets):
    ids = st.session_state['sets'][i]
    tcol1, tcol2, tcol3 = st.columns([2,3,5])
    with tcol1:
        st.markdown(f"**{set_names[i]}**")

    with tcol2:
        mins = st.number_input(f"Ziel Minuten · Set {i+1}", min_value=0, max_value=180, step=1, value=int(st.session_state['targets'][i]/60))
        st.session_state['targets'][i] = mins*60

    with tcol3:
        cur = total_duration(ids)
        tgt = st.session_state['targets'][i]
        delta = cur - tgt
        if tgt == 0:
            color = "#16a34a"
        elif delta > 600:
            color = "#dc2626"
        elif delta > 60:
            color = "#f97316"
        else:
            color = "#16a34a"
        pct = 0 if tgt == 0 else min(1.0, cur/float(tgt))
        bar = int(pct*100)
        st.markdown(f"<div style='height:8px;border-radius:8px;background:#e5e7eb;overflow:hidden;'><div style='width:{bar}%;height:8px;background:{color};'></div></div>", unsafe_allow_html=True)
        suffix = f" / Ziel {mins:02d}:00" if tgt else ""
        st.caption(f"Aktuell {seconds_to_mmss(cur)}{suffix}")

    st.markdown("<div class='rowhdr'>Titel · Dauer · Tonart · Tempo</div>", unsafe_allow_html=True)

    if ids:
        for pos,sid in enumerate(ids):
            s = st.session_state['songs'][sid]
            col_t, col_d, col_k, col_tp, col_act, col_sel = st.columns([6,1.1,1.1,1.1,1.6,0.9])
            with col_t:
                st.markdown(latin1_safe(s['title']))
            with col_d:
                st.markdown(f"<span class='badge'><b>{seconds_to_mmss(s['duration_s'])}</b></span>", unsafe_allow_html=True)
            with col_k:
                st.markdown(f"<span class='small'>{latin1_safe(s['key'])}</span>", unsafe_allow_html=True)
            with col_tp:
                st.markdown(f"<span class='small'>{latin1_safe(s['tempo'])}</span>", unsafe_allow_html=True)
            with col_act:
                c1, c2, c3 = st.columns([1,1,2])
                if c1.button("↑", key=f"up_{i}_{sid}"):
                    if pos>0: ids[pos-1], ids[pos] = ids[pos], ids[pos-1]; st.rerun()
                if c2.button("↓", key=f"down_{i}_{sid}"):
                    if pos<len(ids)-1: ids[pos+1], ids[pos] = ids[pos], ids[pos+1]; st.rerun()
                if c3.button("Entfernen", key=f"rm_{i}_{sid}"):
                    ids.remove(sid)
                    st.session_state['pool'].append(sid)
                    st.rerun()
            with col_sel:
                st.checkbox("Ausw.", key=f"sel_{i}_{sid}")
    else:
        st.caption("Noch keine Songs in diesem Set")

# ========== EXPORT =========
st.header("Export")

def make_pdf_concert(name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, latin1_safe(name), ln=True, align="C")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(10, 8, "#", 1); pdf.cell(90, 8, "Titel", 1); pdf.cell(20, 8, "Dauer", 1); pdf.cell(30, 8, "Tonart", 1); pdf.cell(30, 8, "Tempo", 1); pdf.ln()
    pdf.set_font("Helvetica", "", 11)
    idx=1
    for i in range(num_sets):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Set {i+1}", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for sid in st.session_state['sets'][i]:
            s = st.session_state['songs'][sid]
            pdf.cell(10,8,str(idx),1)
            pdf.cell(90,8,latin1_safe(s['title']),1)
            pdf.cell(20,8,seconds_to_mmss(s['duration_s']),1)
            pdf.cell(30,8,latin1_safe(s['key']),1)
            pdf.cell(30,8,latin1_safe(s['tempo']),1)
            pdf.ln()
            idx+=1
        pdf.cell(0,6,"",ln=True)
    return pdf_bytes(pdf)

def make_pdf_suisa():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica","B",16)
    pdf.cell(0,12,"SUISA-Liste",ln=True,align="C")
    pdf.set_font("Helvetica","",12)
    pdf.cell(100,8,"Titel",1); pdf.cell(90,8,"Interpret",1); pdf.ln()
    for sid,s in st.session_state['songs'].items():
        pdf.cell(100,8,latin1_safe(s['title']),1)
        pdf.cell(90,8,latin1_safe(s['artist']),1)
        pdf.ln()
    return pdf_bytes(pdf)

c1,c2 = st.columns(2)
with c1:
    if HAS_PDF:
        try:
            data = make_pdf_concert("Setliste")
            st.download_button("⬇️ Konzert-PDF", data, file_name="setliste.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF Fehler (Konzert): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
with c2:
    if HAS_PDF:
        try:
            data2 = make_pdf_suisa()
            st.download_button("⬇️ SUISA-PDF", data2, file_name="suisa.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF Fehler (SUISA): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
