
import json
import io
import streamlit as st

# Optional Drag and Drop (used if available)
try:
    from streamlit_sortables import sort_items as sortable
    HAS_DND = True
except Exception:
    HAS_DND = False

st.set_page_config(page_title="Setlist Builder", layout="wide")
st.title("🎼 Setlist Builder")

# ===== styles =====
st.markdown("""
<style>
.stButton>button { background-color:#004D59; color:white; border:none; border-radius:8px; padding:8px 14px; }
.stButton>button:hover { background-color:#00738A; }
.section { background:#FDF1E7; padding:16px; border-radius:16px; margin-bottom:16px; }
.gray-drop { background:#F3F4F6; border:1px dashed #cbd5e1; padding:12px; border-radius:12px; }
.song-line{ display:flex; align-items:center; justify-content:space-between; gap:8px;
           padding:8px 10px; border:1px solid #e6e6e6; border-radius:10px; background:#fff; margin-bottom:6px; }
.song-title{ font-weight:700; color:#004D59; }
.song-meta{ font-size:12px; opacity:0.85; }
.small{ font-size:12px; opacity:0.8; }
</style>
""", unsafe_allow_html=True)

# ===== helpers =====
def mmss_to_seconds(txt_mm, txt_ss):
    try:
        m = int(txt_mm)
    except Exception:
        m = 0
    try:
        s = int(txt_ss)
    except Exception:
        s = 0
    m = max(0, m); s = max(0, s)
    return m*60 + s

def mmss_str_to_seconds(mmss: str):
    if not mmss:
        return 0
    parts = str(mmss).strip().split(":")
    if len(parts) == 2:
        return mmss_to_seconds(parts[0], parts[1])
    return 0

def seconds_to_mmss(total: int):
    if total < 0: total = 0
    m, s = divmod(int(total), 60)
    return f"{m:02d}:{s:02d}"

def ensure_state():
    if "songs" not in st.session_state:
        st.session_state["songs"] = {}   # id -> {title, artist, duration_s, key, note}
    if "next_song_id" not in st.session_state:
        st.session_state["next_song_id"] = 1
    if "sets" not in st.session_state:
        st.session_state["sets"] = [[]]  # list of lists of ids
    if "concert_name" not in st.session_state:
        st.session_state["concert_name"] = ""
    if "library_order" not in st.session_state:
        st.session_state["library_order"] = []
    if "initialized" not in st.session_state:
        st.session_state["initialized"] = False

def total_duration_seconds(ids):
    return sum(st.session_state["songs"][sid]["duration_s"] for sid in ids)

def export_concert_text(concert_name: str) -> str:
    out = [f"Setliste {concert_name}", "="*(9+len(concert_name)),""]
    for idx, set_ids in enumerate(st.session_state["sets"], start=1):
        out.append(f"Set {idx}")
        out.append("------")
        for pos, sid in enumerate(set_ids, start=1):
            s = st.session_state["songs"][sid]
            out.append(f"{pos:>2}. {s['title']} ({seconds_to_mmss(s['duration_s'])})")
        out.append(f"Set Dauer: {seconds_to_mmss(total_duration_seconds(set_ids))}\n")
    total_all = sum(total_duration_seconds(s) for s in st.session_state["sets"])
    out.append(f"Gesamtdauer: {seconds_to_mmss(total_all)}\n")
    return "\n".join(out)

def export_suisa_csv() -> str:
    out = ["Titel,Interpret,Tonart,Notiz"]
    for set_ids in st.session_state["sets"]:
        for sid in set_ids:
            s = st.session_state["songs"][sid]
            title = s["title"].replace(",", " ")
            artist = (s.get("artist") or "").replace(",", " ")
            key = (s.get("key") or "").replace(",", " ")
            note = (s.get("note") or "").replace(",", " ")
            out.append(f"{title},{artist},{key},{note}")
    return "\n".join(out)

ensure_state()

