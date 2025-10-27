
# -*- coding: utf-8 -*-
# setlist_app.py — v1.1 (compact UI, bigger fonts, improved PDFs)
import io
import csv
import streamlit as st

# Optional PDF export
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

# ---------- Page ----------
st.set_page_config(page_title="Setlist", layout="wide")
st.title("🎼 Setlist")

# ---------- Styles (compact, Gagenrechner-like) ----------
def inject_styles():
    st.markdown(
        """
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root {
  --ink:#0f172a; --muted:#475569; --brand:#004D59; --brand2:#0d6b7a;
  --row:#f3f6fb; --row2:#eef2f7;
}
html, body, [class*="css"] {
  font-family:'Space Mono', monospace;
  font-size:18px; /* +20% bigger */
  color:var(--ink);
}
h1,h2,h3,.stButton>button {
  font-family:'Montserrat', sans-serif; font-weight:700;
}

/* pills for radio */
div[data-testid="stRadio"] > label { display:none; }
div[data-testid="stRadio"] div[role="radiogroup"] { display:flex; gap:12px; }
div[role="radio"] {
  background:#e2e8f0; border:1px solid #cbd5e1;
  padding:6px 14px; border-radius:9999px;
}
div[role="radio"][aria-checked="true"] {
  background:var(--brand); color:#fff; border-color:var(--brand);
}
div[role="radio"] p { margin:0; font-weight:700; }

/* set cards */
.set-card { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:10px 12px; margin-bottom:12px; }
.set-title { font-weight:700; }
.progress-outer { height:10px; border-radius:10px; background:#e5e7eb; overflow:hidden; }
.progress-inner { height:10px; width:0%; background:#16a34a; }
.set-meta { font-size:16px; color:var(--muted); min-width:180px; text-align:right; }

/* rows */
.rowhdr { font-weight:700; margin:6px 0 4px; }
.row { display:flex; align-items:center; gap:8px; padding:4px 6px; border-radius:8px; }
.row.alt { background:var(--row); }
.cell-title { flex:1; font-size:18px; }
.cell-badge { min-width:72px; text-align:center; background:var(--row2); padding:2px 8px; border-radius:6px; font-weight:700; }
.cell-meta { width:92px; text-align:center; font-size:16px; color:var(--muted); }

/* compact buttons */
.small-btn > button { padding:2px 10px; border-radius:8px; border:1px solid #cbd5e1; background:#fff; }
.small-btn > button:hover { background:#f3f4f6; }
</style>
        """,
        unsafe_allow_html=True,
    )

inject_styles()

# ---------- Helpers ----------
def latin1_safe(s: str) -> str:
    if s is None: return ""
    rep = {"–":"-","—":"-","’":"'", "“":'"',"”":'"',"…":"..."}
    for k,v in rep.items(): s = s.replace(k, v)
    return s.encode("latin-1","replace").decode("latin-1")

def pdf_bytes(pdf):
    out = pdf.output(dest="S")
    if isinstance(out, bytearray): return bytes(out)
    if isinstance(out, str): return out.encode("latin-1","replace")
    return out

def seconds_to_mmss(total: int) -> str:
    total = max(0, int(total)); m, s = divmod(total, 60); return f"{m:02d}:{s:02d}"

def mmss_to_seconds(mm: int, ss: int) -> int:
    return max(0, int(mm))*60 + max(0, int(ss))

