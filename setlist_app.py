
# Setlist App – Version 2.0.7
# Changes:
# - Remove leftover bar element
# - Return set-duration color logic (Green/Orange/Red as specified)
# - Inline toolbar alignment
# - CSV export restored
# - PDF export: each Set on a new page

import math
import streamlit as st

try:
    from fpdf import FPDF  # PDF Export
    HAS_PDF = True
except Exception:
    HAS_PDF = False

ss = st.session_state

# ========================
# Branding & Page Config
# ========================
st.set_page_config(page_title="BD Setlist 2.0.7", layout="wide")
st.title("BD Setlist 2.0.7")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap');

:root{
  --brand:#004D59;
  --muted:#6b7280;
  --radius:14px;
  --green:#E6F4EA;
  --greenText:#0E7C3A;
  --orange:#FFF4E5;
  --orangeText:#7A3E00;
  --red:#FDE8E8;
  --redText:#B42318;
}

html, body, [class*="block-container"] { font-size:15px; }
h1, h2, h3, h4, h5, h6, .stButton>button { font-family: 'Montserrat', sans-serif; font-weight: 700; }
*, .stTextInput>div>div>input, .stNumberInput>div>input { font-family: 'Space Mono', monospace; }

/* Buttons */
.stButton>button {
  background-color: var(--brand);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 14px;
}
.stButton>button:hover { background-color: #00738A; }

/* Cards */
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: var(--radius); padding: 12px 14px; margin-bottom: 14px; }