# ===== initial repertoire seed (can be edited later) =====
REPERTOIRE_SEED = [
    {"title":"Alors, dont start the blinding lights", "artist":"Dua Lipa, Stromae, The Weeknd", "mmss":"05:26"},
    {"title":"Avicii", "artist":"Avicii", "mmss":"04:10"},
    {"title":"Bella Ballerino", "artist":"Lucio Dalla", "mmss":""},
    {"title":"Carmabesque", "artist":"Coldplay, Stromae, Bizet", "mmss":"06:00"},
    {"title":"Clandestino", "artist":"Manu Chao", "mmss":"03:16"},
    {"title":"Dance Monkey", "artist":"Tones and I", "mmss":"04:09"},
    {"title":"Die with a smile", "artist":"Bruno Mars, Lady Gaga", "mmss":"04:15"},
    {"title":"Emergency Hip Hop", "artist":"Diverse", "mmss":"04:50"},
    {"title":"Feeling Good", "artist":"Anthony Newley, Leslie Bricusse", "mmss":"04:16"},
    {"title":"Fireflies", "artist":"Owl City", "mmss":"03:24"},
    {"title":"Hip Hop Mix 2", "artist":"Diverse", "mmss":"06:12"},
    {"title":"Hopes Stay As They Were", "artist":"Harry Styles, Panic at the Disco, Justin Bieber", "mmss":"05:16"},
    {"title":"Komet / Monsun", "artist":"Udo Lindenberg, Apache207, Tokio Hotel", "mmss":"03:34"},
    {"title":"Leave the door open", "artist":"Silk Sonic", "mmss":"04:08"},
    {"title":"Lets Get Bad", "artist":"J Lo, Billie Eilish", "mmss":"05:05"},
    {"title":"No Roots", "artist":"Alice Merton", "mmss":"03:36"},
    {"title":"Oh Johnny", "artist":"Jan Delay", "mmss":""},
    {"title":"Raw", "artist":"Meute", "mmss":"05:00"},
    {"title":"Romano Hip Hop", "artist":"Gipsy CZ", "mmss":"02:30"},
    {"title":"The Code", "artist":"Nemo", "mmss":"03:12"},
    {"title":"Toxic Industry", "artist":"Lil Nas, Britney Spears", "mmss":"03:20"},
    {"title":"Valerie", "artist":"Mark Ronson, Amy Winehouse", "mmss":""},
    {"title":"Vreneli vo Mahala", "artist":"Mahala Rai Banda, trad.", "mmss":"03:49"},
    {"title":"Wasabi", "artist":"Leningrad", "mmss":""},
]

if not st.session_state["initialized"]:
    # only seed once
    for seed in REPERTOIRE_SEED:
        sid = st.session_state["next_song_id"]; st.session_state["next_song_id"] += 1
        st.session_state["songs"][sid] = {
            "title": seed["title"],
            "artist": seed.get("artist",""),
            "duration_s": mmss_str_to_seconds(seed.get("mmss","")),
            "key": "",
            "note": "",
        }
        st.session_state["library_order"].append(sid)
    st.session_state["initialized"] = True

# ===== top: repertoire list =====
with st.expander("🎵 Repertoire", expanded=True):
    st.caption("Alle vorhandenen Songs. Oben fix angezeigt.")
    # show and allow ordering in repertoire
    ids = [i for i in st.session_state["library_order"] if i in st.session_state["songs"]]
    if HAS_DND:
        # present as simple labels with duration
        labels = [f"{st.session_state['songs'][i]['title']} — {seconds_to_mmss(st.session_state['songs'][i]['duration_s'])}" for i in ids]
        new_labels = sortable(labels, direction="vertical", key="repertoire_dnd")
        inv = {f"{st.session_state['songs'][i]['title']} — {seconds_to_mmss(st.session_state['songs'][i]['duration_s'])}": i for i in ids}
        st.session_state["library_order"] = [inv[l] for l in new_labels]
    # lines with quick add
    for i in st.session_state["library_order"]:
        s = st.session_state["songs"][i]
        c1,c2,c3,c4,c5 = st.columns([3,3,1,1,2])
        with c1: st.markdown(f"<div class='song-title'>{s['title']}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='song-meta'>{s.get('artist','')}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='song-meta'>{seconds_to_mmss(s['duration_s'])}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='song-meta'>{s.get('key','')}</div>", unsafe_allow_html=True)
        with c5:
            if st.session_state["sets"]:
                target = st.selectbox("zu Set", [f"Set {idx+1}" for idx in range(len(st.session_state["sets"]))], key=f"addsel_{i}")
                if st.button("hinzufuegen", key=f"btn_add_{i}"):
                    target_idx = int(target.split(" ")[1]) - 1
                    st.session_state["sets"][target_idx].append(i)
                    st.success(f"{s['title']} hinzugefuegt zu {target}")

