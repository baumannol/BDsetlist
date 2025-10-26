
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
:root { --ink:#0f172a; --muted:#475569; --brand:#004D59; --row:#ffffff; --rowAlt:#f6f7fb; }
html, body, [class*="css"]  { font-family:'Space Mono', monospace; font-size:15px; }
h1,h2,h3,.stButton>button { font-family:'Montserrat', sans-serif; font-weight:700; }
.stButton>button { background:var(--brand); color:#fff; border:none; border-radius:8px; padding:2px 8px; font-size:12px; }
.stButton>button:hover { background:#0d6b7a; }
.small { font-size:12px; color:var(--muted); }
.rowhdr { font-weight:700; }
.setbar { position:sticky; top:0; z-index:20; background:#ffffffd9; border-bottom:1px solid #e5e7eb; padding:4px 6px 8px; }
.badge { padding:2px 6px; border-radius:6px; background:#eef2f7; }
</style>
''', unsafe_allow_html=True)

def latin1_safe(s):
    if not s: return ''
    rep = {"–": "-", "—": "-", "’": "'", "“": '"', "”": '"', "…": "..."}
    for k,v in rep.items():
        s = s.replace(k, v)
    return s.encode('latin-1','replace').decode('latin-1')

def pdf_bytes(pdf):
    out = pdf.output(dest='S')
    if isinstance(out, bytearray): return bytes(out)
    if isinstance(out, str): return out.encode('latin-1','replace')
    return out

st.write("Diese Version ist kompakt, PDF-safe und bereit für Streamlit Cloud.")
