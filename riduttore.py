import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
#                CURVA DI WÖHLER REALE
# ============================================================

def sigma_a_wohler(N, materiale):
    if materiale == "42CrMo4":
        sigma_f = 1150
        b = -0.085
        Se = 450
    elif materiale == "C45":
        sigma_f = 850
        b = -0.095
        Se = 250
    else:
        return None

    if N < 1e6:
        return sigma_f * (N ** b)
    else:
        return Se

# ============================================================
#                  GOODMAN (per confronto)
# ============================================================

def sigma_a_goodman(sigma_b, tau, Se, Su):
    return Se * (1 - (tau / Su))

# ============================================================
#             DIAMETRO MINIMO A FATICA WÖHLER
# ============================================================

def diametro_minimo_wohler(Mb, T, n_rpm, Mat, Se, Su):
    N = 10000 * 3600 * (n_rpm / 60)

    # ----- Ricerca GOODMAN per confronto -----
    d_goodman = None
    for d in np.arange(5, 200, 0.1):
        sigma_b = 32 * Mb / (np.pi * d**3)
        tau = 16 * T / (np.pi * d**3)
        sigma_eq = np.sqrt(sigma_b**2 + 3 * tau**2)
        sigma_lim_G = sigma_a_goodman(sigma_b, tau, Se, Su)
        if sigma_eq <= sigma_lim_G:
            d_goodman = d
            break

    # ----- Ricerca WÖHLER -----
    for d in np.arange(5, 200, 0.1):
        sigma_b = 32 * Mb / (np.pi * d**3)
        tau = 16 * T / (np.pi * d**3)
        sigma_eq = np.sqrt(sigma_b**2 + 3 * tau**2)
        sigma_lim_W = sigma_a_wohler(N, Mat)

        if sigma_eq <= sigma_lim_W:
            return d, d_goodman

    return None, None

# ============================================================
#                        STREAMLIT UI
# ============================================================

st.set_page_config(page_title="Dimensionamento Riduttore",
                   layout="wide",
                   page_icon="⚙️")

st.sidebar.title("⚙️ Parametri di Input")

P = st.sidebar.number_input("Potenza P [kW]", value=5.0)
n1 = st.sidebar.number_input("Velocità ingresso n₁ [rpm]", value=1500.0)
i = st.sidebar.number_input("Rapporto di riduzione i", value=4.0)
z1 = st.sidebar.number_input("Numero denti pignone z₁", value=20)
alpha_deg = st.sidebar.number_input("Angolo pressione α [°]", value=20.0)
eta = st.sidebar.number_input("Efficienza η", value=0.95)

materiale_ruote = st.sidebar.selectbox("Materiale ruote", ["20MnCr5", "C45"])
materiale_alberi = st.sidebar.selectbox("Materiale alberi", ["42CrMo4", "C45"])

st.title("🔧 Progetto Riduttore")


# ===== CONTROLLI INPUT =====
if z1 < 18:
    st.error("❌ Il pignone deve avere almeno 18 denti (evita sottotaglio).")
    st.stop()

# ============================================================
# MATERIALI
# ============================================================

if materiale_ruote == "20MnCr5":
    sigmaF_amm = 300
    sigmaH_amm = 1400
elif materiale_ruote == "C45":
    sigmaF_amm = 180
    sigmaH_amm = 850

if materiale_alberi == "42CrMo4":
    Se = 450
    Su = 950
elif materiale_alberi == "C45":
    Se = 250
    Su = 600

# ============================================================
# COPPIE
# ============================================================

T1 = 9550 * P / n1
T2 = T1 * i * eta

# ============================================================
# MODULO (Lewis + Hertz)
# ============================================================

MList = np.array([1,1.25,1.5,2,2.5,3,4,5,6,8,10,12,16,20])
alpha = np.radians(alpha_deg)

for m in MList:
    b = 10 * m
    d1 = m * z1

    Ft = 2 * T1 * 1000 / d1
    Fr = Ft * np.tan(alpha)

    sigmaF = Ft / (b * m * 0.33)
    if sigmaF > sigmaF_amm:
        continue

    sigmaH = 189 * np.sqrt(Ft / (b * d1))
    if sigmaH > sigmaH_amm:
        continue

    modulo = m
    larghezza = b
    break

z2 = i * z1

# ============================================================
# LUCI REALISTICHE
# ============================================================

L_in = larghezza + 50
L_out = larghezza + 70

# ============================================================
# MOMENTI FLETTENTI MAX
# ============================================================

Mmax_in = Fr * L_in / 4
Mmax_out = Fr * L_out / 4

