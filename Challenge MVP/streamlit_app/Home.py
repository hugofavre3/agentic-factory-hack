# """Home — Pilotage des retards de production bogies par IA — Maestro & Sentinelle.

# Point d'entrée Streamlit multipage.
# Lancer avec :
#     streamlit run "Challenge MVP/streamlit_app/Home.py"
# """

# import streamlit as st
# from datetime import date
# from data import build_seed_orders

# st.set_page_config(
#     page_title="Pilotage des retards — Maestro & Sentinelle",
#     page_icon="🏭",
#     layout="wide",
# )

# # =============================================================================
# # Initialisation session_state
# # =============================================================================

# def init_state():
#     """Seed les données en session si pas encore fait."""
#     if "orders" not in st.session_state:
#         st.session_state["orders"] = build_seed_orders()
#     if "maestro_outputs" not in st.session_state:
#         st.session_state["maestro_outputs"] = {}
#     if "sentinelle_outputs" not in st.session_state:
#         st.session_state["sentinelle_outputs"] = {}
#     if "watchlist" not in st.session_state:
#         st.session_state["watchlist"] = []
#     if "email_actions" not in st.session_state:
#         st.session_state["email_actions"] = {}
#     if "time_sim_results" not in st.session_state:
#         st.session_state["time_sim_results"] = {}
#     if "rescheduling_choices" not in st.session_state:
#         st.session_state["rescheduling_choices"] = {}

# init_state()

# # =============================================================================
# # Sidebar
# # =============================================================================

# st.sidebar.title("🏭 Maestro & Sentinelle")
# st.sidebar.caption(
#     "Naviguez entre les vues :\n"
#     "1. **Cockpit d'anticipation** — Film de production et risques\n"
#     "2. **Maestro & Sentinelle** — Décisions et impacts\n"
#     "3. **Vision Macro** — Impact global des décisions IA"
# )
# st.sidebar.divider()
# if st.sidebar.button("🔄 Réinitialiser la démo", type="secondary"):
#     st.session_state["orders"] = build_seed_orders()
#     st.session_state["maestro_outputs"] = {}
#     st.session_state["sentinelle_outputs"] = {}
#     st.session_state["watchlist"] = []
#     st.session_state["email_actions"] = {}
#     st.session_state["time_sim_results"] = {}
#     st.session_state["rescheduling_choices"] = {}
#     st.rerun()

# # =============================================================================
# # Page Home
# # =============================================================================

# # ── Date du jour ──
# today = date(2026, 3, 12)
# st.markdown(
#     f"<div style='text-align:center; padding:10px; background:#1a1a2e; border-radius:8px; margin-bottom:16px;'>"
#     f"<span style='font-size:1.4em;'>📅 Aujourd'hui : <b>{today.strftime('%d/%m/%Y')}</b></span>"
#     f"</div>",
#     unsafe_allow_html=True,
# )

# st.title("🏭 Pilotage des retards de production bogies par IA")
# st.markdown("## Maestro & Sentinelle")

# st.markdown(
#     "**Dans une industrie où l'on ne peut pas s'arrêter en plein milieu d'un bogie, "
#     "l'IA anticipe les risques de blocage bien avant qu'ils n'arrivent.**\n\n"
#     "La question clé : *\"Si je lance maintenant, ai-je un risque réaliste de me retrouver "
#     "coincé faute de pièces à l'étape X, ou bien les pièces auront-elles très probablement "
#     "eu le temps d'arriver avant que la ligne ne l'atteigne ?\"*"
# )

# st.divider()

# # --- Les deux agents ---
# st.subheader("🎯 Deux agents, un objectif : anticiper, pas subir")

# col1, col2 = st.columns(2)

# with col1:
#     st.markdown(
#         "### 🎼 Maestro\n"
#         "*L'assistant planificateur*\n\n"
#         "Regarde en avance le film de production : étapes, "
#         "temps de passage, stock, délais fournisseurs, historique.\n\n"
#         "**Produit** :\n"
#         "- Un niveau de risque d'arrêt (🟢 / 🟠 / 🔴)\n"
#         "- Une recommandation de lancement ou replanification\n"
#         "- Un plan de commande fournisseur\n"
#         "- Un mail fournisseur simulé"
#     )

