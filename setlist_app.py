
import json
import streamlit as st

# Optional in-set Drag and Drop
HAS_SORTABLES = False
try:
    from streamlit_sortables import sort_items as sortable
    HAS_SORTABLES = True
except Exception:
    HAS_SORTABLES = False

# PDF export
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

st.set_page_config(page_title="Setlist Builder", layout="wide")
st.title("🎼 Setlist Builder")

# ===== styles =====
st.markdown("""
<style>
:root { --ink:#0f172a; --muted:#64748b; --chip:#0f172a; --chipText:#ffffff; --drop:#f3f4f6; }
.stButton>button { background-color:var(--ink); color:white; border:none; border-radius:10px; padding:8px 14px; }
.stButton>button:hover { background-color:#334155; }
.gray-drop { background:var(--drop); border:1px dashed #cbd5e1; padding:12px; border-radius:12px; min-height:64px; }
.card { display:flex; align-items:center; justify-content:space-between; gap:8px;
        padding:10px 12px; border:1px solid #e5e7eb; border-radius:10px; background:#fff; margin-bottom:8px; }
.title { font-weight:700; color:var(--ink); }
.meta { font-size:12px; color:var(--muted); }
.chips { display:flex; flex-wrap:wrap; gap:8px; }
.chip { display:inline-flex; align-items:center; gap:8px; background:var(--chip); color:var(--chipText);
        padding:6px 10px; border-radius:999px; font-size:14px; }
.small { font-size:12px; color:var(--muted); }
.iconbtn { padding:6px 10px; border-radius:8px; border:1px solid #e5e7eb; background:#fff; cursor:pointer; }
.iconbtn:hover { background:#f8fafc; }
hr { border:none; height:1px; background:#e5e7eb; margin:12px 0; }
</style>
""", unsafe_allow_html=True)

# ===== helpers =====
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
    return sum(st.session_state["songs"][sid]["duration_s"] for sid in ids if sid in st.session_state["songs"])

def ensure_state():
    ss=st.session_state
    ss.setdefault("songs", {})
    ss.setdefault("next_song_id", 1)
    ss.setdefault("sets", [[],[]])
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
            "artist": s.get("artist",""),
            "duration_s": mmss_str_to_seconds(s.get("mmss","")),
            "key": "",
            "tempo": ""
        }
        st.session_state["pool"].append(sid)

ensure_state()
if not st.session_state["seeded"] and not st.session_state["songs"]:
    seed_demo()
    st.session_state["seeded"] = True

# ===== Songpool top =====
st.subheader("🎒 Songpool")
st.caption("Titel und Dauer sichtbar. Karte per Klick in Sets verschieben.")

if st.session_state["pool"]:
    # bulk add
    c1,c2,c3 = st.columns([3,2,1])
    pool_labels = [f"{st.session_state['songs'][sid]['title']} ({seconds_to_mmss(st.session_state['songs'][sid]['duration_s'])})" for sid in st.session_state["pool"]]
    lab_to_id = {lab:sid for lab,sid in zip(pool_labels, st.session_state["pool"])}
    with c1:
        picks = st.multiselect("Mehrfachauswahl", pool_labels, default=[])
    with c2:
        dest = st.selectbox("Ziel Set", [f"Set {i+1}" for i in range(len(st.session_state['sets']))])
    with c3:
        if st.button("Hinzufuegen"):
            idx = int(dest.split(" ")[1])-1
            for lab in picks:
                sid = lab_to_id[lab]
                if sid in st.session_state["pool"]:
                    st.session_state["pool"].remove(sid)
                st.session_state["sets"][idx].append(sid)
            st.success("Songs verschoben.")

    st.write("")
    # cards view
    for sid in list(st.session_state["pool"]):
        s = st.session_state["songs"][sid]
        c1,c2 = st.columns([6,3])
        with c1:
            st.markdown(f"<div class='card'><span class='title'>{s['title']}</span> <span class='meta'>({seconds_to_mmss(s['duration_s'])})</span></div>", unsafe_allow_html=True)
        with c2:
            subc1, subc2 = st.columns([2,1])
            with subc1:
                target = st.selectbox("Zu Set", [f"Set {i+1}" for i in range(len(st.session_state['sets']))], key=f"pool_target_{sid}")
            with subc2:
                if st.button("➜", key=f"pool_add_{sid}"):
                    idx = int(target.split(" ")[1])-1
                    st.session_state["pool"].remove(sid)
                    st.session_state["sets"][idx].append(sid)
                    st.experimental_rerun()
else:
    st.caption("Der Songpool ist leer.")

st.write("")
st.write("---")

# ===== Sets =====
st.subheader("🧩 Sets")
ctrl1, ctrl2 = st.columns([2,2])
with ctrl1:
    count = st.selectbox("Anzahl Sets", [1,2,3,4,5], index=len(st.session_state["sets"])-1)
    if count != len(st.session_state["sets"]):
        old = st.session_state["sets"]
        st.session_state["sets"] = old + [[] for _ in range(count-len(old))] if count>len(old) else old[:count]

# render sets
for i in range(len(st.session_state["sets"])):
    ids = st.session_state["sets"][i]
    st.markdown(f"**Set {i+1}**  Dauer {seconds_to_mmss(total_duration_seconds(ids))}")
    st.markdown("<div class='gray-drop'>", unsafe_allow_html=True)

    # reorder inside set
    if ids and HAS_SORTABLES:
        labs = [f"{st.session_state['songs'][sid]['title']} ({seconds_to_mmss(st.session_state['songs'][sid]['duration_s'])})" for sid in ids]
        new_labs = sortable(labs, direction="vertical", key=f"sort_set_{i}")
        inv = {lab:sid for lab,sid in zip(labs, ids)}
        st.session_state["sets"][i] = [inv[l] for l in new_labs]

    # rows with details and return to pool button
    if ids:
        for sid in st.session_state["sets"][i]:
            s = st.session_state["songs"][sid]
            c1,c2 = st.columns([8,2])
            with c1:
                st.markdown(
                    f"<div class='card'><span class='title'>{s['title']}</span> "
                    f"<span class='meta'>({seconds_to_mmss(s['duration_s'])}) · {s.get('key','')} · {s.get('tempo','')}</span></div>",
                    unsafe_allow_html=True
                )
            with c2:
                if st.button("⇤ Pool", key=f"back_{i}_{sid}"):
                    st.session_state["sets"][i].remove(sid)
                    if sid not in st.session_state["pool"]:
                        st.session_state["pool"].append(sid)
                    st.experimental_rerun()
    else:
        st.caption("Noch keine Songs in diesem Set")

    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

# ===== Add new song =====
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

# ===== Export =====
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

st.subheader("📄 Export")
c1,c2 = st.columns(2)
with c1:
    if HAS_PDF:
        pdf_bytes = make_pdf_concert(st.session_state.get("concert_name","Setliste"))
        st.download_button("⬇️ Konzert PDF", data=pdf_bytes, file_name="setliste_konzert.pdf", mime="application/pdf")
    else:
        st.info("PDF Export erfordert fpdf2 in requirements.")
with c2:
    if HAS_PDF:
        pdf2 = make_pdf_suisa(st.session_state.get("concert_name","Setliste"))
        st.download_button("⬇️ SUISA PDF", data=pdf2, file_name="suisa_liste.pdf", mime="application/pdf")
    else:
        st.info("PDF Export erfordert fpdf2 in requirements.")
