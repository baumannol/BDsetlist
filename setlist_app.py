
import json
import streamlit as st

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
:root { --ink:#0f172a; --muted:#475569; --accent:#0f172a; --drop:#f3f4f6; }
.stButton>button { background-color:var(--accent); color:white; border:none; border-radius:10px; padding:8px 14px; }
.stButton>button:hover { background-color:#334155; }
.gray-drop { background:var(--drop); border:1px dashed #cbd5e1; padding:12px; border-radius:12px; min-height:64px; }
.card { display:flex; align-items:center; justify-content:space-between; gap:8px;
        padding:10px 12px; border:1px solid #e5e7eb; border-radius:10px; background:#fff; margin-bottom:8px; }
.title { font-weight:700; color:var(--ink); }
.meta { font-size:12px; color:var(--muted); }
.small { font-size:12px; color:var(--muted); }
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
    ss.setdefault("targets_min", [45,45])
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

def add_to_set(song_ids, set_idx, insert_mode="append", before_pos=0):
    if not song_ids: return
    target_list = st.session_state["sets"][set_idx]
    to_add = [sid for sid in song_ids if sid in st.session_state["pool"] or any(sid in s for s in st.session_state["sets"])]
    if insert_mode == "append" or before_pos <= 0 or before_pos > len(target_list):
        target_list.extend(to_add)
    else:
        pos = max(0, min(before_pos-1, len(target_list)))
        for offset, sid in enumerate(to_add):
            target_list.insert(pos+offset, sid)
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

def move_to_position(set_idx, sid, new_pos):
    ids = st.session_state["sets"][set_idx]
    if sid not in ids: return
    ids.remove(sid)
    new_pos = max(0, min(new_pos-1, len(ids)))
    ids.insert(new_pos, sid)

def auto_balance():
    pool = list(st.session_state["pool"])
    sets = st.session_state["sets"]
    targets = [m*60 for m in st.session_state["targets_min"]]
    while pool:
        sid = max(pool, key=lambda s: st.session_state["songs"][s]["duration_s"])
        pool.remove(sid)
        gaps = [targets[i] - sum(st.session_state["songs"][x]["duration_s"] for x in sets[i]) for i in range(len(sets))]
        idx = max(range(len(sets)), key=lambda i: gaps[i])
        sets[idx].append(sid)
    st.session_state["pool"] = []

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
        pdf.cell(70,7,seconds_to_mmss(sum(st.session_state['songs'][x]['duration_s'] for x in ids)),0,1,"R")
        pdf.ln(2)
    total=sum(sum(st.session_state['songs'][x]['duration_s'] for x in s) for s in st.session_state["sets"])
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

# ===== init =====
ensure_state()
if not st.session_state["seeded"] and not st.session_state["songs"]:
    seed_demo()
    st.session_state["seeded"] = True

# ===== top controls =====
top1, top2 = st.columns([2,2])
with top1:
    st.session_state["concert_name"] = st.text_input("Name der Setliste", value=st.session_state["concert_name"])

with top2:
    count = st.selectbox("Anzahl Sets", [1,2,3,4,5], index=len(st.session_state["sets"])-1)
    if count != len(st.session_state["sets"]):
        old = st.session_state["sets"]
        st.session_state["sets"] = old + [[] for _ in range(count-len(old))] if count>len(old) else old[:count]
    # ensure targets length
    t = st.session_state["targets_min"]
    if len(t) < len(st.session_state["sets"]):
        st.session_state["targets_min"] = t + [45]*(len(st.session_state["sets"])-len(t))
    elif len(t) > len(st.session_state["sets"]):
        st.session_state["targets_min"] = t[:len(st.session_state["sets"])]

# ===== Songpool =====
st.subheader("🎒 Songpool")
pool_search = st.text_input("Suche im Songpool", placeholder="Titel oder mm:ss")
pool_ids = [sid for sid in st.session_state["pool"] if pool_search.strip().lower() in st.session_state["songs"][sid]["title"].lower() or pool_search.strip() in seconds_to_mmss(st.session_state["songs"][sid]["duration_s"]) or not pool_search.strip()]

if pool_ids:
    # bulk add
    c1,c2,c3,c4 = st.columns([3,2,2,1])
    pool_labels = [f"{st.session_state['songs'][sid]['title']} ({seconds_to_mmss(st.session_state['songs'][sid]['duration_s'])})" for sid in pool_ids]
    lab_to_id = {lab:sid for lab,sid in zip(pool_labels, pool_ids)}
    with c1:
        picks = st.multiselect("Mehrfachauswahl", pool_labels, default=[])
    with c2:
        dest = st.selectbox("Ziel Set", [f"Set {i+1}" for i in range(len(st.session_state['sets']))])
    with c3:
        insert_mode = st.selectbox("Einfuegen", ["am Ende", "vor Position"])
        before_pos = st.number_input("Position", min_value=1, value=1, step=1, disabled=(insert_mode=="am Ende"))
    with c4:
        if st.button("Hinzufuegen"):
            idx = int(dest.split(" ")[1])-1
            ids = [lab_to_id[lab] for lab in picks]
            add_to_set(ids, idx, insert_mode="append" if insert_mode=="am Ende" else "before", before_pos=int(before_pos))
            st.success("Songs verschoben.")

    st.write("")
    # list view
    for sid in pool_ids:
        s = st.session_state["songs"][sid]
        c1,c2,c3 = st.columns([6,3,1])
        with c1:
            st.markdown(f"<div class='card'><span class='title'>{s['title']}</span> <span class='meta'>({seconds_to_mmss(s['duration_s'])})</span></div>", unsafe_allow_html=True)
        with c2:
            target = st.selectbox("Zu Set", [f"Set {i+1}" for i in range(len(st.session_state['sets']))], key=f"pool_target_{sid}")
        with c3:
            if st.button("➜", key=f"pool_add_{sid}"):
                idx = int(target.split(" ")[1])-1
                add_to_set([sid], idx, insert_mode="append")
                st.experimental_rerun()
else:
    st.caption("Der Songpool ist leer.")

st.write("---")

# ===== Sets =====
st.subheader("🧩 Sets")
for i in range(len(st.session_state["sets"])):
    ids = st.session_state["sets"][i]
    target_min = st.number_input(f"Ziel Minuten fuer Set {i+1}", min_value=1, max_value=180, value=st.session_state['targets_min'][i], key=f"tgt_{i}")
    st.session_state["targets_min"][i] = target_min

    dur = total_duration_seconds(ids)
    col_a, col_b = st.columns([3,2])
    with col_a:
        st.markdown(f"**Set {i+1}**  Dauer {seconds_to_mmss(dur)}  Ziel {target_min:02d}:00")
    with col_b:
        gap = max(0, target_min*60)
        ratio = min(1.0, dur / gap) if gap else 0
        st.progress(ratio, text=f"{seconds_to_mmss(dur)} von {target_min:02d}:00")

    st.markdown("<div class='gray-drop'>", unsafe_allow_html=True)
    if ids:
        for pos, sid in enumerate(list(ids)):
            s = st.session_state["songs"][sid]
            c1,c2,c3,c4,c5 = st.columns([5,1,1,2,1])
            with c1:
                new_key = st.text_input("Tonart", value=s.get("key",""), key=f"key_{i}_{sid}")
                new_tempo = st.text_input("Tempo", value=s.get("tempo",""), key=f"tempo_{i}_{sid}")
                s["key"] = new_key
                s["tempo"] = new_tempo
                st.markdown(
                    f"<div class='card'><span class='title'>{s['title']}</span> "
                    f"<span class='meta'>({seconds_to_mmss(s['duration_s'])}) · {s['key']} · {s['tempo']}</span></div>",
                    unsafe_allow_html=True
                )
            with c2:
                if st.button("↑", key=f"up_{i}_{sid}"):
                    move_within_set(i, sid, "up"); st.experimental_rerun()
            with c3:
                if st.button("↓", key=f"down_{i}_{sid}"):
                    move_within_set(i, sid, "down"); st.experimental_rerun()
            with c4:
                new_pos = st.number_input("Pos", min_value=1, max_value=max(1,len(ids)), value=pos+1, key=f"pos_{i}_{sid}")
                if st.button("Setzen", key=f"setpos_{i}_{sid}"):
                    move_to_position(i, sid, int(new_pos)); st.experimental_rerun()
            with c5:
                if st.button("✖", key=f"rm_{i}_{sid}"):
                    st.session_state["sets"][i].remove(sid)
                    if sid not in st.session_state["pool"]:
                        st.session_state["pool"].append(sid)
                    st.experimental_rerun()
    else:
        st.caption("Noch keine Songs in diesem Set")
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

# ===== helpers row =====
cbal1, cbal2, cbal3 = st.columns([2,2,2])
with cbal1:
    if st.button("Auto fuellen zu Zielzeiten"):
        auto_balance(); st.experimental_rerun()
with cbal2:
    if st.button("Alle Sets leeren und in Pool legen"):
        all_ids = [sid for s in st.session_state["sets"] for sid in s]
        st.session_state["pool"] = list(dict.fromkeys(st.session_state["pool"] + all_ids))
        st.session_state["sets"] = [[] for _ in st.session_state["sets"]]
        st.experimental_rerun()

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
st.subheader("📄 Export")
col1,col2 = st.columns(2)
with col1:
    if HAS_PDF:
        pdf_bytes = make_pdf_concert(st.session_state.get("concert_name","Setliste"))
        st.download_button("⬇️ Konzert PDF", data=pdf_bytes, file_name="setliste_konzert.pdf", mime="application/pdf")
    else:
        st.info("PDF Export erfordert fpdf2 in requirements.")
with col2:
    if HAS_PDF:
        pdf2 = make_pdf_suisa(st.session_state.get("concert_name","Setliste"))
        st.download_button("⬇️ SUISA PDF", data=pdf2, file_name="suisa_liste.pdf", mime="application/pdf")
    else:
        st.info("PDF Export erfordert fpdf2 in requirements.")