# ---------- State ----------
ss = st.session_state
if "songs" not in ss:
    ss["songs"] = {
        1: {"title": "Alors, dont start the blinding lights", "duration_s": 326, "key": "", "tempo": "", "artist": "Dua Lipa, Stromae, The Weeknd"},
        2: {"title": "Avicii", "duration_s": 250, "key": "", "tempo": "", "artist": "Avicii"},
        3: {"title": "Carmabesque", "duration_s": 360, "key": "", "tempo": "", "artist": "Coldplay, Stromae, Bizet"},
        4: {"title": "Clandestino", "duration_s": 196, "key": "", "tempo": "", "artist": "Manu Chao"},
        5: {"title": "Dance Monkey", "duration_s": 249, "key": "", "tempo": "", "artist": "Tones and I"},
        6: {"title": "Die with a smile", "duration_s": 255, "key": "", "tempo": "", "artist": "Bruno Mars, Lady Gaga"},
        7: {"title": "Emergency Hip Hop", "duration_s": 290, "key": "", "tempo": "", "artist": "Diverse"},
        8: {"title": "Feeling Good", "duration_s": 256, "key": "", "tempo": "", "artist": "Anthony Newley, Leslie Bricusse"},
        9: {"title": "Fireflies", "duration_s": 204, "key": "", "tempo": "", "artist": "Owl City"},
        10: {"title": "Hip Hop Mix 2", "duration_s": 372, "key": "", "tempo": "", "artist": "Diverse"},
        11: {"title": "Hopes Stay As They Were", "duration_s": 316, "key": "", "tempo": "", "artist": "Harry Styles, Panic At The Disco, Justin Bieber"},
        12: {"title": "Komet / Monsun", "duration_s": 214, "key": "", "tempo": "", "artist": "Udo Lindenberg, Apache207, Tokio Hotel"},
        13: {"title": "Leave the door open", "duration_s": 248, "key": "", "tempo": "", "artist": "Silk Sonic"},
        14: {"title": "Lets Get Bad", "duration_s": 305, "key": "", "tempo": "", "artist": "J. Lo, Billie Eilish"},
        15: {"title": "No Roots", "duration_s": 216, "key": "", "tempo": "", "artist": "Alice Merton"},
        16: {"title": "Oh Johnny", "duration_s": 0, "key": "", "tempo": "", "artist": "Jan Delay"},
        17: {"title": "Raw", "duration_s": 300, "key": "", "tempo": "", "artist": "Meute"},
        18: {"title": "Romano Hip Hop", "duration_s": 150, "key": "", "tempo": "", "artist": "Gipsy CZ"},
        19: {"title": "The Code", "duration_s": 192, "key": "", "tempo": "", "artist": "Nemo"},
        20: {"title": "Toxic Industry", "duration_s": 200, "key": "", "tempo": "", "artist": "Lil Nas, Britney Spears"},
        21: {"title": "Valerie", "duration_s": 0, "key": "", "tempo": "", "artist": "Mark Ronson, Amy Winehouse"},
        22: {"title": "Vreneli vo Mahala", "duration_s": 229, "key": "", "tempo": "", "artist": "Mahala Rai Banda, trad."},
        23: {"title": "Uptown Funk", "duration_s": 270, "key": "", "tempo": "", "artist": "Mark Ronson ft. Bruno Mars"},
        24: {"title": "Shut Up and Dance", "duration_s": 210, "key": "", "tempo": "", "artist": "WALK THE MOON"},
        25: {"title": "Sweet Caroline", "duration_s": 205, "key": "", "tempo": "", "artist": "Neil Diamond"},
    }
    ss["next_id"] = max(ss["songs"].keys()) + 1
    ss["pool"] = sorted(ss["songs"].keys(), key=lambda sid: ss["songs"][sid]["title"].casefold())
    ss["sets"] = {0: [], 1: [], 2: []}
    ss["targets"] = [0, 0, 0]   # seconds
    ss["sel"] = {}              # (set_index, song_id) -> bool
    ss["num_sets"] = 3
    ss["concert_name"] = ""