# with col2:
#     st.markdown(
#         "### 🔭 Sentinelle\n"
#         "*L'agent qui surveille*\n\n"
#         "Surveille les hypothèses prises par Maestro et "
#         "actualise en continu le risque de retard.\n\n"
#         "**Produit** :\n"
#         "- Mise à jour du risque (levé / confirmé)\n"
#         "- Suivi des livraisons fournisseurs\n"
#         "- Impact actualisé sur la date de fin\n"
#         "- Proposition de reprogrammation si nécessaire"
#     )

# st.divider()

# # --- Les 3 scénarios ---
# st.subheader("📋 Trois scénarios de démo")

# col_ok, col_moy, col_crit = st.columns(3)

# with col_ok:
#     st.markdown(
#         "### ✅ OK\n"
#         "Les pièces sont là ou arriveront bien avant l'étape "
#         "qui les utilise. Maestro valide : *\"On lance comme prévu.\"*"
#     )

# with col_moy:
#     st.markdown(
#         "### ⚠️ Moyen\n"
#         "Une pièce manque, ETA serrée. Maestro recommande un "
#         "créneau décalé et surveille le risque. "
#         "Sentinelle confirme ou lève l'alerte."
#     )

# with col_crit:
#     st.markdown(
#         "### 🛑 Critique\n"
#         "Blocage quasi certain. Maestro propose de ne pas "
#         "lancer et donne des créneaux de reprogrammation. "
#         "Sentinelle actualise si la situation s'améliore."
#     )

# st.divider()

# st.caption(
#     "💡 *On ne parle plus de gérer les casses une fois qu'on est bloqué, "
#     "mais de voir 2–3 jours à l'avance où ça pourrait coincer, "
#     "et d'ajuster le planning en conséquence.*"
# )
# """
# Home — Anticipation des retards de production bogies par IA — Maestro & Sentinelle

# Point d’entrée de l’application Streamlit multipage.
# Lancement :
#     streamlit run "Challenge MVP/streamlit_app/Home.py"
# """

# import streamlit as st
# from datetime import date
# from data import build_seed_orders


# st.set_page_config(
#     page_title="Anticipation des retards — Maestro & Sentinelle",
#     page_icon="🏭",
#     layout="wide",
# )


# # =============================================================================
# # Initialisation session_state
# # =============================================================================


# def init_state():
#     """Initialise les données de démonstration en session si nécessaire."""
#     if "orders" not in st.session_state:
#         st.session_state["orders"] = build_seed_orders()
#     if "maestro_outputs" not in st.session_state:
#         st.session_state["maestro_outputs"] = {}
#     if "sentinelle_outputs" not in st.session_state:
#         st.session_state["sentinelle_outputs"] = {}
#     if "watchlist" not in st.session_state:
#         st.session_state["watchlist"] = []
#     if "email_actions" not in st.session_state:
#         st.session_state["email_actions"] = {}
#     if "time_sim_results" not in st.session_state:
#         st.session_state["time_sim_results"] = {}
#     if "rescheduling_choices" not in st.session_state:
#         st.session_state["rescheduling_choices"] = {}


# init_state()


# # =============================================================================
# # Sidebar
# # =============================================================================


# st.sidebar.title("🏭 Maestro & Sentinelle")
# st.sidebar.caption(
#     "Naviguez entre les vues de démonstration :\n"
#     "1. **Cockpit d’anticipation** — Visualiser les risques par OF et par étape\n"
#     "2. **Maestro & Sentinelle** — Comprendre les décisions et les recommandations\n"
#     "3. **Vision Macro** — Piloter l’impact global sur les retards et le planning"
# )
# st.sidebar.divider()
# if st.sidebar.button("🔄 Réinitialiser la démo", type="secondary"):
#     st.session_state["orders"] = build_seed_orders()
#     st.session_state["maestro_outputs"] = {}
#     st.session_state["sentinelle_outputs"] = {}
#     st.session_state["watchlist"] = []
#     st.session_state["email_actions"] = {}
#     st.session_state["time_sim_results"] = {}
#     st.session_state["rescheduling_choices"] = {}
#     st.rerun()


# # =============================================================================
# # Page Home
# # =============================================================================


# # ── Date du jour ──
# today = date(2026, 3, 12)
# st.markdown(
#     f"<div style='text-align:center; padding:10px; background:#1a1a2e; border-radius:8px; margin-bottom:16px;'>"
#     f"<span style='font-size:1.4em;'>📅 Date du jour : <b>{today.strftime('%d/%m/%Y')}</b></span>"
#     f"</div>",
#     unsafe_allow_html=True,
# )


