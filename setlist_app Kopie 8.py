
import streamlit as st

# PDF export
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

st.set_page_config(page_title="Setlist", layout="wide")
st.title("🎼 Setlist")

# ===== Styles (inspired by Gagenrechner look) =====
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root { --ink:#0f172a; --muted:#475569; --bg:#ffffff; --bgAlt:#f8fafc; --brand:#004D59; }
html, body, [class*="css"]  { font-family: 'Space Mono', monospace; font-size: 15px; }
h1,h2,h3,h4,h5, .stButton>button { font-family: 'Montserrat', sans-serif; font-weight:700; }
.stButton>button { background-color: var(--brand); color:#fff; border:none; border-radius:12px; padding:8px 16px; }
.stButton>button:hover { background-color:#0d6b7a; }
label, .stMarkdown, .stRadio, .stSelectbox, .stMultiSelect { font-size: 15px; }
.small { font-size: 13px; color:var(--muted); }
.block { padding:10px 12px; border:1px solid #e5e7eb; border-radius:12px; background:#fff; }
.row { display:grid; grid-template-columns: 1fr 90px 90px 90px; align-items:center; gap:8px; padding:8px 10px; border-radius:10px; }
.row.even { background: var(--bgAlt); }
.row.odd  { background: var(--bg); }
.actions { display:flex; gap:6px; }
.iconbtn { padding:6px 10px; border:1px solid #e5e7eb; border-radius:8px; background:#fff; }
</style>
""", unsafe_allow_html=True)

# ===== Helpers =====
def mmss_to_seconds(mm, ss):
    try: m = int(mm)
    except: m = 0
    try: s = int(ss)
    except: s = 0
    return max(0, m)*60 + max(0, s)

def mmss_str_to_seconds(mmss: str):
    if not mmss: return 0
    p = str(mmss).strip().split(":")
    if len(p) == 2: return mmss_to_seconds(p[0], p[1])
    return 0

def seconds_to_mmss(t):
    m, s = divmod(max(0, int(t)), 60)
    return f"{m:02d}:{s:02d}"

def total_duration(ids):
    return sum(st.session_state["songs"][sid]["duration_s"] for sid in ids if sid in st.session_state["songs"])

def ensure_state():
    ss = st.session_state
    ss.setdefault("songs", {})
    ss.setdefault("next_song_id", 1)
    ss.setdefault("sets", [[], [], []])  # start with 3
    ss.setdefault("pool", [])
    ss.setdefault("seeded", False)
    ss.setdefault("concert_name", "")

def seed_demo():
    SEED = [
        {"title":"Alors, dont start the blinding lights","artist":"Dua Lipa, Stromae, The Weeknd","mmss":"05:26"},
        {"title":"Avicii","artist":"Avicii","mmss":"04:10"},
        {"title":"Carmabesque","artist":"Coldplay, Stromae, Bizet","mmss":"06:00"},
        {"title":"Clandestino","artist":"Manu Chao","mmss":"03:16"},
        {"title":"Dance Monkey","artist":"Tones and I","mmss":"04:09"},
        {"title":"Die with a smile","artist":"Bruno Mars, Lady Gaga","mmss":"04:15"},
        {"title":"Emergency Hip Hop","artist":"Diverse","mmss":"04:50"},
        {"title":"Feeling Good","artist":"Anthony Newley, Leslie Bricusse","mmss":"04:16"},
        {"title":"Fireflies","artist":"Owl City","mmss":"03:24"},
        {"title":"Hip Hop Mix 2","artist":"Diverse","mmss":"06:12"},
        {"title":"Hopes Stay As They Were","artist":"Harry Styles, Panic at the Disco, Justin Bieber","mmss":"05:16"},
        {"title":"Komet / Monsun","artist":"Udo Lindenberg, Apache207, Tokio Hotel","mmss":"03:34"},
        {"title":"Leave the door open","artist":"Silk Sonic","mmss":"04:08"},
        {"title":"Lets Get Bad","artist":"J Lo, Billie Eilish","mmss":"05:05"},
        {"title":"No Roots","artist":"Alice Merton","mmss":"03:36"},
        {"title":"Oh Johnny","artist":"Jan Delay","mmss":""},
        {"title":"Raw","artist":"Meute","mmss":"05:00"},
        {"title":"Romano Hip Hop","artist":"Gipsy CZ","mmss":"02:30"},
        {"title":"The Code","artist":"Nemo","mmss":"03:12"},
        {"title":"Toxic Industry","artist":"Lil Nas, Britney Spears","mmss":"03:20"},
        {"title":"Valerie","artist":"Mark Ronson, Amy Winehouse","mmss":""},
        {"title":"Vreneli vo Mahala","artist":"Mahala Rai Banda, trad.","mmss":"03:49"}
    ]
    for s in SEED:
        sid = st.session_state["next_song_id"]; st.session_state["next_song_id"] += 1
        st.session_state["songs"][sid] = {
            "title": s["title"],
            "artist": s.get("artist", ""),
            "duration_s": mmss_str_to_seconds(s.get("mmss", "")),
            "key": "C-Dur",
            "tempo": "120"
        }
        st.session_state["pool"].append(sid)

def add_to_set(song_ids, set_idx):
    if not song_ids: return
    lst = st.session_state["sets"][set_idx]
    to_add = [sid for sid in song_ids if sid in st.session_state["pool"]]
    lst.extend(to_add)
    for sid in to_add:
        if sid in st.session_state["pool"]:
            st.session_state["pool"].remove(sid)

def move_within_set(set_idx, sid, direction):
    ids = st.session_state["sets"][set_idx]
    if sid not in ids: return
    pos = ids.index(sid)
    if direction == "up" and pos > 0:
        ids[pos-1], ids[pos] = ids[pos], ids[pos-1]
    if direction == "down" and pos < len(ids)-1:
        ids[pos+1], ids[pos] = ids[pos], ids[pos+1]

def pdf_bytes(pdf):
    out = pdf.output(dest="S")
    return out if isinstance(out, (bytes, bytearray)) else out.encode("latin1", "replace")

def make_pdf_concert(concert_name: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Setliste {concert_name}", ln=1)
    pdf.set_font("Helvetica", "", 11)
    for idx, ids in enumerate(st.session_state["sets"], start=1):
        pdf.set_font("Helvetica","B",12)
        pdf.cell(0,8,f"Set {idx}",ln=1)
        pdf.set_font("Helvetica","",11)
        for pos,sid in enumerate(ids, start=1):
            s=st.session_state["songs"][sid]
            left = f"{pos}. {s['title']}"
            right = f"{seconds_to_mmss(s['duration_s'])}   {s.get('key','')}   {s.get('tempo','')}"
            pdf.cell(120,7,left,0,0)
            pdf.cell(70,7,right,0,1,"R")
        pdf.set_font("Helvetica","B",11)
        pdf.cell(120,7,"Set Dauer",0,0)
        pdf.cell(70,7,seconds_to_mmss(total_duration(ids)),0,1,"R")
        pdf.ln(2)
    total=sum(total_duration(x) for x in st.session_state["sets"])
    pdf.set_font("Helvetica","B",12)
    pdf.cell(120,8,"Gesamtdauer",0,0)
    pdf.cell(70,8,seconds_to_mmss(total),0,1,"R")
    return pdf_bytes(pdf)

def make_pdf_suisa(concert_name: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"SUISA Liste {concert_name}", ln=1)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(110,8,"Titel",0,0)
    pdf.cell(80,8, "Interpret",0,1)
    pdf.set_font("Helvetica","",11)
    for ids in st.session_state["sets"]:
        for sid in ids:
            s=st.session_state["songs"][sid]
            pdf.cell(110,7,s["title"],0,0)
            pdf.cell(80,7,s.get("artist",""),0,1)
    return pdf_bytes(pdf)

# ===== Init =====
ensure_state()
if not st.session_state["seeded"] and not st.session_state["songs"]:
    seed_demo()
    st.session_state["seeded"] = True

# ===== New song (one row incl. Tonart & Tempo) =====
with st.expander("Neuen Song anlegen", expanded=False):
    with st.form("new_song", clear_on_submit=True):
        a,b,c,d,e,f = st.columns([4,4,1,1,1,1])
        title = a.text_input("Titel*", placeholder="z. B. Firework")
        artist = b.text_input("Interpret optional", placeholder="z. B. Katy Perry")
        mm = c.number_input("Minuten", 0, 59, 3)
        ss = d.number_input("Sekunden", 0, 59, 30, 5)
        key = e.text_input("Tonart", value="C-Dur")
        tempo = f.text_input("Tempo", value="120")
        ok = st.form_submit_button("Speichern")
    if ok and title.strip():
        sid = st.session_state["next_song_id"]; st.session_state["next_song_id"] += 1
        st.session_state["songs"][sid] = {
            "title": title.strip(),
            "artist": artist.strip(),
            "duration_s": mmss_to_seconds(mm, ss),
            "key": key.strip() or "C-Dur",
            "tempo": tempo.strip() or "120"
        }
        st.session_state["pool"].append(sid)
        st.success(f"{title} gespeichert und zum Pool hinzugefügt.")

# ===== Set count 1-3 =====
st.subheader("Anzahl Sets")
current_n = len(st.session_state["sets"])
choice = st.radio("Wähle Anzahl Sets", [1,2,3], index=[1,2,3].index(current_n if current_n in [1,2,3] else 3), horizontal=True)
if choice != current_n:
    if choice > current_n:
        st.session_state["sets"].extend([[] for _ in range(choice-current_n)])
    else:
        removed = st.session_state["sets"][choice:]
        back_ids = [sid for sub in removed for sid in sub]
        existing = set(st.session_state["pool"])
        for sid in back_ids:
            if sid not in existing:
                st.session_state["pool"].append(sid); existing.add(sid)
        st.session_state["sets"] = st.session_state["sets"][:choice]
    st.rerun()

# ===== Pool =====
st.subheader("Repertoire")
pool_ids = list(st.session_state["pool"])
pool_labels = [f"{st.session_state['songs'][sid]['title']} ({seconds_to_mmss(st.session_state['songs'][sid]['duration_s'])})" for sid in pool_ids]
label_to_id = {lab:sid for lab,sid in zip(pool_labels, pool_ids)}

if pool_labels:
    c1,c2,c3 = st.columns([4,2,1])
    picks = c1.multiselect("Songs auswählen", pool_labels, default=[])
    dest = c2.selectbox("Ziel Set", [f"Set {i+1}" for i in range(len(st.session_state['sets']))])
    if c3.button("Hinzufügen"):
        idx = int(dest.split(" ")[1]) - 1
        ids = [label_to_id[lab] for lab in picks]
        add_to_set(ids, idx)
        st.rerun()
else:
    st.caption("Der Pool ist leer.")

st.write("")
st.divider()

# ===== Sets (alternating rows + columns) =====
st.subheader("Sets")
for i in range(len(st.session_state["sets"])):
    ids = st.session_state["sets"][i]
    st.markdown(f"**Set {i+1}** · Dauer {seconds_to_mmss(total_duration(ids))}")
    if ids:
        # Header row
        st.markdown(f"<div class='row odd'><b>Titel</b><b>Dauer</b><b>Tonart</b><b>Tempo</b></div>", unsafe_allow_html=True)
        for pos, sid in enumerate(ids):
            s = st.session_state["songs"][sid]
            bg_class = "even" if pos % 2 == 0 else "odd"
            st.markdown(f"<div class='row {bg_class}'><div>{s['title']}</div>"
                        f"<div class='small'>{seconds_to_mmss(s['duration_s'])}</div>"
                        f"<div class='small'>{s.get('key','')}</div>"
                        f"<div class='small'>{s.get('tempo','')}</div></div>", unsafe_allow_html=True)
            c1,c2,c3 = st.columns([0.1,0.1,0.3])
            if c1.button("↑", key=f"up_{i}_{sid}"):
                move_within_set(i, sid, "up"); st.rerun()
            if c2.button("↓", key=f"down_{i}_{sid}"):
                move_within_set(i, sid, "down"); st.rerun()
            if c3.button("Entfernen", key=f"rm_{i}_{sid}"):
                st.session_state["sets"][i].remove(sid)
                if sid not in st.session_state["pool"]:
                    st.session_state["pool"].append(sid)
                st.rerun()
    else:
        st.caption("Noch keine Songs in diesem Set")
    st.write("")

# ===== Export =====
st.subheader("Export")
c1,c2 = st.columns(2)
with c1:
    if HAS_PDF:
        pdf1 = make_pdf_concert(st.session_state.get("concert_name","Setliste"))
        st.download_button("Setliste Konzert als PDF", data=pdf1, file_name="setliste_konzert.pdf", mime="application/pdf")
    else:
        st.error("PDF Export erfordert fpdf2 in requirements.")

with c2:
    if HAS_PDF:
        pdf2 = make_pdf_suisa(st.session_state.get("concert_name","Setliste"))
        st.download_button("SUISA Liste als PDF", data=pdf2, file_name="suisa_liste.pdf", mime="application/pdf")
    else:
        st.error("PDF Export erfordert fpdf2 in requirements.")