# ============================================================
# DIAMETRI A FATICA (WÖHLER + GOODMAN)
# ============================================================

dmin1, d_good1 = diametro_minimo_wohler(Mmax_in, T1*1000, n1,
                                        materiale_alberi, Se, Su)

dmin2, d_good2 = diametro_minimo_wohler(Mmax_out, T2*1000, n1/i,
                                        materiale_alberi, Se, Su)

# Diametri minimi costruttivi
dmin1 = max(dmin1, 20)
dmin2 = max(dmin2, 25)

# ============================================================
# FRECCIA
# ============================================================

E = 210000
I_in = np.pi * dmin1**4 / 64
I_out = np.pi * dmin2**4 / 64

delta_in = Fr * L_in**3 / (48 * E * I_in)
delta_out = Fr * L_out**3 / (48 * E * I_out)

# ============================================================
# OUTPUT CARDS (NO unsafe_allow_html in st.info/warning/success)
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### ⚙️ Ingranaggi")
    st.markdown(
        f"""
        <div style="padding: 12px; border-radius: 6px; background-color:#e7f3fe;">
            <b>z₂:</b> {z2:.1f}<br>
            <b>Modulo m:</b> {modulo} mm<br>
            <b>Larghezza b:</b> {larghezza} mm
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown("### 📈 Forze")
    st.markdown(
        f"""
        <div style="padding: 12px; border-radius: 6px; background-color:#e8ffe8;">
            <b>Fₜ:</b> {Ft:.1f} N<br>
            <b>Fᵣ:</b> {Fr:.1f} N
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown("### 🔩 Alberi")
    st.markdown(
        f"""
        <div style="padding: 12px; border-radius: 6px; background-color:#fff3cd;">
            <b>d ingresso:</b> {dmin1:.1f} mm 
            <br>(Goodman = {d_good1:.1f} mm)<br><br>
            <b>d uscita:</b> {dmin2:.1f} mm
            <br>(Goodman = {d_good2:.1f} mm)
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# ============================================================
#           CARD COPPIE, MOMENTO MAX, FRECCIA MAX
# ============================================================

st.markdown("## 📘 Risultati aggiuntivi")

colA, colB, colC = st.columns(3)

# ---- COPPIE ----
with colA:
    st.markdown("### 🔄 Coppie")
    st.markdown(
        f"""
        <div style="padding: 12px; border-radius: 6px; background-color:#eef7ff;">
            <b>Coppia ingresso T₁:</b> {T1:.2f} N·m<br>
            <b>Coppia uscita T₂:</b> {T2:.2f} N·m
        </div>
        """,
        unsafe_allow_html=True
    )

# ---- MOMENTI MAX ----
with colB:
    st.markdown("### 📐 Momenti massimi")
    st.markdown(
        f"""
        <div style="padding: 12px; border-radius: 6px; background-color:#fff4e5;">
            <b>Mmax ingresso:</b> {Mmax_in:.2f} N·mm<br>
            <b>Mmax uscita:</b> {Mmax_out:.2f} N·mm
        </div>
        """,
        unsafe_allow_html=True
    )

# ---- FRECCE ----
with colC:
    st.markdown("### 📉 Deflessioni massime")
    st.markdown(
        f"""
        <div style="padding: 12px; border-radius: 6px; background-color:#e8ffe8;">
            <b>δ ingresso:</b> {delta_in:.4f} mm<br>
            <b>δ uscita:</b> {delta_out:.4f} mm
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# GRAFICI INTERATTIVI MOMENTO & TAGLIO (Plotly)
# ============================================================

def diagram_plot(L, Fr, title):
    x = np.arange(0, int(L)+1)
    RA = Fr / 2
    V = np.where(x <= L/2, RA, RA - Fr)
    M = np.where(x <= L/2, RA*x, RA*x - Fr*(x - L/2))

    fig = make_subplots(rows=2, cols=1,
                        subplot_titles=("Taglio " + title,
                                        "Momento " + title))

    fig.add_trace(go.Scatter(x=x, y=V, mode="lines",
                             line=dict(color="blue")),
                  row=1, col=1)

    fig.add_trace(go.Scatter(x=x, y=M, mode="lines",
                             line=dict(color="red")),
                  row=2, col=1)

    fig.update_layout(height=600, showlegend=False)
    return fig

st.header("📊 Diagrammi di Taglio e Momento")
st.plotly_chart(diagram_plot(L_in, Fr, "— Albero Ingresso"))
st.plotly_chart(diagram_plot(L_out, Fr, "— Albero Uscita"))