# st.title("🏭 Anticipation des retards de production bogies par IA")
# st.markdown("## Maestro & Sentinelle")


# st.markdown(
#     "**Dans l’assemblage de bogies, l’enjeu n’est pas seulement de savoir s’il manque une pièce aujourd’hui, "
#     "mais de savoir si cette pièce arrivera avant que la production n’atteigne l’étape où elle devient indispensable.**\n\n"
#     "Cette démonstration montre comment l’IA aide à anticiper les risques de blocage, "
#     "sécuriser les décisions de lancement et limiter les retards de production avant qu’ils ne deviennent visibles en atelier."
# )


# st.divider()


# # --- Les deux agents ---
# st.subheader("🎯 Deux agents complémentaires pour sécuriser le flux de production")


# col1, col2 = st.columns(2)


# with col1:
#     st.markdown(
#         "### 🎼 Maestro\n"
#         "*L’assistant planificateur*\n\n"
#         "Maestro analyse le film de production en amont : "
#         "étapes de la gamme, stock disponible, délais fournisseurs, historique et contraintes planning.\n\n"
#         "**Il produit :**\n"
#         "- Une estimation du risque de blocage par OF\n"
#         "- Une recommandation de lancement, de vigilance ou de replanification\n"
#         "- Une estimation d’impact sur la durée et le retard\n"
#         "- Un projet de message fournisseur prêt à validation"
#     )


# with col2:
#     st.markdown(
#         "### 🔭 Sentinelle\n"
#         "*L’agent de surveillance matière*\n\n"
#         "Sentinelle suit dans le temps les OF sous surveillance et vérifie si les hypothèses de Maestro se confirment.\n\n"
#         "**Elle produit :**\n"
#         "- Une mise à jour du risque de blocage (levé, maintenu ou aggravé)\n"
#         "- Une vision actualisée de l’arrivée des pièces\n"
#         "- L’impact réestimé sur la date de fin OF\n"
#         "- Des recommandations de sécurisation ou de reprogrammation"
#     )


# st.divider()


# # --- Les 3 scénarios ---
# st.subheader("📋 Trois scénarios de démonstration")


# col_ok, col_moy, col_crit = st.columns(3)


# with col_ok:
#     st.markdown(
#         "### ✅ Scénario OK\n"
#         "Les pièces sont disponibles ou arriveront largement avant l’étape critique. "
#         "Le risque de blocage est faible et la production peut être lancée sereinement."
#     )


# with col_moy:
#     st.markdown(
#         "### ⚠️ Scénario Moyen\n"
#         "Une pièce manque encore, mais les délais restent compatibles avec l’avancement du flux. "
#         "Le risque est surveillé de près et peut être levé si la livraison arrive à temps."
#     )


# with col_crit:
#     st.markdown(
#         "### 🛑 Scénario Critique\n"
#         "L’analyse montre un risque fort d’atteindre l’étape critique avant la livraison des pièces. "
#         "Maestro propose alors des créneaux alternatifs de reprogrammation pour limiter le retard."
#     )


# st.divider()


# st.caption(
#     "💡 *L’objectif n’est pas de gérer un arrêt une fois qu’il est arrivé, "
#     "mais d’anticiper plusieurs jours à l’avance les points de blocage potentiels, "
#     "pour décider au bon moment et garder la maîtrise du planning atelier.*"
# )
"""
Home — Anticipating bogie production delays with AI — Maestro & Sentinelle


Entry point for the multipage Streamlit application.
Launch:
    streamlit run "Challenge MVP/streamlit_app/Home.py"
"""


import streamlit as st
from datetime import date
from data import build_seed_orders



st.set_page_config(
    page_title="Delay anticipation — Maestro & Sentinelle",
    page_icon="🏭",
    layout="wide",
)



# =============================================================================
# Session state initialization
# =============================================================================



def init_state():
    """Initialize demo data in session state if needed."""
    if "orders" not in st.session_state:
        st.session_state["orders"] = build_seed_orders()
    if "maestro_outputs" not in st.session_state:
        st.session_state["maestro_outputs"] = {}
    if "sentinelle_outputs" not in st.session_state:
        st.session_state["sentinelle_outputs"] = {}
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []
    if "email_actions" not in st.session_state:
        st.session_state["email_actions"] = {}
    if "time_sim_results" not in st.session_state:
        st.session_state["time_sim_results"] = {}
    if "rescheduling_choices" not in st.session_state:
        st.session_state["rescheduling_choices"] = {}



