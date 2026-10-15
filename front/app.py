import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from front.api_client import ErreurApi, se_connecter, verifier_api

st.set_page_config(page_title="VéloVille", page_icon="🚲", layout="wide")

try:
    verifier_api()
except ErreurApi as erreur:
    st.error(str(erreur))
    st.stop()

if "access_token" not in st.session_state:
    st.title("VéloVille")
    st.subheader("Connexion")
    with st.form("connexion"):
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        soumettre = st.form_submit_button("Se connecter")
    if soumettre:
        try:
            with st.spinner("Connexion en cours..."):
                resultat = se_connecter(username, password)
            st.session_state["access_token"] = resultat["access_token"]
            st.session_state["role"] = resultat["role"]
            st.rerun()
        except ErreurApi as erreur:
            st.error(f"Connexion impossible : {erreur}")
else:
    st.title("VéloVille")
    st.write(f"Session ouverte : **{st.session_state.get('role', 'utilisateur')}**")
    st.info("Les pages Stations, Incidents et Indicateurs sont disponibles dans le menu.")
    if st.button("Se déconnecter"):
        st.session_state.pop("access_token", None)
        st.session_state.pop("role", None)
        st.rerun()
