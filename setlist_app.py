
import streamlit as st

# ====== PDF ======
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

st.set_page_config(page_title="Setlist", layout="wide")
st.title("🎼 Setlist")

# ====== Styles (kompakt) ======
st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root { --ink:#0f172a; --muted:#475569; --brand:#004D59; }
html, body, [class*="css"]  { font-family:'Space Mono', monospace; font-size:15px; }
h1,h2,h3,.stButton>button { font-family:'Montserrat', sans-serif; font-weight:700; }
.stButton>button { background:var(--brand); color:#fff; border:none; border-radius:8px; padding:2px 8px; font-size:12px; }
.stButton>button:hover { background:#0d6b7a; }
.small { font-size:12px; color:var(--muted); }
.rowhdr { font-weight:700; margin-top:4px; }
.setbar { position:sticky; top:0; z-index:20; background:#ffffffd9; border-bottom:1px solid #e5e7eb; padding:4px 6px 8px; }
.badge { padding:2px 6px; border-radius:6px; background:#eef2f7; }
</style>
''', unsafe_allow_html=True)

# ====== Helpers ======
def latin1_safe(s: str) -> str:
    if not s:
        return ""
    rep = {"–": "-", "—": "-", "’": "'", "“": '"', "”": '"', "…": "..."}
    for k, v in rep.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")

def pdf_bytes(pdf):
    out = pdf.output(dest="S")
    if isinstance(out, bytearray):
        return bytes(out)
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    return out  # bytes

def seconds_to_mmss(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"

def mmss_to_seconds(mm: int, ss: int) -> int:
    return max(0, int(mm))*60 + max(0, int(ss))

def total_duration(id_list):
    return sum(st.session_state["songs"][sid]["duration_s"] for sid in id_list)

# ====== State ======
ss = st.session_state
ss.setdefault("songs", {
    1: {"title": "Alors, dont start the blinding lights", "duration_s": 326, "key": "C-Dur", "tempo": "120", "artist": "Dua Lipa, Stromae, The Weeknd"},
    2: {"title": "Avicii", "duration_s": 250, "key": "C-Dur", "tempo": "120", "artist": "Avicii"},
    3: {"title": "Carmabesque", "duration_s": 360, "key": "C-Dur", "tempo": "120", "artist": "Coldplay, Stromae, Bizet"},
    4: {"title": "Hip Hop Mix 2", "duration_s": 372, "key": "C-Dur", "tempo": "120", "artist": "Diverse"},
    5: {"title": "Lets Get Bad", "duration_s": 305, "key": "C-Dur", "tempo": "120", "artist": "J. Lo / Billie Eilish"},
})
ss.setdefault("next_id", max(ss["songs"].keys()) + 1 if ss["songs"] else 1)
ss.setdefault("pool", list(ss["songs"].keys()))
ss.setdefault("sets", {0: [], 1: [], 2: []})
ss.setdefault("targets", [0, 0, 0])  # seconds
ss.setdefault("sel", {})

# ====== Neuer Song ======
with st.expander("➕ Neuen Song anlegen", expanded=False):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 2])
    with c1:
        n_title = st.text_input("Titel", key="new_title")
    with c2:
        n_min = st.number_input("Minuten", 0, 99, 4, key="new_min")
    with c3:
        n_sec = st.number_input("Sekunden", 0, 59, 0, key="new_sec")
    with c4:
        n_artist = st.text_input("Interpret (optional)", key="new_artist")
    if st.button("Hinzufügen", key="btn_add_song"):
        if n_title:
            sid = ss["next_id"]; ss["next_id"] += 1
            ss["songs"][sid] = {
                "title": n_title.strip(),
                "duration_s": mmss_to_seconds(n_min, n_sec),
                "key": "C-Dur",
                "tempo": "120",
                "artist": n_artist.strip(),
            }
            ss["pool"].append(sid)
            st.success(f"Song „{n_title}“ hinzugefügt.")

# ====== Anzahl Sets ======
st.header("Anzahl Sets")
num_sets = st.radio("Wähle Anzahl Sets", [1, 2, 3], index=2, horizontal=True, key="num_sets")
# wenn reduziert wird, bleiben Songs im vorhandenen Bereich, die restlichen Sets werden ignoriert

# ====== Repertoire (sticky) ======
st.header("Repertoire")
rc1, rc2, rc3 = st.columns([4, 2, 1])
pool_ids = list(ss["pool"])
def pool_label(sid: int) -> str:
    s = ss["songs"][sid]
    return f"{s['title']} ({seconds_to_mmss(s['duration_s'])})"
with rc1:
    picks = st.multiselect("Songs auswählen", options=pool_ids, format_func=pool_label, key="pick_from_pool")
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

# ====== Sets ======
st.header("Sets")
set_names = [f"Set {i+1}" for i in range(num_sets)]

for i in range(num_sets):
    ids = ss["sets"][i]

    # Ziel-Minuten + Fortschritt
    tc1, tc2, tc3 = st.columns([2, 3, 5])
    with tc1:
        st.markdown(f"**{set_names[i]}**")
    with tc2:
        mins = st.number_input(f"Ziel Minuten · Set {i+1}", min_value=0, max_value=180, step=1,
                               value=int(ss['targets'][i] // 60), key=f"target_min_{i}")
        mins = st.slider(" ", 0, 180, mins, 1, key=f"target_slider_{i}")
        ss["targets"][i] = mins * 60
    with tc3:
        cur = total_duration(ids)
        tgt = ss["targets"][i]
        delta = cur - tgt
        if tgt == 0:
            color = "#16a34a"
        elif delta > 600:
            color = "#dc2626"  # rot ab +10
        elif delta > 60:
            color = "#f97316"  # orange ab +1
        else:
            color = "#16a34a"
        pct = 0 if tgt == 0 else min(1.0, cur / float(tgt))
        bar = int(pct * 100)
        st.markdown(f"<div style='height:8px;border-radius:8px;background:#e5e7eb;overflow:hidden;'><div style='width:{bar}%;height:8px;background:{color};'></div></div>", unsafe_allow_html=True)
        suffix = f" / Ziel {mins:02d}:00" if tgt else ""
        st.caption(f"Aktuell {seconds_to_mmss(cur)}{suffix}")

    # Kopfzeile
    st.markdown("<div class='rowhdr'>Titel · Dauer · Tonart · Tempo</div>", unsafe_allow_html=True)

    if ids:
        for pos, sid in enumerate(ids):
            s = ss["songs"][sid]
            col_t, col_d, col_k, col_tp, col_act, col_sel = st.columns([6, 1.1, 1.1, 1.1, 1.6, 0.9])
            with col_t:
                st.markdown(latin1_safe(s["title"]))
            with col_d:
                st.markdown(f"<span class='badge'><b>{seconds_to_mmss(s['duration_s'])}</b></span>", unsafe_allow_html=True)
            with col_k:
                st.markdown(f"<span class='small'>{latin1_safe(s['key'])}</span>", unsafe_allow_html=True)
            with col_tp:
                st.markdown(f"<span class='small'>{latin1_safe(s['tempo'])}</span>", unsafe_allow_html=True)
            with col_act:
                b1, b2, b3 = st.columns([1, 1, 2])
                if b1.button("↑", key=f"up_{i}_{sid}"):
                    if pos > 0:
                        ids[pos-1], ids[pos] = ids[pos], ids[pos-1]
                        st.rerun()
                if b2.button("↓", key=f"down_{i}_{sid}"):
                    if pos < len(ids)-1:
                        ids[pos+1], ids[pos] = ids[pos], ids[pos+1]
                        st.rerun()
                if b3.button("Entfernen", key=f"rm_{i}_{sid}"):
                    ids.remove(sid)
                    if sid not in ss["pool"]:
                        ss["pool"].append(sid)
                    st.rerun()
            with col_sel:
                sel_key = (i, sid)
                checked = st.checkbox("Ausw.", key=f"sel_{i}_{sid}", value=ss["sel"].get(sel_key, False))
                ss["sel"][sel_key] = checked
    else:
        st.caption("Noch keine Songs in diesem Set")

    # Batch-Aktionen
    ba1, ba2, _ = st.columns([0.2, 0.2, 0.6])
    if ba1.button("Ausgewählte → anderes Set", key=f"mv_batch_{i}"):
        selected = [sid for (si, sid), v in ss["sel"].items() if si == i and v]
        dest_idx = 0 if i != 0 else (1 if num_sets > 1 else None)
        if dest_idx is not None:
            for sid in selected:
                if sid in ss["sets"][i]:
                    ss["sets"][i].remove(sid)
                    ss["sets"][dest_idx].append(sid)
                    ss["sel"][(i, sid)] = False
            st.rerun()
    if ba2.button("Ausgewählte → Pool", key=f"pool_batch_{i}"):
        selected = [sid for (si, sid), v in ss["sel"].items() if si == i and v]
        for sid in selected:
            if sid in ss["sets"][i]:
                ss["sets"][i].remove(sid)
                if sid not in ss["pool"]:
                    ss["pool"].append(sid)
                ss["sel"][(i, sid)] = False
        st.rerun()

# ====== Export ======
st.header("Export")

def make_pdf_concert(title: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, latin1_safe(f"Setliste {title}"), ln=1)
    for i in range(num_sets):
        ids = ss["sets"][i]
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, latin1_safe(f"Set {i+1}"), ln=1)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(10, 7, "#", 1, 0, "C")
        pdf.cell(115, 7, latin1_safe("Titel"), 1, 0)
        pdf.cell(20, 7, latin1_safe("Dauer"), 1, 0, "C")
        pdf.cell(20, 7, latin1_safe("Tonart"), 1, 0, "C")
        pdf.cell(20, 7, latin1_safe("Tempo"), 1, 1, "C")
        pdf.set_font("Helvetica", "", 11)
        for pos, sid in enumerate(ids, start=1):
            s = ss["songs"][sid]
            pdf.cell(10, 7, str(pos), 1, 0, "C")
            pdf.cell(115, 7, latin1_safe(s["title"]), 1, 0)
            pdf.cell(20, 7, seconds_to_mmss(s["duration_s"]), 1, 0, "C")
            pdf.cell(20, 7, latin1_safe(s["key"]), 1, 0, "C")
            pdf.cell(20, 7, latin1_safe(s["tempo"]), 1, 1, "C")
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(145, 7, latin1_safe("Set Dauer"), 1, 0, "R")
        pdf.cell(40, 7, seconds_to_mmss(total_duration(ids)), 1, 1, "C")
        pdf.ln(2)
    total = sum(total_duration(ss["sets"][i]) for i in range(num_sets))
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(145, 8, latin1_safe("Gesamtdauer"), 0, 0, "R")
    pdf.cell(40, 8, seconds_to_mmss(total), 0, 1, "C")
    return pdf_bytes(pdf)

def make_pdf_suisa(title: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, latin1_safe(f"SUISA Liste {title}"), ln=1)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(115, 7, latin1_safe("Titel"), 1, 0)
    pdf.cell(75, 7, latin1_safe("Interpret"), 1, 1)
    pdf.set_font("Helvetica", "", 11)
    for i in range(num_sets):
        for sid in ss["sets"][i]:
            s = ss["songs"][sid]
            pdf.cell(115, 7, latin1_safe(s["title"]), 1, 0)
            pdf.cell(75, 7, latin1_safe(s.get("artist", "")), 1, 1)
    return pdf_bytes(pdf)

c1, c2 = st.columns(2)
with c1:
    if HAS_PDF:
        try:
            data = make_pdf_concert("Setlist")
            st.download_button("⬇️ Konzert-PDF", data=data, file_name="setliste.pdf", mime="application/pdf", key="dl_concert")
        except Exception as e:
            st.error(f"PDF Fehler (Konzert): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
with c2:
    if HAS_PDF:
        try:
            data2 = make_pdf_suisa("Setlist")
            st.download_button("⬇️ SUISA-PDF", data=data2, file_name="suisa.pdf", mime="application/pdf", key="dl_suisa")
        except Exception as e:
            st.error(f"PDF Fehler (SUISA): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