# ---------- New Song (collapsed) ----------
with st.expander("➕ Neuen Song anlegen", expanded=False):
    c1,c2,c3,c4,c5,c6 = st.columns([3,1,1,2,1.2,1.2])
    n_title = c1.text_input("Titel", key="new_title")
    n_min   = c2.number_input("Minuten", 0, 99, 3, key="new_min")
    n_sec   = c3.number_input("Sekunden", 0, 59, 0, key="new_sec")
    n_artist= c4.text_input("Interpret (optional)", key="new_artist")
    # Tempo & Tonart: no defaults
    n_tempo = c5.text_input("Tempo", value="", key="new_tempo")
    n_key   = c6.text_input("Tonart", value="", key="new_key")
    if st.button("Hinzufügen", key="btn_add_song"):
        if n_title.strip():
            sid = ss["next_id"]; ss["next_id"] += 1
            ss["songs"][sid] = {
                "title": n_title.strip(),
                "duration_s": mmss_to_seconds(n_min, n_sec),
                "key": n_key.strip(),
                "tempo": n_tempo.strip(),
                "artist": n_artist.strip(),
            }
            ss["pool"].append(sid)
            ss["pool"].sort(key=lambda x: ss["songs"][x]["title"].casefold())
            st.success(f"Song „{n_title}“ hinzugefügt.")

# ---------- Set count (pills) ----------
st.subheader("Anzahl Sets")
choice = st.radio(
    "",
    options=["1 Set","2 Sets","3 Sets"],
    index=ss["num_sets"]-1,
    horizontal=True,
    label_visibility="collapsed",
    key="num_sets_radio"
)
ss["num_sets"] = ["1 Set","2 Sets","3 Sets"].index(choice)+1
num_sets = ss["num_sets"]

# ---------- Pool ----------
st.subheader("Repertoire")
rc1, rc2, rc3 = st.columns([4,2,1])
pool_sorted = sorted(ss["pool"], key=lambda sid: ss["songs"][sid]["title"].casefold())
def pool_label(sid: int) -> str:
    s = ss["songs"][sid]
    return f"{s['title']} ({seconds_to_mmss(s['duration_s'])})"
picks = rc1.multiselect("Songs auswählen", options=pool_sorted, format_func=pool_label, key="pick_from_pool")
dest  = rc2.selectbox("Ziel Set", [f"Set {i+1}" for i in range(num_sets)], key="dest_set")
if rc3.button("Hinzufügen", key="btn_add_to_set"):
    if picks:
        idx = int(dest.split()[-1]) - 1
        ss["sets"][idx].extend(picks)
        for sid in picks:
            if sid in ss["pool"]:
                ss["pool"].remove(sid)
        st.rerun()

# ---------- Sets ----------
def total_duration(ids): return sum(ss["songs"][sid]["duration_s"] for sid in ids)

