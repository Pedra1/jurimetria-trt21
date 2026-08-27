# ─────────────────────────────────────────────
# APP PRINCIPAL — DASHBOARD MULTI-TRIBUNAL
# Judicialização dos Direitos Sociais no RN
# ODSS · UFERSA · CNPq/MCTI/FNDCT
# ─────────────────────────────────────────────
import streamlit as st
import base64
from pathlib import Path
from datetime import datetime

# ── Page config (must be first Streamlit call) ──
st.set_page_config(
    page_title="Judicialização dos Direitos Sociais · RN",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Premium Design & Brand Customization ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    /* Global Typography & Font Family override */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Soft Slate Background for Main Area */
    .stApp {
        background-color: #F8FAFC !important;
    }

    /* Professional Headings styling */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        color: #0F172A !important;
        letter-spacing: -0.02em !important;
    }

    /* Premium styled dashboard cards for Streamlit Metrics */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 1.25rem 1.5rem !important;
        box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.04) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.05), 0 4px 6px -4px rgba(15, 23, 42, 0.05) !important;
        border-color: #CBD5E1 !important;
    }
    
    /* Metrics Label and Value Styling */
    div[data-testid="stMetricLabel"] > div {
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: #64748B !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #0F172A !important;
        letter-spacing: -0.03em !important;
    }

    /* Modern Tabs layout customization */
    button[data-baseweb="tab"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        color: #64748B !important;
        padding: 0.75rem 1.25rem !important;
        transition: all 0.2s ease !important;
        border-bottom-width: 2px !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #0F172A !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #0969DA !important;
        border-bottom-color: #0969DA !important;
    }

    /* Professional dark sidebar aesthetic */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B !important;
    }
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] p {
        color: #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #1E293B !important;
    }

    /* Spacing adjustments */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1300px !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Imports ──
from data_loader import carregar_todos
from config import CORES_TRIBUNAL

# ── Logo ──
_LOGO_PATH = Path(__file__).parent / "logodatalab.jpg"
if _LOGO_PATH.exists():
    _LOGO_B64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    _LOGO_SRC = f"data:image/jpeg;base64,{_LOGO_B64}"
else:
    _LOGO_B64 = None
    _LOGO_SRC = ""

# ── Sidebar: Branding + Navegação ──
with st.sidebar:
    if _LOGO_B64:
        st.markdown(f"""
        <div style='text-align:center; padding: 0.8rem 0 0.3rem;'>
            <img src='{_LOGO_SRC}' style='width: 130px; border-radius: 10px; margin-bottom: 0.4rem;' alt='ODSS DataLab'>
            <br>
            <span style='font-size: 0.95rem; font-weight: 700; color: #58A6FF; letter-spacing: 0.05em;'>JUDICIALIZAÇÃO RN</span><br>
            <span style='font-size: 0.65rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.1em;'>Direitos Sociais · Multi-Tribunal</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='text-align:center; padding: 1rem 0 0.5rem;'>
            <span style='font-size: 2.2rem;'>⚖️</span><br>
            <span style='font-size: 0.95rem; font-weight: 700; color: #58A6FF; letter-spacing: 0.05em;'>JUDICIALIZAÇÃO RN</span><br>
            <span style='font-size: 0.65rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.1em;'>Direitos Sociais · Multi-Tribunal</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Navegação por radio buttons ──
    secao = st.radio(
        "📌 SEÇÃO",
        options=[
            "📊  Visão Geral",
            "⚖️  TRT21 — Trabalho",
            "📋  TRT21 — ULISSES",
            "🏛️  TJRN — Estadual (Saúde)",
            "🇧🇷  JFRN — Federal (Saúde)",
        ],
        index=0,
        key="nav_secao",
    )

    st.markdown("---")

# ── Carregar dados ──
with st.spinner("Carregando dados dos tribunais..."):
    dados = carregar_todos()

# Verificar se há dados
has_data = any(not df.empty for df in dados.values())
if not has_data:
    st.error("⚠️ Nenhum ficheiro Parquet encontrado na pasta atual.")
    st.info("Certifique-se de que os arquivos `processos_*.parquet` estão na mesma pasta do script.")
    st.stop()

# ── Roteamento ──
if "Visão Geral" in secao:
    from secao_overview import render_overview
    render_overview(dados)

elif "TRT21" in secao and "ULISSES" in secao:
    from secao_trt21_ulisses import render_trt21_ulisses
    render_trt21_ulisses(dados['TRT21_ULISSES'])

elif "TRT21" in secao:
    from secao_trt21 import render_trt21
    render_trt21(dados['TRT21'])

elif "TJRN" in secao:
    from secao_tribunal import render_tribunal_generico
    render_tribunal_generico(dados['TJRN'], 'TJRN')

elif "JFRN" in secao:
    from secao_tribunal import render_tribunal_generico
    render_tribunal_generico(dados['JFRN'], 'JFRN')

# ── Rodapé ──
st.divider()
_footer_logo = f"<img src='{_LOGO_SRC}' style='width: 100px; border-radius: 8px; margin-bottom: 0.8rem; opacity: 0.92;' alt='ODSS DataLab'>" if _LOGO_B64 else ""
st.markdown(f"""
<div style='text-align: center; padding: 1.5rem 1rem; color: #8B949E; font-size: 0.78rem; line-height: 1.8;'>
    {_footer_logo}
    <div style='margin-bottom: 0.6rem;'>
        <span style='font-weight: 700; color: #58A6FF; letter-spacing: 0.03em;'>Judicialização dos Direitos Sociais</span>
        <span style='color: #484F58;'> · </span>
        <span>Rio Grande do Norte</span>
    </div>
    <div style='margin-bottom: 0.8rem; color: #6E7681; font-size: 0.72rem;'>
        Desenvolvido no âmbito do projeto
        <span style='color: #58A6FF; font-weight: 600;'>Observatório dos Direitos Sociais do Semiárido (ODSS)</span>
        · <span style='color: #C9D1D9;'>UFERSA</span><br>
        <span style='color: #484F58; font-size: 0.65rem;'>Financiamento: CNPq/MCTI/FNDCT · Chamada nº 44/2024</span>
    </div>
    <div style='display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; font-size: 0.68rem; color: #484F58;'>
        <span>📊 Dados: <span style='color: #6E7681;'>DataJud · CNJ (API pública)</span></span>
        <span>🔬 Metodologia: <span style='color: #6E7681;'>Análise Quantitativa e Jurimetria</span></span>
        <span>📅 Processamento: <span style='color: #6E7681;'>{datetime.now().strftime('%d/%m/%Y %H:%M')}</span></span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar footer ──
with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center; padding: 0.5rem 0 0.2rem; border-top: 1px solid #21262D; margin-top: 0.5rem;'>
        <span style='font-size: 0.6rem; color: #58A6FF; font-weight: 600; letter-spacing: 0.05em;'>ODSS · UFERSA</span><br>
        <span style='font-size: 0.5rem; color: #484F58; margin-top: 2px; display: inline-block;'>
            Dados: DataJud / CNJ
        </span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:0.7rem; color:#8B949E; text-align:center;'>Atualizado em {datetime.now().strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)
