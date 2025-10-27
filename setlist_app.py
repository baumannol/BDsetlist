import io
import csv
import streamlit as st

# ========= PDF =========
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

st.set_page_config(page_title="Setlist", layout="wide")
st.title("🎼 Setlist")

# ========= Styles (Gagenrechner-Stil, kompakt & gut lesbar) =========
st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root { --ink:#0f172a; --muted:#475569; --brand:#004D59; --brand2:#0d6b7a; --bg:#f8fafc; --row:#f1f5f9; }
html, body, [class*="css"]  { font-family:'Space Mono', monospace; font-size:16px; color:var(--ink); }
h1,h2,h3,.stButton>button { font-family:'Montserrat', sans-serif; font-weight:700; }

/* Buttons */
.stButton>button { background:var(--brand); color:#fff; border:none; border-radius:10px; padding:6px 12px; font-size:15px; }
.stButton>button:hover { background:var(--brand2); }
.btn-ghost { display:inline-block; padding:6px 12px; border-radius:10px; border:1px solid #cbd5e1; background:#e2e8f0; color:#0f172a; font-weight:700; }
.btn-ghost.active { background:#004D59; border-color:#004D59; color:#fff; }

/* Set Cards */
.set-card { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:12px 14px; margin-bottom:14px; }
.set-header { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.set-title { font-weight:700; }
.set-progress { flex:1; }
.progress-outer { height:10px; border-radius:10px; background:#e5e7eb; overflow:hidden; }
.progress-inner { height:10px; width:0%; background:#16a34a; }
.set-meta { font-size:14px; color:var(--muted); min-width:160px; text-align:right; }

/* Table-like rows */
.rowhdr { font-weight:700; margin:6px 0 2px; }
.row { display:flex; align-items:center; gap:10px; padding:6px 8px; border-radius:8px; }
.row.alt { background:var(--row); }
.cell-title { flex:1; font-size:16px; }
.cell-badge { min-width:68px; text-align:center; background:#eef2f7; padding:2px 8px; border-radius:6px; font-weight:700; }
.cell-meta { width:86px; text-align:center; font-size:14px; color:var(--muted); }
.cell-actions { width:180px; display:flex; gap:6px; justify-content:flex-end; }
.cell-select { width:64px; text-align:right; }

/* Compact icon buttons */
.icon { display:inline-block; width:32px; height:32px; border-radius:10px; background:var(--brand); color:#fff; text-align:center; line-height:32px; font-weight:700; }
.icon:hover { background:var(--brand2); }
</style>
''', unsafe_allow_html=True)

# ========= Helpers =========
def latin1_safe(s: str) -> str:
    if s is None:
        return ""
    rep = {"–":"-","—":"-","’":"'", "“":'"',"”":'"',"…":"..."}
    for k,v in rep.items():
        s = s.replace(k, v)
    return s.encode("latin-1","replace").decode("latin-1")

def pdf_bytes(pdf):
    out = pdf.output(dest="S")
    if isinstance(out, bytearray):
        return bytes(out)
    if isinstance(out, str):
        return out.encode("latin-1","replace")
    return out  # bytes

def seconds_to_mmss(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"

def mmss_to_seconds(mm: int, ss: int) -> int:
    return max(0, int(mm))*60 + max(0, int(ss))

def total_duration(id_list):
    return sum(st.session_state["songs"][sid]["duration_s"] for sid in id_list)

# ========= State =========
ss = st.session_state
if "songs" not in ss:
    # Seed: dein Repertoire
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
    ss["pool"] = list(ss["songs"].keys())
    ss["sets"] = {0: [], 1: [], 2: []}
    ss["targets"] = [0, 0, 0]
    ss["sel"] = {}
    ss["num_sets"] = 3
    ss["concert_name"] = ""

# ========= Neuer Song =========
with st.expander("➕ Neuen Song anlegen", expanded=False):
    c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 2, 1.2, 1.2])
    with c1:
        n_title = st.text_input("Titel", key="new_title")
    with c2:
        n_min = st.number_input("Minuten", 0, 99, 3, key="new_min")
    with c3:
        n_sec = st.number_input("Sekunden", 0, 59, 0, key="new_sec")
    with c4:
        n_artist = st.text_input("Interpret (optional)", key="new_artist")
    with c5:
        n_tempo = st.text_input("Tempo", value="", key="new_tempo")
    with c6:
        n_key = st.text_input("Tonart", value="", key="new_key")
    if st.button("Hinzufügen", key="btn_add_song"):
        if n_title:
            sid = ss["next_id"]; ss["next_id"] += 1
            ss["songs"][sid] = {
                "title": n_title.strip(),
                "duration_s": mmss_to_seconds(n_min, n_sec),
                "key": n_key.strip(),
                "tempo": n_tempo.strip(),
                "artist": n_artist.strip(),
            }
            ss["pool"].append(sid)
            st.success(f"Song „{n_title}“ hinzugefügt.")

# ========= Anzahl Sets – Segmentierter Toggle =========
st.subheader("Anzahl Sets")
col_sets = st.columns(3)
def set_toggle(col, label, n):
    active = (ss["num_sets"] == n)
    with col:
        if st.button(label, key=f"choose_{n}", type="secondary"):
            ss["num_sets"] = n
        st.markdown(f"<span class='btn-ghost {'active' if active else ''}'>{label}</span>", unsafe_allow_html=True)
set_toggle(col_sets[0], "1 Set", 1)
set_toggle(col_sets[1], "2 Sets", 2)
set_toggle(col_sets[2], "3 Sets", 3)
num_sets = ss["num_sets"]

# ========= Repertoire =========
st.subheader("Repertoire")
rc1, rc2, rc3 = st.columns([4, 2, 1])
pool_sorted = sorted(ss["pool"], key=lambda sid: ss["songs"][sid]["title"].casefold())
def pool_label(sid: int) -> str:
    s = ss["songs"][sid]
    return f"{s['title']} ({seconds_to_mmss(s['duration_s'])})"
with rc1:
    picks = st.multiselect("Songs auswählen", options=pool_sorted, format_func=pool_label, key="pick_from_pool")
with rc2:
    dest = st.selectbox("Ziel Set", [f"Set {i+1}" for i in range(num_sets)], key="dest_set")
with rc3:
    if st.button("Hinzufügen", key="btn_add_to_set"):
        if picks:
            idx = int(dest.split()[-1]) - 1
            ss["sets"][idx].extend(picks)
            for sid in picks:
                if sid in ss["pool"]:
                    ss["pool"].remove(sid)
            st.rerun()

# ========= Sets (Cards + Tabelle + Toolbar) =========
st.subheader("Sets")
set_names = [f"Set {i+1}" for i in range(num_sets)]

for i in range(num_sets):
    ids = ss["sets"][i]

    # Card Start
    st.markdown("<div class='set-card'>", unsafe_allow_html=True)
    # Header
    cur = total_duration(ids)
    tgt = ss["targets"][i]
    delta = cur - tgt
    if tgt == 0:
        color = "#16a34a"
    elif delta > 600:
        color = "#dc2626"  # rot ab +10 min
    elif delta > 60:
        color = "#f97316"  # orange ab +1 min
    else:
        color = "#16a34a"
    pct = 0 if tgt == 0 else min(1.0, cur / float(tgt))
    bar = int(pct * 100)

    h1, h2, h3 = st.columns([2.5, 4, 2.5])
    with h1:
        st.markdown(f"<div class='set-header'><div class='set-title'>🎵 {set_names[i]}</div></div>", unsafe_allow_html=True)
        mins = st.number_input(f"Ziel Minuten · {set_names[i]}", min_value=0, max_value=180, step=1,
                               value=int(ss['targets'][i] // 60), key=f"target_min_{i}")
        ss["targets"][i] = mins * 60
    with h2:
        st.markdown(f"<div class='set-progress'><div class='progress-outer'><div class='progress-inner' style='width:{bar}%;background:{color};'></div></div></div>", unsafe_allow_html=True)
    with h3:
        suffix = f"Ziel {mins:02d}:00" if tgt else "Ziel –"
        st.markdown(f"<div class='set-meta'>Aktuell {seconds_to_mmss(cur)}<br/>{suffix}</div>", unsafe_allow_html=True)

    st.markdown("<div class='rowhdr'>Titel · Dauer · Tonart · Tempo</div>", unsafe_allow_html=True)

    # Rows
    if ids:
        for pos, sid in enumerate(ids):
            s = ss["songs"][sid]
            alt = " alt" if pos % 2 == 1 else ""
            st.markdown(f"<div class='row{alt}'>", unsafe_allow_html=True)
            c_t, c_d, c_k, c_tp, c_act, c_sel = st.columns([6, 1.2, 1.2, 1.2, 1.8, 0.8])
            with c_t:
                st.markdown(f"<div class='cell-title'>{latin1_safe(s['title'])}</div>", unsafe_allow_html=True)
            with c_d:
                st.markdown(f"<div class='cell-badge'>{seconds_to_mmss(s['duration_s'])}</div>", unsafe_allow_html=True)
            with c_k:
                st.markdown(f"<div class='cell-meta'>{latin1_safe(s.get('key','')) or '-'}</div>", unsafe_allow_html=True)
            with c_tp:
                st.markdown(f"<div class='cell-meta'>{latin1_safe(s.get('tempo','')) or '-'}</div>", unsafe_allow_html=True)
            with c_act:
                c_up, c_down, c_rm = st.columns([1, 1, 2])
                if c_up.button("↑", key=f"up_{i}_{sid}"):
                    if pos > 0:
                        ids[pos-1], ids[pos] = ids[pos], ids[pos-1]
                        st.rerun()
                if c_down.button("↓", key=f"down_{i}_{sid}"):
                    if pos < len(ids)-1:
                        ids[pos+1], ids[pos] = ids[pos], ids[pos+1]
                        st.rerun()
                if c_rm.button("Entfernen", key=f"rm_{i}_{sid}"):
                    ids.remove(sid)
                    if sid not in ss["pool"]:
                        ss["pool"].append(sid)
                    st.rerun()
            with c_sel:
                sel_key = (i, sid)
                checked = st.checkbox("Ausw.", key=f"sel_{i}_{sid}", value=ss["sel"].get(sel_key, False))
                ss["sel"][sel_key] = checked
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.caption("Noch keine Songs in diesem Set")

    # Toolbar unten in Card
    dest_other = [j for j in range(num_sets) if j != i]
    dest_map = {f"Set {j+1}": j for j in dest_other} or {f"Set {i+1}": i}
    tl, tm, tr = st.columns([2.2, 2.2, 5.6])
    with tm:
        dest_choice = st.selectbox(f"Ziel für Auswahl – {set_names[i]}", list(dest_map.keys()), key=f"batch_dest_{i}")
    with tl:
        if st.button("Ausgewählte → anderes Set", key=f"mv_batch_{i}"):
            selected = [sid for (si, sid), v in ss["sel"].items() if si == i and v]
            j = dest_map[dest_choice]
            if j is not None and selected:
                for sid in selected:
                    if sid in ss["sets"][i]:
                        ss["sets"][i].remove(sid)
                        ss["sets"][j].append(sid)
                        ss["sel"][(i, sid)] = False
                st.rerun()
    with tr:
        if st.button("Ausgewählte → Pool", key=f"pool_batch_{i}"):
            selected = [sid for (si, sid), v in ss["sel"].items() if si == i and v]
            for sid in selected:
                if sid in ss["sets"][i]:
                    ss["sets"][i].remove(sid)
                    if sid not in ss["pool"]:
                        ss["pool"].append(sid)
                    ss["sel"][(i, sid)] = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # Card End

# ========= Export =========
st.subheader("Export")

def make_pdf_concert(title: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Header (ohne Datum, wie gewünscht)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 12, latin1_safe(f"Konzert-Setlist {title}"), ln=1, align="L")
    pdf.ln(2)

    for i in range(num_sets):
        ids = ss["sets"][i]
        # Set Titel + Kopf
        cur = seconds_to_mmss(total_duration(ids))
        tgt = seconds_to_mmss(ss["targets"][i]) if ss["targets"][i] else "–"
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 9, latin1_safe(f"Set {i+1}  ·  Ziel: {tgt}  ·  Aktuell: {cur}"), ln=1)

        # Tabellenkopf
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(12, 9, "#", 1, 0, "C")
        pdf.cell(110, 9, latin1_safe("Titel"), 1, 0)
        pdf.cell(22, 9, latin1_safe("Dauer"), 1, 0, "C")
        pdf.cell(23, 9, latin1_safe("Tonart"), 1, 0, "C")
        pdf.cell(23, 9, latin1_safe("Tempo"), 1, 1, "C")

        # Inhalt
        pdf.set_font("Helvetica", "", 14)
        for pos, sid in enumerate(ids, start=1):
            s = ss["songs"][sid]
            pdf.cell(12, 9, str(pos), 1, 0, "C")
            pdf.cell(110, 9, latin1_safe(s["title"]), 1, 0)
            pdf.cell(22, 9, seconds_to_mmss(s["duration_s"]), 1, 0, "C")
            pdf.cell(23, 9, latin1_safe(s.get("key","") or "-"), 1, 0, "C")
            pdf.cell(23, 9, latin1_safe(s.get("tempo","") or "-"), 1, 1, "C")

        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(122, 9, latin1_safe("Total Set"), 1, 0, "R")
        pdf.cell(46, 9, cur, 1, 1, "C")
        pdf.ln(2)

    # Gesamt
    total = seconds_to_mmss(sum(total_duration(ss["sets"][i]) for i in range(num_sets)))
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

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(120, 9, latin1_safe("Titel"), 1, 0)
    pdf.cell(70, 9, latin1_safe("Interpret"), 1, 1)

    pdf.set_font("Helvetica", "", 14)
    for i in range(num_sets):
        for sid in ss["sets"][i]:
            s = ss["songs"][sid]
            pdf.cell(120, 9, latin1_safe(s["title"]), 1, 0)
            pdf.cell(70, 9, latin1_safe(s.get("artist","")), 1, 1)

    return pdf_bytes(pdf)

def make_csv_all_sets() -> bytes:
    # Titel, Dauer, Tonart, Tempo, Interpret, Set
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Titel", "Dauer", "Tonart", "Tempo", "Interpret", "Set"])
    for i in range(num_sets):
        for sid in ss["sets"][i]:
            s = ss["songs"][sid]
            writer.writerow([
                s["title"],
                seconds_to_mmss(s["duration_s"]),
                s.get("key",""),
                s.get("tempo",""),
                s.get("artist",""),
                f"Set {i+1}"
            ])
    return buf.getvalue().encode("utf-8")

c1, c2, c3 = st.columns(3)
with c1:
    if HAS_PDF:
        try:
            data = make_pdf_concert(ss.get("concert_name",""))
            st.download_button("⬇️ Konzert-PDF", data=data, file_name="setliste.pdf", mime="application/pdf", key="dl_concert")
        except Exception as e:
            st.error(f"PDF Fehler (Konzert): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
with c2:
    if HAS_PDF:
        try:
            data2 = make_pdf_suisa(ss.get("concert_name",""))
            st.download_button("⬇️ SUISA-PDF", data=data2, file_name="suisa.pdf", mime="application/pdf", key="dl_suisa")
        except Exception as e:
            st.error(f"PDF Fehler (SUISA): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
with c3:
    try:
        csv_bytes = make_csv_all_sets()
        st.download_button("⬇️ CSV (alle Sets)", data=csv_bytes, file_name="setliste.csv", mime="text/csv", key="dl_csv")
    except Exception as e:
        st.error(f"CSV Fehler: {e}")