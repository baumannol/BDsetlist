
import streamlit as st

st.set_page_config(page_title="🎶 Setlist Builder", layout="wide")
st.title("🎶 Setlist Builder")

# Step 1: Song Pool
st.header("1. Song-Auswahl")
if "song_pool" not in st.session_state:
    st.session_state.song_pool = []

new_song = st.text_input("Song hinzufügen")
song_interpret = st.text_input("Interpret (optional)")
song_duration = st.number_input("Dauer in Minuten", 0, 20, 3)

if st.button("➕ Song zur Liste hinzufügen"):
    if new_song:
        st.session_state.song_pool.append({
            "title": new_song,
            "interpret": song_interpret,
            "duration": song_duration
        })
        st.success(f"'{new_song}' hinzugefügt!")
    else:
        st.warning("Bitte Songtitel eingeben.")

# Step 2: Anzahl Sets bestimmen
st.header("2. Anzahl Sets")
num_sets = st.slider("Wie viele Sets?", 1, 5, 2)
for i in range(num_sets):
    st.subheader(f"🎵 Set {i+1}")
    st.write("👉 (Drag & Drop-Funktion kommt später)")
    st.write("Noch keine Songs zugewiesen.")

# Songpool anzeigen
st.header("🎼 Aktueller Songpool")
if st.session_state.song_pool:
    for s in st.session_state.song_pool:
        st.markdown(f"- {s['title']} ({s['duration']} min) – *{s['interpret']}*")
else:
    st.info("Noch keine Songs hinzugefügt.")
