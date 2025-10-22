
import json
import streamlit as st

# Drag & Drop via SortableJS wrapper
HAS_DND = False
try:
    from streamlit_sortables import sort_items as sortable  # okld/streamlit-sortables
    HAS_DND = True
except Exception:
    HAS_DND = False

# PDF export
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

st.set_page_config(page_title="Setlist Builder", layout="wide")
st.title("🎼 Setlist Builder")

st.markdown("""
<style>
.stButton>button { background-color:#0f172a; color:white; border:none; border-radius:10px; padding:8px 14px; }
.stButton>button:hover { background-color:#334155; }
.gray-drop { background:#F3F4F6; border:1px dashed #cbd5e1; padding:12px; border-radius:12px; min-height:56px; }
.chip { display:inline-block; padding:8px 12px; border-radius:12px; background:#0f172a; color:#fff; margin:6px 6px 0 0; font-size:14px; }
.song-line{ display:flex; align-items:center; justify-content:space-between; gap:8px;
           padding:8px 10px; border:1px solid #e5e7eb; border-radius:10px; background:#fff; margin-bottom:6px; }
.song-title{ font-weight:700; color:#0f172a; }
.song-meta{ font-size:12px; opacity:.85; }
</style>
""", unsafe_allow_html=True)

# ---------- helpers ----------
def mmss_to_seconds(mm, ss):
    try: m=int(mm)
    except: m=0
    try: s=int(ss)
    except: s=0
    return max(0,m)*60+max(0,s)

def mmss_str_to_seconds(mmss: str):
    if not mmss: return 0
    p=str(mmss).strip().split(":")
    if len(p)==2: return mmss_to_seconds(p[0], p[1])
    return 0

def seconds_to_mmss(t):
    m,s=divmod(max(0,int(t)),60)
    return f"{m:02d}:{s:02d}"

def total_duration_seconds(ids):
    return sum(st.session_state["songs"][sid]["duration_s"] for sid in ids)

def label_for_pool(sid):
    s=st.session_state["songs"][sid]
    return f"{s['title']} ({seconds_to_mmss(s['duration_s'])})"

def label_for_set(sid):
    # same label string, we keep one canonical to track across lists
    return label_for_pool(sid)

def ensure_state():
    ss=st.session_state
    ss.setdefault("songs", {})
    ss.setdefault("next_song_id", 1)
    ss.setdefault("sets", [[],[]])
    ss.setdefault("pool", [])
    ss.setdefault("seeded", False)
    ss.setdefault("concert_name", "")

ensure_state()

# ---------- seed (Wasabi & Bella Ballerino entfernt) ----------
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
if not st.session_state["seeded"]:
    for s in SEED:
        sid = st.session_state["next_song_id"]; st.session_state["next_song_id"] += 1
        st.session_state["songs"][sid] = {
            "title": s["title"],
            "artist": s.get("artist",""),
            "duration_s": mmss_str_to_seconds(s.get("mmss","")),
            "key": "",
            "tempo": ""  # formerly "note"
        }
        st.session_state["pool"].append(sid)
    st.session_state["seeded"] = True

# ---------- Songpool (cross-list DnD) ----------
st.subheader("🎒 Songpool")
st.caption("Ziehe Songs per Drag & Drop direkt in ein Set. Anzeigen: Titel und Dauer.")

# Build label maps
id_to_label = {}
for sid in list(st.session_state["songs"].keys()):
    id_to_label[sid] = label_for_pool(sid)

# Compose lists of labels for each container
pool_labels = [id_to_label[sid] for sid in st.session_state["pool"]]
set_labels = [[id_to_label[sid] for sid in s] for s in st.session_state["sets"]]

# Render pool + sets with common group for cross-list
cols = st.columns([1,1])
with cols[0]:
    st.markdown("<div class='gray-drop'>Songpool</div>", unsafe_allow_html=True)
    if HAS_DND:
        pool_new = sortable(pool_labels, direction="vertical", key="pool", group="songs")
    else:
        pool_new = pool_labels
        st.info("Drag & Drop Gruppe aktiv, falls streamlit-sortables installiert ist.")

# Sets header and control
st.subheader("🧩 Sets")
top = st.columns([1,1,2])
with top[0]:
    count = st.selectbox("Anzahl Sets", [1,2,3,4,5], index=len(st.session_state["sets"])-1)
    if count != len(st.session_state["sets"]):
        old = st.session_state["sets"]
        st.session_state["sets"] = old + [[] for _ in range(count-len(old))] if count>len(old) else old[:count]
        set_labels = [[id_to_label[sid] for sid in s] for s in st.session_state["sets"]]