st.subheader("Sets")
names = [f"Set {i+1}" for i in range(num_sets)]
for i in range(num_sets):
    ids = ss["sets"][i]
    st.markdown("<div class='set-card'>", unsafe_allow_html=True)

    cur = total_duration(ids)
    tgt = ss["targets"][i]  # seconds
    if tgt == 0: color = "#16a34a"; pct = 0
    else:
        delta = cur - tgt
        if delta > 600: color = "#dc2626"
        elif delta > 60: color = "#f97316"
        else: color = "#16a34a"
        pct = min(1.0, cur/float(tgt)) if tgt else 0
    bar = int(pct*100)

    a,b,c = st.columns([2.4,4,2.6])
    a.markdown(f"<div class='set-title'>🎵 {names[i]}</div>", unsafe_allow_html=True)
    minutes = a.number_input(f"Ziel Minuten · {names[i]}", 0, 180, int(tgt//60), key=f"target_min_{i}")
    ss["targets"][i] = minutes*60
    b.markdown(f"<div class='progress-outer'><div class='progress-inner' style='width:{bar}%;background:{color};'></div></div>", unsafe_allow_html=True)
    c.markdown(f"<div class='set-meta'>Aktuell {seconds_to_mmss(cur)}<br/>{('Ziel %02d:00'%minutes) if minutes else 'Ziel –'}</div>", unsafe_allow_html=True)

    st.markdown("<div class='rowhdr'>Titel · Dauer · Tonart · Tempo</div>", unsafe_allow_html=True)
    if ids:
        for pos, sid in enumerate(ids):
            s = ss["songs"][sid]
            alt = " alt" if pos%2==1 else ""
            st.markdown(f"<div class='row{alt}'>", unsafe_allow_html=True)
            c_t, c_d, c_k, c_tp, c_act, c_sel = st.columns([6,1.1,1.1,1.1,2,1])
            c_t.markdown(f"<div class='cell-title'>{latin1_safe(s['title'])}</div>", unsafe_allow_html=True)
            c_d.markdown(f"<div class='cell-badge'>{seconds_to_mmss(s['duration_s'])}</div>", unsafe_allow_html=True)
            c_k.markdown(f"<div class='cell-meta'>{latin1_safe(s.get('key','')) or '-'}</div>", unsafe_allow_html=True)
            c_tp.markdown(f"<div class='cell-meta'>{latin1_safe(s.get('tempo','')) or '-'}</div>", unsafe_allow_html=True)
            # compact action buttons
            u,dn,rm = c_act.columns(3)
            if u.button("↑", key=f"up_{i}_{sid}") and pos>0:
                ids[pos-1], ids[pos] = ids[pos], ids[pos-1]; st.rerun()
            if dn.button("↓", key=f"down_{i}_{sid}") and pos < len(ids)-1:
                ids[pos+1], ids[pos] = ids[pos], ids[pos+1]; st.rerun()
            if rm.button("Entf", key=f"rm_{i}_{sid}"):
                ids.remove(sid)
                if sid not in ss["pool"]:
                    ss["pool"].append(sid)
                    ss["pool"].sort(key=lambda x: ss["songs"][x]["title"].casefold())
                st.rerun()
            # selection
            sel_key = (i, sid)
            checked = c_sel.checkbox("Ausw.", key=f"sel_{i}_{sid}", value=ss["sel"].get(sel_key, False))
            ss["sel"][sel_key] = checked
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.caption("Noch keine Songs in diesem Set")

    # Batch toolbar
    left, mid, right = st.columns([2.6, 2.6, 4.8])
    if left.button("Ausgewählte → anderes Set", key=f"mv_batch_{i}"):
        selected = [sid for (si, sid), v in ss["sel"].items() if si==i and v]
        targets = [j for j in range(num_sets) if j != i]
        j = targets[0] if targets else i
        for sid in selected:
            if sid in ss["sets"][i]:
                ss["sets"][i].remove(sid)
                ss["sets"][j].append(sid)
                ss["sel"][(i, sid)] = False
        st.rerun()
    target_choice = mid.selectbox(f"Ziel für Auswahl – {names[i]}", [f"Set {j+1}" for j in range(num_sets) if j!=i] or [names[i]], key=f"batch_dest_{i}")
    ss[f"batch_target_{i}"] = int(target_choice.split()[-1]) - 1
    if right.button("Ausgewählte → Pool", key=f"pool_batch_{i}"):
        selected = [sid for (si, sid), v in ss["sel"].items() if si==i and v]
        for sid in selected:
            if sid in ss["sets"][i]:
                ss["sets"][i].remove(sid)
                if sid not in ss["pool"]:
                    ss["pool"].append(sid)
                    ss["pool"].sort(key=lambda x: ss["songs"][x]["title"].casefold())
                ss["sel"][(i, sid)] = False
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Exports side-by-side ----------
st.subheader("Export")
ec1, ec2, ec3, ec4 = st.columns([3,3,3,3])

def make_pdf_concert(title: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    # larger, stage-friendly fonts
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, latin1_safe(f"Konzert-Setlist {title}"), ln=1, align="L")
    pdf.ln(2)
    for i in range(num_sets):
        ids = ss["sets"][i]
        cur = seconds_to_mmss(sum(ss["songs"][sid]["duration_s"] for sid in ids))
        tgt = seconds_to_mmss(ss["targets"][i]) if ss["targets"][i] else "–"
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 9, latin1_safe(f"Set {i+1}  ·  Ziel: {tgt}  ·  Aktuell: {cur}"), ln=1)
        # header
        pdf.set_font("Helvetica", "B", 15)
        pdf.cell(12, 10, "#", 1, 0, "C")
        pdf.cell(110, 10, latin1_safe("Titel"), 1, 0)
        pdf.cell(22, 10, latin1_safe("Dauer"), 1, 0, "C")
        pdf.cell(23, 10, latin1_safe("Tonart"), 1, 0, "C")
        pdf.cell(23, 10, latin1_safe("Tempo"), 1, 1, "C")
        # rows
        pdf.set_font("Helvetica", "", 15)
        for pos, sid in enumerate(ids, start=1):
            s = ss["songs"][sid]
            pdf.cell(12, 10, str(pos), 1, 0, "C")
            pdf.cell(110, 10, latin1_safe(s["title"]), 1, 0)
            pdf.cell(22, 10, seconds_to_mmss(s["duration_s"]), 1, 0, "C")
            pdf.cell(23, 10, latin1_safe(s.get("key","") or "-"), 1, 0, "C")
            pdf.cell(23, 10, latin1_safe(s.get("tempo","") or "-"), 1, 1, "C")
        pdf.set_font("Helvetica", "B", 15)
        pdf.cell(122, 10, latin1_safe("Total Set"), 1, 0, "R")
        pdf.cell(46, 10, cur, 1, 1, "C")
        pdf.ln(2)
    total_seconds = sum(ss["songs"][sid]["duration_s"] for i in range(num_sets) for sid in ss["sets"][i])
    total = seconds_to_mmss(total_seconds)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(122, 10, latin1_safe("Gesamtdauer"), 0, 0, "R")
    pdf.cell(46, 10, total, 0, 1, "C")
    return pdf_bytes(pdf)

def make_pdf_suisa(title: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, latin1_safe(f"SUISA-Liste {title}"), ln=1, align="L")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(120, 10, latin1_safe("Titel"), 1, 0)
    pdf.cell(70, 10, latin1_safe("Interpret"), 1, 1)
    pdf.set_font("Helvetica", "", 15)
    for i in range(num_sets):
        for sid in ss["sets"][i]:
            s = ss["songs"][sid]
            pdf.cell(120, 10, latin1_safe(s["title"]), 1, 0)
            pdf.cell(70, 10, latin1_safe(s.get("artist","")), 1, 1)
    return pdf_bytes(pdf)

def make_csv_all_sets() -> bytes:
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["Titel","Dauer","Tonart","Tempo","Interpret","Set"])
    for i in range(num_sets):
        for sid in ss["sets"][i]:
            s = ss["songs"][sid]
            w.writerow([
                s["title"],
                seconds_to_mmss(s["duration_s"]),
                s.get("key",""),
                s.get("tempo",""),
                s.get("artist",""),
                f"Set {i+1}"
            ])
    return buf.getvalue().encode("utf-8")

with ec1:
    ss["concert_name"] = st.text_input("Titel auf Export (optional)", value=ss.get("concert_name",""), key="concert_name")
with ec2:
    if HAS_PDF:
        try:
            st.download_button("⬇️ Konzert-PDF", data=make_pdf_concert(ss.get("concert_name","")),
                               file_name="setliste_konzert.pdf", mime="application/pdf", key="dl_concert")
        except Exception as e:
            st.error(f"PDF Fehler (Konzert): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
with ec3:
    if HAS_PDF:
        try:
            st.download_button("⬇️ SUISA-PDF", data=make_pdf_suisa(ss.get("concert_name","")),
                               file_name="setliste_suisa.pdf", mime="application/pdf", key="dl_suisa")
        except Exception as e:
            st.error(f"PDF Fehler (SUISA): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
with ec4:
    try:
        st.download_button("⬇️ CSV (alle Sets)", data=make_csv_all_sets(),
                           file_name="setliste.csv", mime="text/csv", key="dl_csv")
    except Exception as e:
        st.error(f"CSV Fehler: {e}")
