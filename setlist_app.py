# setlist_app_v2_1_0_responsive.py
# BD Setlist – Einheitliches RESPONSIVE Row-Layout (Desktop & Mobile)
# - Pro Song: ALLE Elemente in EINER Zeile (Titel, Dauer, Tonart, Tempo, Aktionen, Auswahl)
# - Keine speziellen Mobile-Toggles/Slider – reine CSS-Responsiveness mit Ellipsis & kompakten Chips
# - Export (PDF/CSV) wie gehabt

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
st.set_page_config(page_title="BD Setlist 2.1.0 (responsive)", layout="wide")
st.title("BD Setlist 2.1.0 (responsive)")

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

/* Buttons (global) */
.stButton>button {
  background-color: var(--brand);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 14px;
}
.stButton>button:hover { background-color: #00738A; }

/* Row Layout */
.songrow { 
  display: grid;
  grid-template-columns: 1fr 70px 70px 70px 150px 26px;
  align-items: center;
  gap: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 8px 10px;
  margin: 8px 0;
  background: #fff;
}
.songrow .title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 700;
}
.songrow .artist {
  font-size: 12px; color: var(--muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.chip{
  padding:6px 8px;border-radius:10px;border:1px solid #e5e7eb;background:#f3f4f6;display:inline-block;text-align:center;
}
.actions { display:flex; gap:6px; justify-content:flex-end; }
.actions .stButton>button { min-width: 40px; padding:6px 8px; }

/* Header */
.headergrid{
  display:grid; grid-template-columns: 1fr 70px 70px 70px 150px 26px; gap:8px; margin-top:4px; margin-bottom:6px;
}
.headergrid div{ font-weight:700; color:#374151; font-size:14px; }

/* Compact on narrow screens */
@media (max-width: 640px){
  html, body, [class*="block-container"] { font-size:15px; }
  .songrow{ grid-template-columns: 1fr 56px 56px 56px 120px 26px; padding:6px 8px; gap:6px; }
  .headergrid{ grid-template-columns: 1fr 56px 56px 56px 120px 26px; }
  .chip{ padding:4px 6px; font-size:12px; }
  .actions .stButton>button{ min-width:36px; padding:4px 6px; font-size:13px; }
  /* Artist inline mit Titel via title-attribute (Tooltip) */
  .songrow .artist{ display:none; }
}

/* Extra narrow (<=400px): noch enger, aber weiterhin eine Zeile */
@media (max-width: 400px){
  .songrow{ grid-template-columns: 1fr 50px 50px 50px 110px 26px; gap:4px; }
  .headergrid{ grid-template-columns: 1fr 50px 50px 50px 110px 26px; }
  .actions .stButton>button{ min-width:32px; padding:4px 5px; font-size:12px; }
}
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
    except Exception:
        return 0
    return 0

def seconds_to_mmss(total):
    if total < 0: total = 0
    m, s = divmod(int(total), 60)
    return f"{m:02d}:{s:02d}"

def total_duration(ids):
    return sum(ss.songs[i]["duration_s"] for i in ids if i in ss.songs)

def badge_style_for_delta(cur_s, tgt_min):
    diff = cur_s - tgt_min*60
    if diff >= 120:
        bg, fg = "var(--red)", "var(--redText)"
    elif diff < -60:
        bg, fg = "var(--orange)", "var(--orangeText)"
    else:
        bg, fg = "var(--green)", "var(--greenText)"
    return f"background:{bg};color:{fg};padding:8px 12px;border-radius:12px;font-weight:700;text-align:right;"

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
        if not title: 
            continue
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
    if st.button("Hinzufuegen", key="add_song"):
        if title.strip():
            ss.songs[ss.next_id] = {
                "title": title.strip(),
                "duration_s": mmss_to_seconds(m, s),
                "artist": artist.strip(),
                "tempo": tempo.strip(),
                "key": key_sig.strip(),
            }
            ss.next_id += 1
            st.success("Song hinzugefuegt.")
            st.rerun()

# ========================
# 🎵 Repertoire (Pool)
# ========================
def pool_ids():
    used = set(i for s in ss.sets[:ss.active_sets] for i in s)
    return sorted([i for i in ss.songs if i not in used], key=lambda i: ss.songs[i]["title"].lower())

with st.expander("🎵 Repertoire", expanded=True):
    pool = pool_ids()
    selected = []
    cols = st.columns(2)
    for idx, sid in enumerate(pool):
        song = ss.songs[sid]
        label = f"{song['title']} ({seconds_to_mmss(song['duration_s'])})"
        with cols[idx % 2]:
            if st.checkbox(label, key=f"pool_cb_{sid}"):
                selected.append(sid)
    dest = st.radio("Ziel Set", [1,2,3][:ss.active_sets], horizontal=True, format_func=lambda i: f"Set {i}")
    if st.button("Auswahl in Set uebernehmen"):
        if selected:
            tgt = dest - 1
            for sid in selected:
                if sid not in ss.sets[tgt]:
                    ss.sets[tgt].append(sid)
        st.rerun()

# ========================
# 🎼 Sets
# ========================
def render_song_row_responsive(i, pos, sid):
    s = ss.songs.get(sid)
    if not s:
        return
    title = s['title']
    artist = s.get('artist','')
    dur = seconds_to_mmss(s['duration_s'])
    key_sig = s.get('key','') or '–'
    tempo = s.get('tempo','') or '–'

    # ROW
    st.markdown("<div class='songrow'>", unsafe_allow_html=True)

    # Col 1: Titel + Artist (Artist als kleine Unterzeile, die auf sehr schmalen Screens ausgeblendet wird)
    with st.container():
        st.markdown(f"<div class='title' title='{artist}'>{title}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='artist'>{artist}</div>", unsafe_allow_html=True)

    # Col 2: Dauer
    st.markdown(f"<div class='chip'>{dur}</div>", unsafe_allow_html=True)

    # Col 3: Tonart
    st.markdown(f"<div class='chip'>{key_sig}</div>", unsafe_allow_html=True)

    # Col 4: Tempo
    st.markdown(f"<div class='chip'>{tempo}</div>", unsafe_allow_html=True)

    # Col 5: Aktionen
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("↑", key=f"up_{i}_{sid}") and pos > 0:
            ss.sets[i][pos-1], ss.sets[i][pos] = ss.sets[i][pos], ss.sets[i][pos-1]
            st.rerun()
    with c2:
        if st.button("↓", key=f"down_{i}_{sid}") and pos < len(ss.sets[i]) - 1:
            ss.sets[i][pos+1], ss.sets[i][pos] = ss.sets[i][pos], ss.sets[i][pos+1]
            st.rerun()
    with c3:
        if st.button("✕", key=f"rm_{i}_{sid}"):
            ss.sets[i].remove(sid)
            st.rerun()

    # Col 6: Auswahl
    st.checkbox("", key=f"sel_{i}_{sid}")
    st.markdown("</div>", unsafe_allow_html=True)

with st.expander("🎼 Sets", expanded=True):
    for i in range(ss.active_sets):
        ids = ss.sets[i]
        st.subheader(f"Set {i+1}")

        # Header
        st.markdown("<div class='headergrid'><div>Titel</div><div>Dauer</div><div>Tonart</div><div>Tempo</div><div>Aktion</div><div>Ausw.</div></div>", unsafe_allow_html=True)

        for pos, sid in enumerate(ids):
            render_song_row_responsive(i, pos, sid)

        # Multi-Action Toolbar
        st.markdown("<div style='display:flex;gap:12px;align-items:center;margin:8px 0;flex-wrap:wrap;'>", unsafe_allow_html=True)
        tb1, tb2, tb3 = st.columns([1.4, 1.6, 1])
        with tb1:
            target = st.selectbox("Zielset", [j+1 for j in range(ss.active_sets) if j != i], key=f"dest_{i}", format_func=lambda v: f"Set {v}")
        with tb2:
            if st.button("Ausgewaehlte → anderes Set", key=f"mv_{i}"):
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
            if st.button("Ausgewaehlte → Pool", key=f"pool_{i}"):
                pool_back = [sid for sid in ids if ss.get(f"sel_{i}_{sid}", False)]
                for sid in pool_back:
                    if sid in ids:
                        ids.remove(sid)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # Zielzeit / aktuelle Dauer (Badge rechts)
        cur_s = total_duration(ids)
        tgt = ss.targets_min[i] if i < len(ss.targets_min) else 0
        col_left, col_right = st.columns([3,1])
        with col_left:
            ss.targets_min[i] = st.number_input(f"Ziel Minuten · Set {i+1}", 0, 300, tgt, key=f"tgt_{i}")
        with col_right:
            st.markdown(f"<div style='{badge_style_for_delta(cur_s, ss.targets_min[i])}'>Aktuell {seconds_to_mmss(cur_s)} · Ziel {ss.targets_min[i]:02d}:00</div>", unsafe_allow_html=True)

# ========================
# 📤 Export – PDFs & CSV
# ========================
with st.expander("📤 Export", expanded=False):
    concert_name = st.text_input("Titel auf Export", value=ss.get("concert_name",""), key="concert_name_input_2")
    ss["concert_name"] = concert_name

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
        for si in range(ss.active_sets):
            new_page_with_header(pdf, "BD Setlist")
            pdf.set_text_color(0,77,89)
            pdf.set_font("Helvetica","B",16)
            pdf.cell(0,10, (ss.get("concert_name") or "Setliste") + f" – Set {si+1}", ln=1)
            pdf.ln(1)
            pdf.set_font("Helvetica","B",11)
            pdf.set_draw_color(229,231,235)
            pdf.set_fill_color(241,245,249)
            pdf.set_text_color(17,24,39)
            pdf.cell(10,8,"#",1,0,"C",True)
            pdf.cell(100,8,"Titel",1,0,"L",True)
            pdf.cell(22,8,"Dauer",1,0,"C",True)
            pdf.cell(22,8,"Tonart",1,0,"C",True)
            pdf.cell(22,8,"Tempo",1,1,"C",True)
            pdf.set_font("Helvetica","",11)
            for idx, sid in enumerate(ss.sets[si], start=1):
                s = ss.songs.get(sid)
                if not s:
                    continue
                pdf.cell(10,8,str(idx),1,0,"C")
                pdf.cell(100,8,s["title"],1,0,"L")
                pdf.cell(22,8,mmss_local(s["duration_s"]),1,0,"C")
                pdf.cell(22,8,s.get("key",""),1,0,"C")
                pdf.cell(22,8,s.get("tempo",""),1,1,"C")
            pdf.set_font("Helvetica","B",11)
            total = sum(ss.songs[i]["duration_s"] for i in ss.sets[si])
            pdf.cell(110,8,"Setdauer",1,0,"R")
            pdf.cell(22,8,mmss_local(total),1,0,"C")
            pdf.cell(22,8,"",1,0)
            pdf.cell(22,8,"",1,1)
        out = pdf.output(dest="S")
        if isinstance(out, bytearray): 
            return bytes(out)
        if isinstance(out, str): 
            return out.encode("latin-1","replace")
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
                if not s:
                    continue
                pdf.cell(120,8,s["title"],1,0,"L")
                pdf.cell(70,8,s.get("artist",""),1,1,"L")
        out = pdf.output(dest="S")
        if isinstance(out, bytearray): 
            return bytes(out)
        if isinstance(out, str): 
            return out.encode("latin-1","replace")
        return out

    def make_csv() -> bytes:
        lines = ["Titel,Dauer,Tonart,Tempo,Artist,Set"]
        for si in range(ss.active_sets):
            for sid in ss.sets[si]:
                s = ss.songs.get(sid)
                if not s:
                    continue
                title = s["title"].replace(","," ")
                dur = seconds_to_mmss(s["duration_s"])
                key = (s.get("key","") or "").replace(","," ")
                tempo = (s.get("tempo","") or "").replace(","," ")
                artist = (s.get("artist","") or "").replace(","," ")
                lines.append(f"{title},{dur},{key},{tempo},{artist},Set {si+1}")
        return ("\n".join(lines)).encode("utf-8")

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
