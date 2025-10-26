import io
import csv
import streamlit as st

# ====== PDF ======
try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

st.set_page_config(page_title="Setlist", layout="wide")
st.title("🎼 Setlist")

# ====== Styles (grössere Schrift, kompakt, gagenrechner-stil) ======
st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root { --ink:#0f172a; --muted:#475569; --brand:#004D59; --brand2:#0d6b7a; --chip:#eef2f7; }
html, body, [class*="css"]  { font-family:'Space Mono', monospace; font-size:16px; color:var(--ink); }
h1,h2,h3,.stButton>button { font-family:'Montserrat', sans-serif; font-weight:700; }
.stButton>button { background:var(--brand); color:#fff; border:none; border-radius:10px; padding:4px 10px; font-size:14px; }
.stButton>button:hover { background:var(--brand2); }
.small { font-size:14px; color:var(--muted); }
.badge { padding:2px 8px; border-radius:6px; background:var(--chip); font-weight:700; }
.rowhdr { font-weight:700; margin-top:6px; }
.setbar { position:sticky; top:0; z-index:20; background:#ffffffee; border-bottom:1px solid #e5e7eb; padding:6px 8px 10px; }
.btnwrap { display:flex; gap:8px; }
.btnpill { display:inline-block; padding:8px 14px; border-radius:9999px; border:1px solid #cbd5e1; background:#e2e8f0; color:#0f172a; font-weight:700; }
.btnpill.active { background:#004D59; border-color:#004D59; color:#fff; }
.hr { height:1px; background:#e5e7eb; margin:8px 0; }
</style>
''', unsafe_allow_html=True)

# ====== Helpers ======
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

# ====== State ======
ss = st.session_state
ss.setdefault("songs", {
    1: {"title": "Alors, dont start the blinding lights", "duration_s": 326, "key": "", "tempo": "", "artist": "Dua Lipa, Stromae, The Weeknd"},
    2: {"title": "Avicii", "duration_s": 250, "key": "", "tempo": "", "artist": "Avicii"},
    3: {"title": "Carmabesque", "duration_s": 360, "key": "", "tempo": "", "artist": "Coldplay, Stromae, Bizet"},
    4: {"title": "Hip Hop Mix 2", "duration_s": 372, "key": "", "tempo": "", "artist": "Diverse"},
    5: {"title": "Lets Get Bad", "duration_s": 305, "key": "", "tempo": "", "artist": "J. Lo / Billie Eilish"},
})
ss.setdefault("next_id", max(ss["songs"].keys()) + 1 if ss["songs"] else 1)
ss.setdefault("pool", list(ss["songs"].keys()))
ss.setdefault("sets", {0: [], 1: [], 2: []})
ss.setdefault("targets", [0, 0, 0])  # seconds
ss.setdefault("sel", {})
ss.setdefault("num_sets", 3)

# ====== Neuer Song ======
with st.expander("➕ Neuen Song anlegen", expanded=False):
    c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 2, 1.2, 1.2])
    with c1:
        n_title = st.text_input("Titel", key="new_title")
    with c2:
        n_min = st.number_input("Minuten", 0, 99, 4, key="new_min")
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

# ====== Anzahl Sets – Pseudo-farbige Buttons (ohne JS, Cloud-safe) ======
st.subheader("Anzahl Sets")
cbtn1, cbtn2, cbtn3 = st.columns(3)
def render_pill(col, label, n):
    active = (ss["num_sets"] == n)
    with col:
        # Wir rendern eine "Fake"-Schaltfläche als Link-Button mit Markdown, um Styles sicher zu halten
        if st.button(label, key=f"choose_{n}", type="secondary"):
            ss["num_sets"] = n
        st.markdown(f"<div class='btnwrap'><span class='btnpill {'active' if active else ''}'>{label}</span></div>", unsafe_allow_html=True)

render_pill(cbtn1, "1 Set", 1)
render_pill(cbtn2, "2 Sets", 2)
render_pill(cbtn3, "3 Sets", 3)

num_sets = ss["num_sets"]

# ====== Repertoire (alphabetisch) ======
st.subheader("Repertoire")
rc1, rc2, rc3 = st.columns([4, 2, 1])

# sortiert nach Titel A→Z
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

# ====== Sets ======
st.subheader("Sets")
set_names = [f"Set {i+1}" for i in range(num_sets)]

for i in range(num_sets):
    ids = ss["sets"][i]

    # Set Kopf: Name + Ziel-Minuten (direkte Übernahme) + Progress
    tc1, tc2, tc3 = st.columns([2, 3, 5])
    with tc1:
        st.markdown(f"**{set_names[i]}**")
    with tc2:
        mins = st.number_input(f"Ziel Minuten · {set_names[i]}", min_value=0, max_value=180, step=1,
                               value=int(ss['targets'][i] // 60), key=f"target_min_{i}")
        ss["targets"][i] = mins * 60  # direkte Übernahme
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
        st.markdown(f"<div style='height:10px;border-radius:10px;background:#e5e7eb;overflow:hidden;'><div style='width:{bar}%;height:10px;background:{color};'></div></div>", unsafe_allow_html=True)
        suffix = f" / Ziel {mins:02d}:00" if tgt else ""
        st.caption(f"Aktuell {seconds_to_mmss(cur)}{suffix}")

    st.markdown("<div class='rowhdr'>Titel · Dauer · Tonart · Tempo</div>", unsafe_allow_html=True)

    if ids:
        for pos, sid in enumerate(ids):
            s = ss["songs"][sid]
            col_t, col_d, col_k, col_tp, col_act, col_sel = st.columns([6, 1.2, 1.2, 1.2, 1.6, 0.8])
            with col_t:
                st.markdown(latin1_safe(s["title"]))
            with col_d:
                st.markdown(f"<span class='badge'>{seconds_to_mmss(s['duration_s'])}</span>", unsafe_allow_html=True)
            with col_k:
                st.markdown(f"<span class='small'>{latin1_safe(s.get('key','')) or '-'}</span>", unsafe_allow_html=True)
            with col_tp:
                st.markdown(f"<span class='small'>{latin1_safe(s.get('tempo','')) or '-'}</span>", unsafe_allow_html=True)
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

    # Batch-Aktionen inkl. Ziel-Set Auswahl
    ba1, ba_sel, ba2 = st.columns([0.25, 0.25, 0.5])
    dest_other_options = [j for j in range(num_sets) if j != i]
    dest_map = {f"Set {j+1}": j for j in dest_other_options} or {f"Set {i+1}": i}
    with ba_sel:
        dest_choice = st.selectbox(f"Ziel für Auswahl – {set_names[i]}", list(dest_map.keys()), key=f"batch_dest_{i}")
    with ba1:
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
    with ba2:
        if st.button("Ausgewählte → Pool", key=f"pool_batch_{i}"):
            selected = [sid for (si, sid), v in ss["sel"].items() if si == i and v]
            for sid in selected:
                if sid in ss["sets"][i]:
                    ss["sets"][i].remove(sid)
                    if sid not in ss["pool"]:
                        ss["pool"].append(sid)
                    ss["sel"][(i, sid)] = False
            st.rerun()

# ====== Export ======
st.subheader("Export")

def make_pdf_concert(title: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, latin1_safe(f"Setliste {title}"), ln=1, align="L")
    for i in range(num_sets):
        ids = ss["sets"][i]
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 9, latin1_safe(f"Set {i+1}"), ln=1)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(12, 8, "#", 1, 0, "C")
        pdf.cell(118, 8, latin1_safe("Titel"), 1, 0)
        pdf.cell(22, 8, latin1_safe("Dauer"), 1, 0, "C")
        pdf.cell(20, 8, latin1_safe("Tonart"), 1, 0, "C")
        pdf.cell(20, 8, latin1_safe("Tempo"), 1, 1, "C")
        pdf.set_font("Helvetica", "", 12)
        for pos, sid in enumerate(ids, start=1):
            s = ss["songs"][sid]
            pdf.cell(12, 8, str(pos), 1, 0, "C")
            pdf.cell(118, 8, latin1_safe(s["title"]), 1, 0)
            pdf.cell(22, 8, seconds_to_mmss(s["duration_s"]), 1, 0, "C")
            pdf.cell(20, 8, latin1_safe(s.get("key","") or "-"), 1, 0, "C")
            pdf.cell(20, 8, latin1_safe(s.get("tempo","") or "-"), 1, 1, "C")
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(150, 8, latin1_safe("Set Dauer"), 1, 0, "R")
        pdf.cell(42, 8, seconds_to_mmss(total_duration(ids)), 1, 1, "C")
        pdf.ln(2)
    total = sum(total_duration(ss["sets"][i]) for i in range(num_sets))
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(150, 10, latin1_safe("Gesamtdauer"), 0, 0, "R")
    pdf.cell(42, 10, seconds_to_mmss(total), 0, 1, "C")
    return pdf_bytes(pdf)

def make_pdf_suisa(title: str):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, latin1_safe(f"SUISA Liste {title}"), ln=1, align="L")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(120, 8, latin1_safe("Titel"), 1, 0)
    pdf.cell(72, 8, latin1_safe("Interpret"), 1, 1)
    pdf.set_font("Helvetica", "", 12)
    for i in range(num_sets):
        for sid in ss["sets"][i]:
            s = ss["songs"][sid]
            pdf.cell(120, 8, latin1_safe(s["title"]), 1, 0)
            pdf.cell(72, 8, latin1_safe(s.get("artist","")), 1, 1)
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
            data = make_pdf_concert("")
            st.download_button("⬇️ Konzert-PDF", data=data, file_name="setliste.pdf", mime="application/pdf", key="dl_concert")
        except Exception as e:
            st.error(f"PDF Fehler (Konzert): {e}")
    else:
        st.warning("PDF Export erfordert fpdf2 in requirements.")
with c2:
    if HAS_PDF:
        try:
            data2 = make_pdf_suisa("")
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