/* Chips */
.rowchip{padding:4px 8px;border-radius:8px;border:1px solid #e5e7eb;background:#f3f4f6;display:inline-block;min-width:58px;text-align:center;}

.title{font-weight:700;margin:0;padding:0;}
.sub{font-size:12px;color:#6b7280;margin-top:2px;}

.headerlabel{font-weight:700;color:#374151;font-size:14px;margin-bottom:6px;}

/* Inline toolbar */
.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:nowrap;margin:8px 0;}
.toolbar > div { display:flex; align-items:center; }
.toolbar .stSelectbox, .toolbar .stButton { margin-top: 0 !important; }

/* Remove any stray full-width bars (older Streamlit classes) */
hr, .stProgress { display:none !important; }
</style>
""", unsafe_allow_html=True)

# ========================
# Utilities
# ========================
def mmss_to_seconds(m, s):
    try:
        m = int(m or 0); s = int(s or 0)
    except Exception:
        m, s = 0, 0
    s = max(0, min(59, s)); m = max(0, m)
    return m * 60 + s

def parse_mmss(text):
    try:
        if not text: return 0
        parts = text.strip().split(":")
        if len(parts)==2:
            return mmss_to_seconds(parts[0], parts[1])
        if len(parts)==1:
            return int(parts[0])
    except:
        return 0
    return 0

def seconds_to_mmss(total):
    if total < 0: total = 0
    m, s = divmod(int(total), 60)
    return f"{m:02d}:{s:02d}"

def total_duration(ids):
    return sum(ss.songs[i]["duration_s"] for i in ids if i in ss.songs)

def badge_style_for_delta(cur_s, tgt_min):
    """Color logic:
       Grün = Ziel erreicht -1min bis +2min
       Orange = unter Ziel (< -1min)
       Rot = über Ziel ab +2min (>= +120s)
    """
    diff = cur_s - tgt_min*60
    if diff >= 120:  # >= +2min
        bg, fg = "var(--red)", "var(--redText)"
    elif diff < -60:  # more than 1min under
        bg, fg = "var(--orange)", "var(--orangeText)"
    else:  # within [-1min, +2min)
        bg, fg = "var(--green)", "var(--greenText)"
    return f"background:{bg};color:{fg};padding:6px 10px;border-radius:10px;font-weight:700;text-align:right;"

# ========================
# Session Defaults
# ========================
def init_state():
    if "songs" not in ss:
        ss.songs = {}
    if "next_id" not in ss:
        ss.next_id = 1
    if "sets" not in ss:
        ss.sets = [[], [], []]
    if "active_sets" not in ss:
        ss.active_sets = 3
    if "targets_min" not in ss:
        ss.targets_min = [0, 0, 0]
    if "concert_name" not in ss:
        ss.concert_name = ""

init_state()

# ========================
# Seed list
# ========================
SETLIST_1_0 = [
    ("Alors, don't start the blinding lights","Dua Lipa, Stromae, The Weeknd","05:26"),
    ("Avicii","", ""),
    ("Bella Ballerino","", ""),
    ("Carmabesque","", "06:00"),
    ("Clandestino","Manu Chao","03:16"),
    ("Dance Monkey","Tones and I","04:09"),
    ("Die with a smile","Bruno Mars, Lady Gaga","04:15"),
    ("Emergency Hip Hop","Diverse","04:50"),
    ("Feeling Good","", "04:16"),
    ("Fireflies","Owl City","03:24"),
    ("Hip Hop Mix 2","Diverse","06:12"),
    ("Hopes Stay As They Were","", "05:16"),
    ("Komet/Monsun","", "03:34"),
    ("Lean On","Major Lazer & DJ Snake","03:00"),
    ("Leave the door open","Bruno Mars","04:08"),
    ("Let's Get Bad","", "05:05"),
    ("No Roots","Alice Merton","03:36"),
    ("Oh Johnny","", ""),
    ("Raw","", "05:00"),
    ("Romano Hip Hop","Diverse","02:30"),
    ("The Code","", "03:12"),
    ("Toxic Industry","", "03:20"),
    ("Valerie","", ""),
    ("Vreneli vo Mahala","", "03:49"),
    ("Wasabi","", ""),
    ("Where is my husband?","", "03:15"),
]

def seed_setlist_from_list(rows):
    ss.songs.clear()
    ss.next_id = 1
    for title, artist, dur in rows:
        if not title: continue
        ss.songs[ss.next_id] = {
            "title": title.strip(),
            "duration_s": parse_mmss(dur),
            "artist": (artist or "").strip(),
            "tempo": "120",
            "key": "C",
        }
        ss.next_id += 1

if not ss.songs:
    seed_setlist_from_list(SETLIST_1_0)

# ========================
# ➕ Neuen Song anlegen
# ========================
with st.expander("➕ Neuen Song anlegen", expanded=False):
    c1, c2, c3, c4, c5, c6 = st.columns([3,1,1,3,1,1])
    title = c1.text_input("Titel")
    m = c2.number_input("Minuten", 0, 59, 0)
    s = c3.number_input("Sekunden", 0, 59, 0, step=5)
    artist = c4.text_input("Artist")
    tempo = c5.text_input("Tempo", value="120")
    key_sig = c6.text_input("Tonart", value="C")
    if st.button("Hinzufügen", key="add_song"):
        if title.strip():
            ss.songs[ss.next_id] = {
                "title": title.strip(),
                "duration_s": mmss_to_seconds(m, s),
                "artist": artist.strip(),
                "tempo": tempo.strip(),
                "key": key_sig.strip(),
            }
            ss.next_id += 1
            st.success("Song hinzugefügt.")
            st.rerun()

# ========================
# 🎵 Repertoire (ohne Pane/Balken)
# ========================
def pool_ids():
    used = set(i for s in ss.sets[:ss.active_sets] for i in s)
    return sorted([i for i in ss.songs if i not in used], key=lambda i: ss.songs[i]["title"].lower())

with st.expander("🎵 Repertoire", expanded=True):
    pool = pool_ids()
    left, right = st.columns(2)
    selected = []
    for idx, sid in enumerate(pool):
        song = ss.songs[sid]
        label = f"{song['title']} ({seconds_to_mmss(song['duration_s'])})"
        with (left if idx % 2 == 0 else right):
            if st.checkbox(label, key=f"pool_cb_{sid}"):
                selected.append(sid)
    dest = st.radio("Ziel Set", [1,2,3][:ss.active_sets], horizontal=True, format_func=lambda i: f"Set {i}")
    if st.button("Auswahl in Set übernehmen"):
        if selected:
            tgt = dest - 1
            for sid in selected:
                if sid not in ss.sets[tgt]:
                    ss.sets[tgt].append(sid)
        st.rerun()

# ========================
# 🔢 Anzahl Set
# ========================
with st.expander("🔢 Anzahl Set", expanded=False):
    new_count = st.radio("Anzahl", [1,2,3], index=ss.active_sets-1, horizontal=True, format_func=lambda i: f"Set {i}")
    if new_count != ss.active_sets:
        ss.active_sets = new_count
        st.rerun()

# ========================
# 🎼 Sets (untereinander) inkl. Multi-Action
# ========================
with st.expander("🎼 Sets", expanded=True):
    for i in range(ss.active_sets):
        ids = ss.sets[i]
        st.subheader(f"Set {i+1}")
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        tcol1, tcol2 = st.columns([3,1])
        tgt = tcol1.number_input(f"Ziel Minuten · Set {i+1}", 0, 300, ss.targets_min[i], key=f"tgt_{i}")
        ss.targets_min[i] = tgt
        cur_s = total_duration(ids)
        tcol2.markdown(
            f"<div style='{badge_style_for_delta(cur_s, tgt)}'>Aktuell {seconds_to_mmss(cur_s)} · Ziel {tgt:02d}:00</div>",
            unsafe_allow_html=True
        )

        # Header
        h1, h2, h3, h4, h5, h6 = st.columns([6,1,1,1,2,0.7])
        with h1: st.markdown("<div class='headerlabel'>Titel</div>", unsafe_allow_html=True)
        with h2: st.markdown("<div class='headerlabel'>Dauer</div>", unsafe_allow_html=True)
        with h3: st.markdown("<div class='headerlabel'>Tonart</div>", unsafe_allow_html=True)
        with h4: st.markdown("<div class='headerlabel'>Tempo</div>", unsafe_allow_html=True)
        with h5: st.markdown("<div class='headerlabel'>Aktion</div>", unsafe_allow_html=True)
        with h6: st.markdown("<div class='headerlabel'>Ausw.</div>", unsafe_allow_html=True)

        # Rows
        for pos, sid in enumerate(ids):
            s = ss.songs.get(sid, None)
            if not s: continue
            c1, c2, c3, c4, c5, c6 = st.columns([6,1,1,1,2,0.7])
            with c1:
                st.markdown(f"<div class='title'>{s['title']}</div><div class='sub'>{s.get('artist','')}</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<span class='rowchip'>{seconds_to_mmss(s['duration_s'])}</span>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<span class='rowchip'>{s.get('key','') or '–'}</span>", unsafe_allow_html=True)
            with c4:
                st.markdown(f"<span class='rowchip'>{s.get('tempo','') or '–'}</span>", unsafe_allow_html=True)
            with c5:
                b1, b2, b3 = st.columns([1,1,1])
                with b1:
                    if st.button("↑", key=f"up_{i}_{sid}") and pos > 0:
                        ids[pos-1], ids[pos] = ids[pos], ids[pos-1]
                        st.rerun()
                with b2:
                    if st.button("↓", key=f"down_{i}_{sid}") and pos < len(ids) - 1:
                        ids[pos+1], ids[pos] = ids[pos], ids[pos+1]
                        st.rerun()
                with b3:
                    if st.button("✕", key=f"rm_{i}_{sid}"):
                        ids.remove(sid)
                        st.rerun()
            with c6:
                st.checkbox("", key=f"sel_{i}_{sid}")

        # Multi-Action Toolbar (inline)
        st.markdown("<div class='toolbar'>", unsafe_allow_html=True)
        tb1, tb2, tb3 = st.columns([1.2, 1.4, 1])
        with tb1:
            target = st.selectbox("Zielset", [j+1 for j in range(ss.active_sets) if j != i], key=f"dest_{i}", format_func=lambda v: f"Set {v}")
        with tb2:
            if st.button("Ausgewählte → anderes Set", key=f"mv_{i}"):
                move_ids = [sid for sid in ids if ss.get(f"sel_{i}_{sid}", False)]
                if move_ids:
                    tgt_idx = (target - 1) if target else i
                    for sid in move_ids:
                        if sid in ids:
                            ids.remove(sid)
                            if sid not in ss.sets[tgt_idx]:
                                ss.sets[tgt_idx].append(sid)
                st.rerun()
        with tb3:
            if st.button("Ausgewählte → Pool", key=f"pool_{i}"):
                pool_back = [sid for sid in ids if ss.get(f"sel_{i}_{sid}", False)]
                for sid in pool_back:
                    if sid in ids:
                        ids.remove(sid)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ========================
# 📤 Export – PDFs & CSV
# ========================
with st.expander("📤 Export", expanded=False):
    concert_name = st.text_input("Titel auf Export", value=ss.get("concert_name",""), key="concert_name_input_2")
    ss["concert_name"] = concert_name

    # Helpers for rounded rectangles in FPDF2
    def rounded_rect(pdf, x, y, w, h, r=3, style=''):
        k = pdf.k
        hp = pdf.h
        myArc = 4/3 * (math.sqrt(2) - 1)
        pdf._out('q')
        pdf._out('%.2F %.2F m' % ((x+r)*k, (hp-y)*k))
        pdf._out('%.2F %.2F l' % ((x+w-r)*k, (hp-y)*k))
        pdf._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((x+w-r*myArc)*k, (hp-y)*k, (x+w)*k, (hp-y+r*myArc)*k, (x+w)*k, (hp-(y+r))*k))
        pdf._out('%.2F %.2F l' % ((x+w)*k, (hp-(y+h-r))*k))
        pdf._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((x+w)*k, (hp-(y+h-r*myArc))*k, (x+w-r*myArc)*k, (hp-(y+h))*k, (x+w-r)*k, (hp-(y+h))*k))
        pdf._out('%.2F %.2F l' % ((x+r)*k, (hp-(y+h))*k))
        pdf._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((x+r*myArc)*k, (hp-(y+h))*k, x*k, (hp-(y+h-r*myArc))*k, x*k, (hp-(y+h-r))*k))
        pdf._out('%.2F %.2F l' % (x*k, (hp-(y+r))*k))
        pdf._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % (x*k, (hp-(y+r*myArc))*k, (x+r*myArc)*k, (hp-y)*k, (x+r)*k, (hp-y)*k))
        if style == 'F':
            op='f'
        elif style in ('FD','DF'):
            op='B'
        else:
            op='S'
        pdf._out(op)
        pdf._out('Q')

    def mmss_local(total):
        m, s = divmod(int(total), 60)
        return f"{m:02d}:{s:02d}"

    def new_page_with_header(pdf, title_text):
        pdf.add_page()
        pdf.set_auto_page_break(True, 14)
        pdf.set_draw_color(0,77,89)
        pdf.set_fill_color(0,77,89)
        rounded_rect(pdf, 10, 10, 190, 14, r=5, style='F')
        pdf.set_text_color(255,255,255)
        pdf.set_font("Helvetica","B",14)
        pdf.set_xy(10, 12)
        pdf.cell(190,10, title_text, align="C")
        pdf.ln(12)

    def make_pdf_concert() -> bytes:
        if not HAS_PDF:
            raise RuntimeError("fpdf2 nicht installiert")
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        # Each set on its own page
        for si in range(ss.active_sets):
            new_page_with_header(pdf, "BD Setlist")
            # Title
            pdf.set_text_color(0,77,89)
            pdf.set_font("Helvetica","B",16)
            pdf.cell(0,10, (ss.get("concert_name") or "Setliste") + f" – Set {si+1}", ln=1)
            pdf.ln(1)

            # Table header
            pdf.set_font("Helvetica","B",11)
            pdf.set_draw_color(229,231,235)
            pdf.set_fill_color(241,245,249)
            pdf.set_text_color(17,24,39)
            pdf.cell(10,8,"#",1,0,"C",True)
            pdf.cell(100,8,"Titel",1,0,"L",True)
            pdf.cell(22,8,"Dauer",1,0,"C",True)
            pdf.cell(22,8,"Tonart",1,0,"C",True)
            pdf.cell(22,8,"Tempo",1,1,"C",True)

            # Rows
            pdf.set_font("Helvetica","",11)
            for idx, sid in enumerate(ss.sets[si], start=1):
                s = ss.songs.get(sid)
                if not s: continue
                pdf.cell(10,8,str(idx),1,0,"C")
                pdf.cell(100,8,s["title"],1,0,"L")
                pdf.cell(22,8,mmss_local(s["duration_s"]),1,0,"C")
                pdf.cell(22,8,s.get("key",""),1,0,"C")
                pdf.cell(22,8,s.get("tempo",""),1,1,"C")

            # Total row
            pdf.set_font("Helvetica","B",11)
            total = sum(ss.songs[i]["duration_s"] for i in ss.sets[si])
            pdf.cell(110,8,"Setdauer",1,0,"R")
            pdf.cell(22,8,mmss_local(total),1,0,"C")
            pdf.cell(22,8,"",1,0)
            pdf.cell(22,8,"",1,1)

        out = pdf.output(dest="S")
        if isinstance(out, bytearray): return bytes(out)
        if isinstance(out, str): return out.encode("latin-1","replace")
        return out

    def make_pdf_suisa() -> bytes:
        if not HAS_PDF:
            raise RuntimeError("fpdf2 nicht installiert")
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        for si in range(ss.active_sets):
            new_page_with_header(pdf, "BD SUISA-Liste")
            pdf.set_text_color(0,77,89)
            pdf.set_font("Helvetica","B",16)
            pdf.cell(0,10, (ss.get("concert_name") or "SUISA Liste") + f" – Set {si+1}", ln=1)
            pdf.ln(1)
            pdf.set_font("Helvetica","B",11)
            pdf.set_draw_color(229,231,235)
            pdf.set_fill_color(241,245,249)
            pdf.set_text_color(17,24,39)
            pdf.cell(120,8,"Titel",1,0,"L",True)
            pdf.cell(70,8,"Artist",1,1,"L",True)

            pdf.set_font("Helvetica","",11)
            for sid in ss.sets[si]:
                s = ss.songs.get(sid)
                if not s: continue
                pdf.cell(120,8,s["title"],1,0,"L")
                pdf.cell(70,8,s.get("artist",""),1,1,"L")

        out = pdf.output(dest="S")
        if isinstance(out, bytearray): return bytes(out)
        if isinstance(out, str): return out.encode("latin-1","replace")
        return out

    def make_csv() -> bytes:
        lines = ["Titel,Dauer,Tonart,Tempo,Artist,Set"]
        for si in range(ss.active_sets):
            for sid in ss.sets[si]:
                s = ss.songs.get(sid)
                if not s: continue
                title = s["title"].replace(","," ")
                dur = seconds_to_mmss(s["duration_s"])
                key = (s.get("key","") or "").replace(","," ")
                tempo = (s.get("tempo","") or "").replace(","," ")
                artist = (s.get("artist","") or "").replace(","," ")
                lines.append(f"{title},{dur},{key},{tempo},{artist},Set {si+1}")
        return ("\\n".join(lines)).encode("utf-8")

    c1, c2, c3 = st.columns(3)
    with c1:
        if HAS_PDF:
            try:
                st.download_button("Setliste als PDF", make_pdf_concert(), file_name="setliste_konzert.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"PDF Fehler Setliste: {e}")
        else:
            st.warning("PDF Export erfordert fpdf2 in requirements.")
    with c2:
        if HAS_PDF:
            try:
                st.download_button("SUISA als PDF", make_pdf_suisa(), file_name="setliste_suisa.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"PDF Fehler SUISA: {e}")
    with c3:
        st.download_button("CSV Export", make_csv(), file_name="setliste.csv", mime="text/csv")