# Draw sets in grid
set_cols = st.columns(len(st.session_state["sets"])) if st.session_state["sets"] else []
new_set_labels = []
for i, c in enumerate(set_cols):
    with c:
        st.markdown(f"<div class='gray-drop'>Set {i+1}</div>", unsafe_allow_html=True)
        if HAS_DND:
            new_labels = sortable(set_labels[i] if i < len(set_labels) else [], direction="vertical", key=f"set_{i}", group="songs")
        else:
            new_labels = set_labels[i] if i < len(set_labels) else []
        new_set_labels.append(new_labels)

# Recompute membership from returned labels
label_to_id = {v:k for k,v in id_to_label.items()}
# Pool
new_pool_ids = [label_to_id[l] for l in pool_new if l in label_to_id]
# Sets
new_sets_ids = []
for lab_list in new_set_labels:
    new_sets_ids.append([label_to_id[l] for l in lab_list if l in label_to_id])

# Update state
st.session_state["pool"] = new_pool_ids
st.session_state["sets"] = new_sets_ids

# ---------- Add new song (lands in pool) ----------
st.subheader("➕ Neuen Song anlegen")
with st.form("new_song", clear_on_submit=True):
    a,b,c,d,e = st.columns([3,3,1,1,2])
    with a: title = st.text_input("Titel*")
    with b: artist = st.text_input("Interpret optional")
    with c: mm = st.number_input("Minuten",0,59,3)
    with d: ss = st.number_input("Sekunden",0,59,30,5)
    with e: key = st.text_input("Tonart optional")
    tempo = st.text_input("Tempo optional", placeholder="z. B. 120 bpm oder Ballade")
    ok = st.form_submit_button("Song speichern")
if ok and title.strip():
    sid = st.session_state["next_song_id"]; st.session_state["next_song_id"] += 1
    st.session_state["songs"][sid] = {
        "title": title.strip(),
        "artist": artist.strip(),
        "duration_s": mmss_to_seconds(mm, ss),
        "key": key.strip(),
        "tempo": tempo.strip()
    }
    st.session_state["pool"].append(sid)
    st.success(f"{title} gespeichert und in den Songpool gelegt.")

# ---------- Show sets with details (in list below) ----------
st.markdown("### Aktuelle Sets (Details)")
for i, ids in enumerate(st.session_state["sets"]):
    st.markdown(f"**Set {i+1}** — Dauer {seconds_to_mmss(total_duration_seconds(ids))}")
    for sid in ids:
        s = st.session_state["songs"][sid]
        st.markdown(
            f"<div class='song-line'><span class='song-title'>{s['title']}</span>"
            f"<span class='song-meta'>({seconds_to_mmss(s['duration_s'])}) · {s.get('key','')} · {s.get('tempo','')}</span></div>",
            unsafe_allow_html=True
        )

# ---------- Exports ----------
def make_pdf_concert(concert_name: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Setliste {concert_name}", ln=1)
    pdf.set_font("Helvetica", "", 11)
    for idx, ids in enumerate(st.session_state["sets"], start=1):
        pdf.set_font("Helvetica","B",12); pdf.cell(0,8,f"Set {idx}",ln=1)
        pdf.set_font("Helvetica","",11)
        for pos,sid in enumerate(ids, start=1):
            s=st.session_state["songs"][sid]
            left = f"{pos}. {s['title']}"
            right = f"{seconds_to_mmss(s['duration_s'])}   {s.get('key','')}   {s.get('tempo','')}"
            pdf.cell(120,7,left,0,0)
            pdf.cell(70,7,right,0,1,"R")
        pdf.set_font("Helvetica","B",11)
        pdf.cell(120,7,"Set Dauer",0,0)
        pdf.cell(70,7,seconds_to_mmss(total_duration_seconds(ids)),0,1,"R")
        pdf.ln(2)
    total=sum(total_duration_seconds(x) for x in st.session_state["sets"])
    pdf.set_font("Helvetica","B",12)
    pdf.cell(120,8,"Gesamtdauer",0,0)
    pdf.cell(70,8,seconds_to_mmss(total),0,1,"R")
    return pdf.output(dest="S").encode("latin1","replace")

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
    return pdf.output(dest="S").encode("latin1","replace")

st.markdown("### 📄 Export")
c1,c2 = st.columns(2)
with c1:
    if HAS_PDF:
        pdf_bytes = make_pdf_concert(st.session_state.get("concert_name","Setliste"))
        st.download_button("⬇️ Konzert PDF", data=pdf_bytes, file_name="setliste_konzert.pdf", mime="application/pdf")
    else:
        st.info("PDF Export erfordert fpdf2.")
with c2:
    if HAS_PDF:
        pdf2 = make_pdf_suisa(st.session_state.get("concert_name","Setliste"))
        st.download_button("⬇️ SUISA PDF", data=pdf2, file_name="suisa_liste.pdf", mime="application/pdf")
    else:
        st.info("PDF Export erfordert fpdf2.")
