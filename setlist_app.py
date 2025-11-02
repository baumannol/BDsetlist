# setlist_app_v2_1_2_rowlock_fixed.py
# BD Setlist – Fixed one-line-per-song layout (no syntax errors, no dividers, responsive clean)

import math
import streamlit as st

try:
    from fpdf import FPDF
    HAS_PDF = True
except Exception:
    HAS_PDF = False

ss = st.session_state

# ============ PAGE & STYLES ============
st.set_page_config(page_title="BD Setlist 2.1.2 (rowlock fixed)", layout="wide")
st.title("BD Setlist 2.1.2 (rowlock fixed)")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Space+Mono&display=swap');
:root{ --brand:#004D59; --muted:#6b7280; }
h1,h2,h3,h4,h5,h6,.stButton>button{font-family:'Montserrat',sans-serif;font-weight:700}
*, .stTextInput>div>div>input, .stNumberInput>div>input { font-family:'Space Mono',monospace }

.stButton>button{background:var(--brand);color:#fff;border:none;border-radius:10px;padding:6px 8px;font-size:13px;min-width:36px}
.stButton>button:hover{background:#00738A}
.chip{padding:6px 8px;border-radius:10px;border:1px solid #e5e7eb;background:#f3f4f6;display:inline-block;text-align:center}
.title{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artist{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
hr,.stHorizontalBlock{display:none!important}
</style>
""", unsafe_allow_html=True)

# ============ UTILS ============
def mmss_to_seconds(m, s):
    try:
        m = int(m or 0); s = int(s or 0)
    except Exception:
        m, s = 0, 0
    return m*60 + s

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
    m, s = divmod(int(total or 0), 60)
    return f"{m:02d}:{s:02d}"

def total_duration(ids):
    return sum(ss.songs[i]["duration_s"] for i in ids if i in ss.songs)

def badge_style_for_delta(cur_s, tgt_min):
    diff = cur_s - tgt_min*60
    if diff >= 120:
        bg, fg = "#FDE8E8", "#B42318"
    elif diff < -60:
        bg, fg = "#FFF4E5", "#7A3E00"
    else:
        bg, fg = "#E6F4EA", "#0E7C3A"
    return f"background:{bg};color:{fg};padding:8px 12px;border-radius:12px;font-weight:700;text-align:right;"

# ============ STATE & SEED ============
def init_state():
    if "songs" not in ss: ss.songs = {}
    if "next_id" not in ss: ss.next_id = 1
    if "sets" not in ss: ss.sets = [[], [], []]
    if "active_sets" not in ss: ss.active_sets = 3
    if "targets_min" not in ss: ss.targets_min = [0,0,0]
    if "concert_name" not in ss: ss.concert_name = ""

init_state()

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

if not ss.songs:
    for title, artist, dur in SETLIST_1_0:
        if not title: continue
        ss.songs[ss.next_id] = {
            "title": title,
            "artist": artist,
            "duration_s": parse_mmss(dur),
            "key": "C",
            "tempo": "120"
        }
        ss.next_id += 1

# ============ ADD SONG ============
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

# ============ POOL ============
def pool_ids():
    used = {i for s in ss.sets[:ss.active_sets] for i in s}
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
    if st.button("Auswahl in Set übernehmen"):
        if selected:
            tgt = dest - 1
            for sid in selected:
                if sid not in ss.sets[tgt]:
                    ss.sets[tgt].append(sid)
        st.rerun()

# ============ RENDER SONG ROW ============
def render_row(i, pos, sid):
    s = ss.songs.get(sid)
    if not s:
        return
    col_title, col_dur, col_key, col_tmp, col_actions, col_sel = st.columns([8,1.2,1,1,2,0.6])
    with col_title:
        st.markdown(f"<div class='title' title='{s.get('artist','')}'>{s['title']}</div>", unsafe_allow_html=True)
    with col_dur:
        st.markdown(f"<span class='chip'>{seconds_to_mmss(s['duration_s'])}</span>", unsafe_allow_html=True)
    with col_key:
        st.markdown(f"<span class='chip'>{s.get('key','') or '–'}</span>", unsafe_allow_html=True)
    with col_tmp:
        st.markdown(f"<span class='chip'>{s.get('tempo','') or '–'}</span>", unsafe_allow_html=True)
    with col_actions:
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("↑", key=f"up_{i}_{sid}") and pos > 0:
                ss.sets[i][pos-1], ss.sets[i][pos] = ss.sets[i][pos], ss.sets[i][pos-1]
                st.rerun()
        with b2:
            if st.button("↓", key=f"down_{i}_{sid}") and pos < len(ss.sets[i]) - 1:
                ss.sets[i][pos+1], ss.sets[i][pos] = ss.sets[i][pos], ss.sets[i][pos+1]
                st.rerun()
        with b3:
            if st.button("✕", key=f"rm_{i}_{sid}"):
                ss.sets[i].remove(sid)
                st.rerun()
    with col_sel:
        st.checkbox("", key=f"sel_{i}_{sid}")

# ============ SETS ============
with st.expander("🎼 Sets", expanded=True):
    for i in range(ss.active_sets):
        ids = ss.sets[i]
        st.subheader(f"Set {i+1}")
        h1,h2,h3,h4,h5,h6 = st.columns([8,1.2,1,1,2,0.6])
        with h1: st.markdown("**Titel**")
        with h2: st.markdown("**Dauer**")
        with h3: st.markdown("**Tonart**")
        with h4: st.markdown("**Tempo**")
        with h5: st.markdown("**Aktion**")
        with h6: st.markdown("**Ausw.**")
        for pos, sid in enumerate(ids):
            render_row(i, pos, sid)

        cur_s = total_duration(ids)
        tgt = ss.targets_min[i]
        l, r = st.columns([3,1])
        with l:
            ss.targets_min[i] = st.number_input(f"Ziel Minuten · Set {i+1}", 0, 300, tgt, key=f"tgt_{i}")
        with r:
            st.markdown(f"<div style='{badge_style_for_delta(cur_s, ss.targets_min[i])}'>Aktuell {seconds_to_mmss(cur_s)} · Ziel {ss.targets_min[i]:02d}:00</div>", unsafe_allow_html=True)

# ============ EXPORT ============
with st.expander("📤 Export", expanded=False):
    concert_name = st.text_input("Titel auf Export", value=ss.get("concert_name",""), key="concert_name_input_2")
    ss["concert_name"] = concert_name

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

    st.download_button("CSV Export", make_csv(), file_name="setliste.csv", mime="text/csv")