init_state()



# =============================================================================
# Sidebar
# =============================================================================



st.sidebar.title("🏭 Maestro & Sentinelle")
st.sidebar.caption(
    "Navigate through the demo views:\n"
    "1. **Anticipation cockpit** — Visualize risks by production order and by step\n"
    "2. **Maestro & Sentinelle** — Understand decisions and recommendations\n"
    "3. **Macro view** — Monitor the overall impact on delays and scheduling"
)
st.sidebar.divider()
if st.sidebar.button("🔄 Reset demo", type="secondary"):
    st.session_state["orders"] = build_seed_orders()
    st.session_state["maestro_outputs"] = {}
    st.session_state["sentinelle_outputs"] = {}
    st.session_state["watchlist"] = []
    st.session_state["email_actions"] = {}
    st.session_state["time_sim_results"] = {}
    st.session_state["rescheduling_choices"] = {}
    st.rerun()



# =============================================================================
# Home page
# =============================================================================



# ── Current date ──
today = date(2026, 3, 12)
st.markdown(
    f"<div style='text-align:center; padding:10px; background:#1a1a2e; border-radius:8px; margin-bottom:16px;'>"
    f"<span style='font-size:1.4em;'>📅 Current date: <b>{today.strftime('%d/%m/%Y')}</b></span>"
    f"</div>",
    unsafe_allow_html=True,
)



st.title("🏭 Anticipating bogie production delays with AI")
st.markdown("## Maestro & Sentinelle")



st.markdown(
    "**In bogie assembly, the challenge is not only knowing whether a part is missing today, "
    "but whether that part will arrive before production reaches the stage where it becomes essential.**\n\n"
    "This demonstration shows how AI helps anticipate blocking risks, "
    "secure production launch decisions, and limit production delays before they become visible on the shop floor."
)



st.divider()



# --- The two agents ---
st.subheader("🎯 Two complementary agents to secure the production flow")



col1, col2 = st.columns(2)



with col1:
    st.markdown(
        "### 🎼 Maestro\n"
        "*The planning assistant*\n\n"
        "Maestro analyzes the production flow upstream: "
        "routing steps, available stock, supplier lead times, historical data, and scheduling constraints.\n\n"
        "**It provides:**\n"
        "- An estimate of blocking risk for each production order\n"
        "- A recommendation to launch, monitor closely, or reschedule\n"
        "- An estimate of impact on duration and delay\n"
        "- A supplier message draft ready for validation"
    )



with col2:
    st.markdown(
        "### 🔭 Sentinelle\n"
        "*The material monitoring agent*\n\n"
        "Sentinelle tracks monitored production orders over time and checks whether Maestro’s assumptions are confirmed.\n\n"
        "**It provides:**\n"
        "- An updated blocking risk status (cleared, maintained, or worsened)\n"
        "- An up-to-date view of part arrivals\n"
        "- A revised estimate of impact on the production order completion date\n"
        "- Recommendations for securing the situation or rescheduling"
    )



st.divider()



# --- The 3 scenarios ---
st.subheader("📋 Three demonstration scenarios")



col_ok, col_moy, col_crit = st.columns(3)



with col_ok:
    st.markdown(
        "### ✅ OK scenario\n"
        "Parts are available or will arrive well before the critical step. "
        "The blocking risk is low and production can be launched with confidence."
    )



with col_moy:
    st.markdown(
        "### ⚠️ Medium scenario\n"
        "A part is still missing, but lead times remain compatible with the progress of the flow. "
        "The risk is closely monitored and may be cleared if the delivery arrives on time."
    )



with col_crit:
    st.markdown(
        "### 🛑 Critical scenario\n"
        "The analysis shows a high risk of reaching the critical step before the parts are delivered. "
        "Maestro then proposes alternative rescheduling slots to limit the delay."
    )



st.divider()



st.caption(
    "💡 *The goal is not to manage a stoppage once it has already happened, "
    "but to anticipate potential blocking points several days in advance, "
    "so the right decisions can be made at the right time and control over the workshop schedule can be maintained.*"
)
