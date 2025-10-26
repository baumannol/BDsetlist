
import streamlit as st

# PDF export
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

st.set_page_config(page_title="Setlist", layout="wide")
st.title("🎼 Setlist")

# ===== Styles =====
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root { --ink:#0f172a; --muted:#475569; --bg:#ffffff; --bgAlt:#f8fafc; --brand:#004D59; --row:#ffffff; --rowAlt:#f6f7fb; }
html, body, [class*="css"]  { font-family: 'Space Mono', monospace; font-size: 15px; }
h1,h2,h3,h4,h5, .stButton>button { font-family: 'Montserrat', sans-serif; font-weight:700; }
.stButton>button { background-color: var(--brand); color:#fff; border:none; border-radius:10px; padding:6px 12px; font-size:14px; }
.stButton>button:hover { background-color:#0d6b7a; }
label, .stMarkdown, .stRadio, .stSelectbox, .stMultiSelect { font-size: 15px; }
.small { font-size: 13px; color:var(--muted); }
.row { display:grid; grid-template-columns: 1fr 90px 80px 80px 140px; align-items:center; gap:6px; padding:6px 8px; border-radius:8px; }
.row.even { background: var(--rowAlt); }
.row.odd  { background: var(--row); }
.duration { font-weight:700; font-size:14px; }
.controls { display:flex; gap:6px; justify-content:flex-end; }
.setbar { position: sticky; top: 0; z-index: 20; background: #ffffffd9; backdrop-filter: blur(4px);
          border-bottom: 1px solid #e5e7eb; padding:6px 6px 10px 6px; margin-bottom: 8px; }
@media (max-width: 640px){
  .row { grid-template-columns: 1fr 70px 70px 70px 110px; gap:4px; padding:6px; }
  .stButton>button { padding:6px 10px; font-size:13px; }
}
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
    ss.setdefault("targets", [0,0,0])  # per-set target seconds
    ss.setdefault("sel", {})  # selection state for batch actions

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

def latin1_safe(s: str) -> str:
    if s is None: return ""
    replacements = {"–":"-","—":"-","’":"'", "“":'"',"”":'"',"…":"..."}
    for k,v in replacements.items(): s = s.replace(k,v)
    return s.encode("latin-1", "replace").decode("latin-1")

def pdf_bytes(pdf):
    out = pdf.output(dest="S")
    return out if isinstance(out, (bytes, bytearray)) else out.encode("latin1", "replace")

def make_pdf_concert(concert_name: str, set_names):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica","B",18); pdf.cell(0,10, latin1_safe(f"Setliste {concert_name}"), ln=1)
    for idx, ids in enumerate(st.session_state["sets"], start=1):
        name = set_names[idx-1] if idx-1 < len(set_names) else f"Set {idx}"
        pdf.set_font("Helvetica","B",13); pdf.cell(0,8, latin1_safe(name), ln=1)
        pdf.set_font("Helvetica","B",11)
        pdf.cell(10,7,"#",1,0,"C")
        pdf.cell(115,7, latin1_safe("Titel"),1,0)
        pdf.cell(20,7, latin1_safe("Dauer"),1,0,"C")
        pdf.cell(20,7, latin1_safe("Tonart"),1,0,"C")
        pdf.cell(20,7, latin1_safe("Tempo"),1,1,"C")
        pdf.set_font("Helvetica","",11)
        for pos, sid in enumerate(ids, start=1):
            s = st.session_state["songs"][sid]
            pdf.cell(10,7, str(pos),1,0,"C")
            pdf.cell(115,7, latin1_safe(s["title"]),1,0)
            pdf.cell(20,7, seconds_to_mmss(s["duration_s"]),1,0,"C")
            pdf.cell(20,7, latin1_safe(s.get("key","")),1,0,"C")
            pdf.cell(20,7, latin1_safe(s.get("tempo","")),1,1,"C")
        pdf.set_font("Helvetica","B",11)
        pdf.cell(145,7, latin1_safe("Set Dauer"),1,0,"R")
        pdf.cell(40,7, seconds_to_mmss(total_duration(ids)),1,1,"C")
        pdf.ln(3)
    total = sum(total_duration(x) for x in st.session_state["sets"])
    pdf.set_font("Helvetica","B",12); pdf.cell(145,8, latin1_safe("Gesamtdauer"),0,0,"R")
    pdf.cell(40,8, seconds_to_mmss(total),0,1,"C")
    return pdf_bytes(pdf)

def make_pdf_suisa(concert_name: str, set_names):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica","B",18); pdf.cell(0,10, latin1_safe(f"SUISA Liste {concert_name}"), ln=1)
    pdf.set_font("Helvetica","B",11)
    pdf.cell(115,7, latin1_safe("Titel"),1,0)
    pdf.cell(75,7, latin1_safe("Interpret"),1,1)
    pdf.set_font("Helvetica","",11)
    for ids in st.session_state["sets"]:
        for sid in ids:
            s = st.session_state["songs"][sid]
            pdf.cell(115,7, latin1_safe(s["title"]),1,0)
            pdf.cell(75,7, latin1_safe(s.get("artist","")),1,1)
    return pdf_bytes(pdf)

# ===== Init =====
ensure_state()
if not st.session_state["seeded"] and not st.session_state["songs"]:
    seed_demo()
    st.session_state["seeded"] = True

# ===== New song =====
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

# ===== Anzahl Sets =====
st.subheader("Anzahl Sets")
current_n = len(st.session_state["sets"])
choice = st.radio("Wähle Anzahl Sets", [1,2,3], index=[1,2,3].index(current_n if current_n in [1,2,3] else 3), horizontal=True)
if choice != current_n:
    if choice > current_n:
        st.session_state["sets"].extend([[] for _ in range(choice-current_n)])
        st.session_state["targets"].extend([0 for _ in range(choice-current_n)])
    else:
        removed = st.session_state["sets"][choice:]
        back_ids = [sid for sub in removed for sid in sub]
        existing = set(st.session_state["pool"])
        for sid in back_ids:
            if sid not in existing:
                st.session_state["pool"].append(sid); existing.add(sid)
        st.session_state["sets"] = st.session_state["sets"][:choice]
        st.session_state["targets"] = st.session_state["targets"][:choice]
    st.rerun()

# ===== Compact sticky toolbar =====
st.markdown("<div class='setbar'></div>", unsafe_allow_html=True)
tb = st.container()
with tb:
    c1,c2,c3 = st.columns([4,2,1])
    pool_ids = list(st.session_state["pool"])
    pool_labels = [f"{st.session_state['songs'][sid]['title']} ({seconds_to_mmss(st.session_state['songs'][sid]['duration_s'])})" for sid in pool_ids]
    label_to_id = {lab:sid for lab,sid in zip(pool_labels, pool_ids)}
    picks = c1.multiselect("Songs auswählen", pool_labels, default=[])
    dest = c2.selectbox("Ziel Set", [f"Set {i+1}" for i in range(len(st.session_state['sets']))])
    if c3.button("Hinzufügen"):
        idx = int(dest.split(" ")[1]) - 1
        ids = [label_to_id[lab] for lab in picks]
        add_to_set(ids, idx)
        st.rerun()

# ===== Sets with targets, progress, batch actions =====
st.subheader("Sets")
set_names = [f"Set {i+1}" for i in range(len(st.session_state["sets"]))]

for i in range(len(st.session_state["sets"])):
    ids = st.session_state["sets"][i]
    # target controls
    tcol1,tcol2,tcol3 = st.columns([2,2,6])
    with tcol1:
        st.markdown(f"**{set_names[i]}**")
    with tcol2:
        tm = st.text_input(f"Ziel-Länge (MM:SS) · Set {i+1}", value=seconds_to_mmss(st.session_state['targets'][i]) if st.session_state['targets'][i] else "", key=f"t_{i}")
        target_s = 0
        if tm and ":" in tm:
            mm, ss = tm.split(":",1)
            try: target_s = int(mm)*60 + int(ss)
            except: target_s = 0
        st.session_state["targets"][i] = target_s
    with tcol3:
        cur = total_duration(ids)
        tgt = st.session_state["targets"][i] or 0
        pct = 0 if tgt==0 else min(1.0, cur/float(tgt))
        bar = int(pct*100)
        color = "#16a34a" if tgt==0 or cur<=tgt else ("#f97316" if cur<=tgt+60 else "#dc2626")
        st.markdown(f"<div style='height:10px;border-radius:8px;background:#e5e7eb;overflow:hidden;'><div style='width:{bar}%;height:10px;background:{color};'></div></div>", unsafe_allow_html=True)
        st.caption(f"Aktuell {seconds_to_mmss(cur)}{(' / Ziel ' + seconds_to_mmss(tgt)) if tgt else ''}")
    # header row
    st.markdown(f"<div class='row odd'><b>Titel</b><b class='duration'>Dauer</b><b>Tonart</b><b>Tempo</b><b class='small'>Aktionen</b></div>", unsafe_allow_html=True)

    selected_here = []
    if ids:
        for pos, sid in enumerate(ids):
            s = st.session_state["songs"][sid]
            bg_class = "even" if pos % 2 == 0 else "odd"
            st.markdown(f"<div class='row {bg_class}'><div>{latin1_safe(s['title'])}</div>"
                        f"<div class='duration'>{seconds_to_mmss(s['duration_s'])}</div>"
                        f"<div class='small'>{latin1_safe(s.get('key',''))}</div>"
                        f"<div class='small'>{latin1_safe(s.get('tempo',''))}</div>"
                        f"<div class='controls'></div></div>", unsafe_allow_html=True)
            cc1,cc2,cc3,cc4 = st.columns([0.08,0.08,0.22,0.12])
            if cc1.button("↑", key=f"up_{i}_{sid}"): move_within_set(i, sid, "up"); st.rerun()
            if cc2.button("↓", key=f"down_{i}_{sid}"): move_within_set(i, sid, "down"); st.rerun()
            if cc3.button("Entfernen", key=f"rm_{i}_{sid}"):
                st.session_state["sets"][i].remove(sid)
                if sid not in st.session_state["pool"]: st.session_state["pool"].append(sid)
                st.rerun()
            sel_key = (i, sid)
            checked = cc4.checkbox("Ausw.", key=f"sel_{i}_{sid}", value=st.session_state["sel"].get(sel_key, False))
            st.session_state["sel"][sel_key] = checked
            if checked: selected_here.append(sid)
    else:
        st.caption("Noch keine Songs in diesem Set")

    # batch actions
    b1,b2,b3 = st.columns([0.18,0.18,0.64])
    if b1.button("Ausgewählte → anderes Set", key=f"mv_{i}") and selected_here:
        dests = [j for j in range(len(st.session_state["sets"])) if j != i]
        j = dests[0] if dests else None
        if j is not None:
            for sid in selected_here:
                if sid in st.session_state["sets"][i]:
                    st.session_state["sets"][i].remove(sid)
                    st.session_state["sets"][j].append(sid)
                    st.session_state["sel"][(i,sid)] = False
        st.rerun()
    if b2.button("Ausgewählte → Pool", key=f"pool_{i}") and selected_here:
        for sid in selected_here:
            if sid in st.session_state["sets"][i]:
                st.session_state["sets"][i].remove(sid)
                if sid not in st.session_state["pool"]: st.session_state["pool"].append(sid)
                st.session_state["sel"][(i,sid)] = False
        st.rerun()

    st.write("")

# ===== Export =====
st.subheader("Export")
c1,c2 = st.columns(2)
with c1:
    if HAS_PDF:
        try:
            pdf1 = make_pdf_concert(st.session_state.get("concert_name","Setliste"), set_names)
            st.download_button("Setliste Konzert als PDF", data=pdf1, file_name="setliste_konzert.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF Fehler (Konzert): {e}")
    else:
        st.error("PDF Export erfordert fpdf2 in requirements.")

with c2:
    if HAS_PDF:
        try:
            pdf2 = make_pdf_suisa(st.session_state.get("concert_name","Setliste"), set_names)
            st.download_button("SUISA Liste als PDF", data=pdf2, file_name="suisa_liste.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF Fehler (SUISA): {e}")
    else:
        st.error("PDF Export erfordert fpdf2 in requirements.")