# ===== add new song form =====
with st.expander("➕ Neuen Song anlegen", expanded=True):
    with st.form("new_song_form", clear_on_submit=True):
        a,b,c,d,e = st.columns([3,3,1,1,2])
        with a:
            title = st.text_input("Titel*", placeholder="z. B. Uptown Funk")
        with b:
            artist = st.text_input("Interpret optional", placeholder="z. B. Mark Ronson ft. Bruno Mars")
        with c:
            mm = st.number_input("Minuten", min_value=0, max_value=59, value=3, step=1)
        with d:
            ss = st.number_input("Sekunden", min_value=0, max_value=59, value=30, step=5)
        with e:
            key = st.text_input("Tonart optional", placeholder="z. B. Bb, Eb, Cm")
        note = st.text_input("Notiz optional", placeholder="Hinweise, Einsaetze, Tempo")
        submit = st.form_submit_button("Song speichern")
    if submit:
        if not title.strip():
            st.warning("Bitte einen Titel eingeben")
        else:
            sid = st.session_state["next_song_id"]; st.session_state["next_song_id"] += 1
            st.session_state["songs"][sid] = {
                "title": title.strip(),
                "artist": artist.strip(),
                "duration_s": mmss_to_seconds(mm, ss),
                "key": key.strip(),
                "note": note.strip(),
            }
            st.session_state["library_order"].append(sid)
            st.success(f"Song {title} gespeichert")

# ===== sets controls and gray drop zones =====
with st.expander("🧩 Sets und Reihenfolge", expanded=True):
    # select number of sets as selectbox (not slider)
    count = st.selectbox("Anzahl Sets", [1,2,3,4,5], index=len(st.session_state["sets"]) - 1)
    if count != len(st.session_state["sets"]):
        old = st.session_state["sets"]
        st.session_state["sets"] = old + [[] for _ in range(count-len(old))] if count>len(old) else old[:count]

    for set_idx in range(len(st.session_state["sets"])):
        set_ids = st.session_state["sets"][set_idx]
        st.markdown(f"**Set {set_idx+1}**  Dauer {seconds_to_mmss(total_duration_seconds(set_ids))}")
        st.markdown("<div class='gray-drop'>", unsafe_allow_html=True)

        if set_ids:
            # drag and drop ordering within the set
            if HAS_DND:
                labels = [f"{st.session_state['songs'][sid]['title']} — {seconds_to_mmss(st.session_state['songs'][sid]['duration_s'])}" for sid in set_ids]
                new_order = sortable(labels, direction="vertical", key=f"set_dnd_{set_idx}")
                inv = {f"{st.session_state['songs'][sid]['title']} — {seconds_to_mmss(st.session_state['songs'][sid]['duration_s'])}": sid for sid in set_ids}
                st.session_state["sets"][set_idx] = [inv[l] for l in new_order]
            # show rows with remove buttons
            for pos, sid in enumerate(st.session_state["sets"][set_idx]):
                s = st.session_state["songs"][sid]
                c1,c2,c3,c4 = st.columns([6,1,1,1])
                with c1: st.markdown(f"<div class='song-line'><span class='song-title'>{s['title']}</span> <span class='song-meta'>({seconds_to_mmss(s['duration_s'])}) · {s.get('artist','')} · {s.get('key','')}</span></div>", unsafe_allow_html=True)
                with c2:
                    if st.button("↑", key=f"up_{set_idx}_{sid}") and pos>0:
                        st.session_state["sets"][set_idx][pos-1], st.session_state["sets"][set_idx][pos] = st.session_state["sets"][set_idx][pos], st.session_state["sets"][set_idx][pos-1]
                        st.experimental_rerun()
                with c3:
                    if st.button("↓", key=f"down_{set_idx}_{sid}") and pos<len(st.session_state['sets'][set_idx])-1:
                        st.session_state["sets"][set_idx][pos+1], st.session_state["sets"][set_idx][pos] = st.session_state["sets"][set_idx][pos], st.session_state["sets"][set_idx][pos+1]
                        st.experimental_rerun()
                with c4:
                    if st.button("✖", key=f"del_{set_idx}_{sid}"):
                        st.session_state["sets"][set_idx].remove(sid)
                        st.experimental_rerun()
        else:
            st.caption("Noch keine Songs in diesem Set")

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

# ===== export =====
with st.expander("📋 Zusammenfassung und Export", expanded=True):
    total = 0
    for i, ids in enumerate(st.session_state["sets"], start=1):
        dur = total_duration_seconds(ids); total += dur
        st.markdown(f"**Set {i}** – {len(ids)} Songs · Dauer **{seconds_to_mmss(dur)}**")
    st.markdown(f"**Gesamt** {sum(len(s) for s in st.session_state['sets'])} Songs · **{seconds_to_mmss(total)}**")

    c1,c2 = st.columns(2)
    with c1:
        txt = export_concert_text(st.session_state["concert_name"] or "Setliste")
        st.download_button("⬇️ Setliste Konzert TXT", data=txt.encode("utf-8"), file_name="setliste_konzert.txt", mime="text/plain")
    with c2:
        csv = export_suisa_csv()
        st.download_button("⬇️ SUISA Liste CSV", data=csv.encode("utf-8"), file_name="suisa_liste.csv", mime="text/csv")
