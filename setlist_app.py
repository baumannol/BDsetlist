# setlist_app.py (patched)
import io
import csv
import streamlit as st

try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

st.set_page_config(page_title="Setlist", layout="wide")
st.title("🎼 Setlist")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root { --ink:#0f172a; --muted:#475569; --brand:#004D59; --brand2:#0d6b7a; --bg:#f8fafc; --row:#f1f5f9; }
html, body, [class*="css"]  { font-family:'Space Mono', monospace; font-size:16px; color:var(--ink); }
h1,h2,h3,.stButton>button { font-family:'Montserrat', sans-serif; font-weight:700; }

/* radio pills */
div[data-testid="stRadio"] > label { display:none; }
div[data-testid="stRadio"] div[role="radiogroup"] { display:flex; gap:16px; }
div[role="radio"] { background:#e2e8f0; border:1px solid #cbd5e1; padding:8px 16px; border-radius:9999px; }
div[role="radio"][aria-checked="true"] { background:var(--brand); color:#fff; border-color:var(--brand); }
div[role="radio"] p { margin:0; font-weight:700; }

/* set cards */
.set-card { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:12px 14px; margin-bottom:14px; }
.set-title { font-weight:700; }
.progress-outer { height:10px; border-radius:10px; background:#e5e7eb; overflow:hidden; }
.progress-inner { height:10px; width:0%; background:#16a34a; }
.set-meta { font-size:14px; color:var(--muted); min-width:160px; text-align:right; }
.rowhdr { font-weight:700; margin:6px 0 2px; }
.row { display:flex; align-items:center; gap:10px; padding:6px 8px; border-radius:8px; }
.row.alt { background:var(--row); }
.cell-title { flex:1; font-size:16px; }
.cell-badge { min-width:68px; text-align:center; background:#eef2f7; padding:2px 8px; border-radius:6px; font-weight:700; }
.cell-meta { width:86px; text-align:center; font-size:14px; color:var(--muted); }
</style>
''', unsafe_allow_html=True)

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
    return out

def seconds_to_mmss(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"

def total_duration(id_list):
    return sum(st.session_state["songs"][sid]["duration_s"] for sid in id_list)

ss = st.session_state
if "songs" not in ss:
    ss["songs"] = {
        1: {"title": "Alors, dont start the blinding lights", "duration_s": 326, "key": "", "tempo": "", "artist": "Dua Lipa, Stromae, The Weeknd"},
        2: {"title": "Avicii", "duration_s": 250, "key": "", "tempo": "", "artist": "Avicii"},
        3: {"title": "Carmabesque", "duration_s": 360, "key": "", "tempo": "", "artist": "Coldplay, Stromae, Bizet"},
    }
    ss["next_id"] = max(ss["songs"].keys()) + 1
    ss["pool"] = list(ss["songs"].keys())
    ss["sets"] = {0: [], 1: [], 2: []}
    ss["targets"] = [0, 0, 0]
    ss["sel"] = {}
    ss["num_sets"] = 3
    ss["concert_name"] = ""

with st.expander("➕ Neuen Song anlegen", expanded=False):
    c1,c2,c3,c4,c5,c6 = st.columns([3,1,1,2,1.2,1.2])
    n_title = c1.text_input("Titel")
    n_min = c2.number_input("Minuten", 0, 99, 3)
    n_sec = c3.number_input("Sekunden", 0, 59, 0)
    n_artist = c4.text_input("Interpret (optional)")
    n_tempo = c5.text_input("Tempo", value="")
    n_key = c6.text_input("Tonart", value="")
    if st.button("Hinzufügen"):
        if n_title:
            sid = ss["next_id"]; ss["next_id"] += 1
            ss["songs"][sid] = {
                "title": n_title.strip(),
                "duration_s": int(n_min)*60 + int(n_sec),
                "key": n_key.strip(),
                "tempo": n_tempo.strip(),
                "artist": n_artist.strip(),
            }
            ss["pool"].append(sid)
            st.success(f"Song „{n_title}“ hinzugefügt.")

st.subheader("Anzahl Sets")
choice = st.radio("", ["1 Set","2 Sets","3 Sets"], index=ss["num_sets"]-1, horizontal=True, label_visibility="collapsed")
ss["num_sets"] = ["1 Set","2 Sets","3 Sets"].index(choice)+1
num_sets = ss["num_sets"]

st.subheader("Repertoire")
rc1, rc2, rc3 = st.columns([4,2,1])
pool_sorted = sorted(ss["pool"], key=lambda sid: ss["songs"][sid]["title"].casefold())
def pool_label(sid: int) -> str:
    s = ss["songs"][sid]
    return f"{s['title']} ({seconds_to_mmss(s['duration_s'])})"
picks = rc1.multiselect("Songs auswählen", options=pool_sorted, format_func=pool_label, key="pick_from_pool")
dest = rc2.selectbox("Ziel Set", [f"Set {i+1}" for i in range(num_sets)], key="dest_set")
if rc3.button("Hinzufügen"):
    if picks:
        idx = int(dest.split()[-1])-1
        ss["sets"][idx].extend(picks)
        for sid in picks:
            if sid in ss["pool"]:
                ss["pool"].remove(sid)
        st.rerun()

st.subheader("Sets")
for i in range(num_sets):
    ids = ss["sets"][i]
    st.markdown("<div class='set-card'>", unsafe_allow_html=True)
    cur = total_duration(ids)
    tgt = ss["targets"][i]
    pct = 0 if tgt == 0 else min(1.0, cur/float(tgt))
    color = "#16a34a" if tgt==0 or cur<=tgt+60 else ("#f97316" if cur<=tgt+600 else "#dc2626")
    bar = int(pct*100)

    a,b,c = st.columns([2.5,4,2.5])
    a.markdown(f"<div class='set-title'>🎵 Set {i+1}</div>", unsafe_allow_html=True)
    mins = a.number_input(f"Ziel Minuten · Set {i+1}", 0, 180, int(tgt//60), key=f"tgt_{i}")
    ss["targets"][i] = mins*60
    b.markdown(f"<div class='progress-outer'><div class='progress-inner' style='width:{bar}%;background:{color};'></div></div>", unsafe_allow_html=True)
    c.markdown(f"<div class='set-meta'>Aktuell {seconds_to_mmss(cur)}<br/>Ziel {mins:02d}:00</div>", unsafe_allow_html=True)

    st.markdown("<div class='rowhdr'>Titel · Dauer · Tonart · Tempo</div>", unsafe_allow_html=True)
    if ids:
        for pos, sid in enumerate(ids):
            s = ss["songs"][sid]
            alt = " alt" if pos%2==1 else ""
            st.markdown(f"<div class='row{alt}'>", unsafe_allow_html=True)
            t,d,k,tp,act = st.columns([6,1.2,1.2,1.2,2])
            t.markdown(f"<div class='cell-title'>{latin1_safe(s['title'])}</div>", unsafe_allow_html=True)
            d.markdown(f"<div class='cell-badge'>{seconds_to_mmss(s['duration_s'])}</div>", unsafe_allow_html=True)
            k.markdown(f"<div class='cell-meta'>{latin1_safe(s.get('key','') or '-')}</div>", unsafe_allow_html=True)
            tp.markdown(f"<div class='cell-meta'>{latin1_safe(s.get('tempo','') or '-')}</div>", unsafe_allow_html=True)
            if act.button("Entfernen", key=f"rm_{i}_{sid}"):
                ids.remove(sid)
                if sid not in ss["pool"]:
                    ss["pool"].append(sid)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.caption("Noch keine Songs in diesem Set")
    st.markdown("</div>", unsafe_allow_html=True)

# Minimal exports to ensure file loads
st.subheader("Export")
if HAS_PDF:
    try:
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Helvetica","B",16); pdf.cell(0,10,"Test",ln=1)
        data = pdf.output(dest="S")
        if isinstance(data, bytearray):
            data = bytes(data)
        elif isinstance(data, str):
            data = data.encode("latin-1","replace")
        st.download_button("⬇️ Test PDF", data=data, file_name="test.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"PDF Fehler: {e}")
else:
    st.warning("PDF Export erfordert fpdf2 in requirements.")
