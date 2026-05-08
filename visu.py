import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob
import numpy as np
from datetime import datetime
import json
import base64
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Jurimetria TRT21 · RN",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
# PALETA DE CORES CONSISTENTE
# ─────────────────────────────────────────────
COR_PRIMARIA   = "#58A6FF"
COR_SECUNDARIA = "#3FB950"
COR_ALERTA     = "#D29922"
COR_PERIGO     = "#F85149"
COR_ROXO       = "#BC8CFF"
COR_CIANO      = "#39D3F0"
COR_LARANJA    = "#FF7B54"
ESCALA_AZUL    = ["#0D1F36", "#0C2D5A", "#1C3F80", "#2958B3", "#388BFD", "#58A6FF", "#79BFFF", "#A5D3FF"]
FUNDO_PLOT     = "rgba(0,0,0,0)"
FUNDO_PAPEL    = "rgba(22,27,34,0)"
FONTE_PLOT     = dict(family="Sora, sans-serif", size=12, color="#8B949E")
LINHA_GRADE    = "#21262D"
TEXTO_EIXO     = "#8B949E"

# ─────────────────────────────────────────────
# DICIONÁRIO GEOGRÁFICO — COMARCAS TRT21/RN
# Coordenadas das sedes das varas do trabalho
# ─────────────────────────────────────────────
COMARCAS_GEO = {
    "Natal":                    {"lat": -5.7945,  "lon": -35.2110, "varas": 13, "regiao": "Grande Natal"},
    "Parnamirim":               {"lat": -5.9148,  "lon": -35.2633, "varas": 1,  "regiao": "Grande Natal"},
    "São Gonçalo do Amarante":  {"lat": -5.7939,  "lon": -35.3314, "varas": 1,  "regiao": "Grande Natal"},
    "Ceará-Mirim":              {"lat": -5.6381,  "lon": -35.4253, "varas": 1,  "regiao": "Grande Natal"},
    "Macaíba":                  {"lat": -5.8569,  "lon": -35.3564, "varas": 1,  "regiao": "Grande Natal"},
    "Mossoró":                  {"lat": -5.1879,  "lon": -37.3441, "varas": 4,  "regiao": "Oeste"},
    "Macau":                    {"lat": -5.1101,  "lon": -36.6322, "varas": 2,  "regiao": "Salineira"},
    "Assu":                     {"lat": -5.5719,  "lon": -36.9075, "varas": 1,  "regiao": "Vale do Açu"},
    "Pau dos Ferros":           {"lat": -6.1108,  "lon": -38.2042, "varas": 1,  "regiao": "Alto Oeste"},
    "Caicó":                    {"lat": -6.4583,  "lon": -37.0972, "varas": 1,  "regiao": "Seridó"},
    "Currais Novos":            {"lat": -6.2597,  "lon": -36.5158, "varas": 1,  "regiao": "Seridó"},
    "Santa Cruz":               {"lat": -6.2239,  "lon": -35.8244, "varas": 1,  "regiao": "Trairi"},
    "Goianinha":                {"lat": -6.2692,  "lon": -35.2011, "varas": 1,  "regiao": "Litoral Sul"},
    "Nova Cruz":                {"lat": -6.2503,  "lon": -35.4253, "varas": 1,  "regiao": "Agreste"},
    "Caraúbas":                 {"lat": -5.7842,  "lon": -37.5567, "varas": 1,  "regiao": "Oeste"},
    "Apodi":                    {"lat": -5.6597,  "lon": -37.7958, "varas": 1,  "regiao": "Oeste"},
    "João Câmara":              {"lat": -5.5392,  "lon": -35.8136, "varas": 1,  "regiao": "Agreste"},
    "São Paulo do Potengi":     {"lat": -5.8992,  "lon": -35.6419, "varas": 1,  "regiao": "Agreste"},
    "Açu":                      {"lat": -5.5719,  "lon": -36.9075, "varas": 1,  "regiao": "Vale do Açu"},
}

import unicodedata

def _normalizar(texto: str) -> str:
    """Remove acentos e converte para maiúsculas para comparação robusta."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).upper().strip()

# Pré-computa chaves normalizadas do dicionário uma única vez
_COMARCAS_GEO_NORM = {_normalizar(k): (k, v) for k, v in COMARCAS_GEO.items()}

def _match_comarca(nome: str) -> dict | None:
    """Busca coordenadas da comarca por correspondência parcial, sem sensibilidade a acentos."""
    if not nome:
        return None
    nome_norm = _normalizar(nome)
    # 1. Correspondência exata normalizada
    if nome_norm in _COMARCAS_GEO_NORM:
        key, val = _COMARCAS_GEO_NORM[nome_norm]
        return {**val, "nome_geo": key}
    # 2. Correspondência parcial: chave contém o nome ou nome contém a chave
    for key_norm, (key_orig, val) in _COMARCAS_GEO_NORM.items():
        if key_norm in nome_norm or nome_norm in key_norm:
            return {**val, "nome_geo": key_orig}
    return None

def layout_plotly(titulo=""):
    return dict(
        title=dict(text=titulo, font=dict(family="Sora, sans-serif", size=14, color="#C9D1D9"), x=0.01, xanchor="left"),
        paper_bgcolor=FUNDO_PAPEL,
        plot_bgcolor=FUNDO_PLOT,
        font=FONTE_PLOT,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            bgcolor="rgba(22,27,34,0.8)",
            bordercolor="#21262D",
            borderwidth=1,
            font=dict(color="#8B949E", size=11),
        ),
        xaxis=dict(
            gridcolor=LINHA_GRADE,
            tickcolor=LINHA_GRADE,
            tickfont=dict(color=TEXTO_EIXO, size=11),
            linecolor="#21262D",
            zerolinecolor="#21262D",
        ),
        yaxis=dict(
            gridcolor=LINHA_GRADE,
            tickcolor=LINHA_GRADE,
            tickfont=dict(color=TEXTO_EIXO, size=11),
            linecolor="#21262D",
            zerolinecolor="#21262D",
        ),
        hoverlabel=dict(
            bgcolor="#21262D",
            bordercolor="#388BFD",
            font=dict(family="Sora, sans-serif", size=12, color="#E6EDF3"),
        ),
    )

# ─────────────────────────────────────────────
# CARREGAMENTO DE DADOS
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def carregar_dados():
    arquivos = glob.glob("processos_trt21_enriquecido_*.parquet")
    if not arquivos:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)
    df['ano_extracao']     = df['dataajuizamento_dt'].dt.year
    df['mes_extracao']     = df['dataajuizamento_dt'].dt.month
    df['trimestre']        = df['dataajuizamento_dt'].dt.to_period('Q').astype(str)
    df['mes_ano']          = df['dataajuizamento_dt'].dt.to_period('M').astype(str)
    if 'valor_causa' in df.columns:
        df['valor_causa'] = pd.to_numeric(df['valor_causa'], errors='coerce')
    return df

with st.spinner("Carregando dados..."):
    df = carregar_dados()

if df.empty:
    st.error("⚠️  Nenhum ficheiro Parquet encontrado na pasta atual.")
    st.info("Certifique-se de que os arquivos `processos_trt21_enriquecido_*.parquet` estão na mesma pasta do script.")
    st.stop()

# ─────────────────────────────────────────────
# BARRA LATERAL — FILTROS
# ─────────────────────────────────────────────
# ── Carregar logo como base64 para uso em HTML ──
_LOGO_PATH = Path(__file__).parent / "logodatalab.jpg"
if _LOGO_PATH.exists():
    _LOGO_B64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    _LOGO_SRC = f"data:image/jpeg;base64,{_LOGO_B64}"
else:
    _LOGO_B64 = None
    _LOGO_SRC = ""

with st.sidebar:
    if _LOGO_B64:
        st.markdown(f"""
        <div style='text-align:center; padding: 0.8rem 0 0.3rem;'>
            <img src='{_LOGO_SRC}' style='width: 130px; border-radius: 10px; margin-bottom: 0.4rem;' alt='ODSS DataLab'>
            <br>
            <span style='font-size: 1rem; font-weight: 700; color: #58A6FF; letter-spacing: 0.05em;'>JURIMETRIA RN</span><br>
            <span style='font-size: 0.7rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.1em;'>TRT 21ª Região</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='text-align:center; padding: 1rem 0 0.5rem;'>
            <span style='font-size: 2.2rem;'>⚖️</span><br>
            <span style='font-size: 1rem; font-weight: 700; color: #58A6FF; letter-spacing: 0.05em;'>JURIMETRIA RN</span><br>
            <span style='font-size: 0.7rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.1em;'>TRT 21ª Região</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**📅 PERÍODO**")
    anos_disp = sorted(df['ano_extracao'].dropna().unique().tolist())
    anos_sel  = st.multiselect("Anos", options=anos_disp, default=anos_disp, label_visibility="collapsed")

    st.markdown("**📍 COMARCA**")
    comarcas_disp = sorted(df['municipio_comarca'].dropna().unique().tolist())
    comarcas_sel  = st.multiselect("Comarcas", options=comarcas_disp, default=comarcas_disp, label_visibility="collapsed")

    st.markdown("**💻 SISTEMA**")
    sistemas_disp = sorted(df['sistema_nome'].dropna().unique().tolist())
    sistemas_sel  = st.multiselect("Sistemas", options=sistemas_disp, default=sistemas_disp, label_visibility="collapsed")

    # Filtro por assunto (se coluna disponível)
    if 'assunto_primario_nome' in df.columns:
        st.markdown("**📂 ASSUNTO (Top 20)**")
        top_assuntos = df['assunto_primario_nome'].value_counts().head(20).index.tolist()
        assuntos_sel = st.multiselect("Assuntos", options=top_assuntos, default=[], label_visibility="collapsed")
    else:
        assuntos_sel = []

    st.markdown("---")
    st.markdown(f"<p style='font-size:0.7rem; color:#8B949E; text-align:center;'>Atualizado em {datetime.now().strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center; padding: 0.5rem 0 0.2rem; border-top: 1px solid #21262D; margin-top: 0.5rem;'>
        <span style='font-size: 0.6rem; color: #58A6FF; font-weight: 600; letter-spacing: 0.05em;'>ODSS · UFERSA</span><br>
        <span style='font-size: 0.55rem; color: #6E7681; line-height: 1.5;'>
            Kenia Guerreiro · Pedro Nildo<br>Vinicius Augusto
        </span><br>
        <span style='font-size: 0.5rem; color: #484F58; margin-top: 2px; display: inline-block;'>
            Dados: DataJud / CNJ
        </span>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# APLICAR FILTROS
# ─────────────────────────────────────────────
mask = (
    df['ano_extracao'].isin(anos_sel) &
    df['municipio_comarca'].isin(comarcas_sel) &
    df['sistema_nome'].isin(sistemas_sel)
)
if assuntos_sel:
    mask &= df['assunto_primario_nome'].isin(assuntos_sel)

df_f = df[mask].copy()

# ─────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────
st.caption("⚖️ Tribunal Regional do Trabalho · 21ª Região")
st.title("Painel de Jurimetria")
st.markdown("Análise quantitativa da judicialização trabalhista no Rio Grande do Norte · 2020–2024")

if df_f.empty:
    st.warning("Nenhum processo encontrado com os filtros selecionados.")
    st.stop()

# ─────────────────────────────────────────────
# KPIs PRINCIPAIS
# ─────────────────────────────────────────────
total   = len(df_f)
n_ano   = df_f.groupby('ano_extracao').size()
delta_p = ((n_ano.iloc[-1] - n_ano.iloc[-2]) / n_ano.iloc[-2] * 100) if len(n_ano) >= 2 else 0
media_ano = int(n_ano.mean()) if not n_ano.empty else 0
n_comarcas = df_f['municipio_comarca'].nunique()
ano_pico   = int(n_ano.idxmax()) if not n_ano.empty else "—"

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total de Processos",     f"{total:,}".replace(",", "."),           help="Processos no filtro selecionado")
k2.metric("Variação (último ano)",  f"{delta_p:+.1f}%",                       delta=f"{delta_p:+.1f}%")
k3.metric("Média Anual",            f"{media_ano:,}".replace(",", "."))
k4.metric("Comarcas Analisadas",    f"{n_comarcas}")
k5.metric("Ano de Maior Demanda",   f"{ano_pico}")

st.markdown("---")

# ─────────────────────────────────────────────
# ABAS
# ─────────────────────────────────────────────
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "📈  Evolução Temporal",
    "🗺️  Mapa Interativo",
    "📍  Distribuição Geográfica",
    "📂  Assuntos & Tipos",
    "⚙️  Análise por Sistema",
    "🔍  Explorar Dados",
])

# ══════════════════════════════════════════════
# ABA 1 — EVOLUÇÃO TEMPORAL
# ══════════════════════════════════════════════
with aba1:
    col_a, col_b = st.columns([2, 1])

    with col_a:
        # Série histórica anual com anotações
        df_anual = df_f.groupby('ano_extracao').size().reset_index(name='qtd')
        fig_linha = go.Figure()
        fig_linha.add_trace(go.Scatter(
            x=df_anual['ano_extracao'], y=df_anual['qtd'],
            mode='lines+markers+text',
            text=df_anual['qtd'].apply(lambda v: f"{v:,}".replace(",",".")),
            textposition='top center',
            textfont=dict(size=10, color=COR_PRIMARIA),
            line=dict(color=COR_PRIMARIA, width=2.5),
            marker=dict(size=8, color=COR_PRIMARIA, line=dict(color="#0D1117", width=2)),
            fill='tozeroy',
            fillcolor='rgba(88,166,255,0.06)',
            name='Processos',
            hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
        ))
        fig_linha.update_layout(**layout_plotly("Evolução Anual de Processos"))
        fig_linha.update_xaxes(tickmode='linear', dtick=1)
        st.plotly_chart(fig_linha, use_container_width=True)

    with col_b:
        # Crescimento YoY
        df_anual['delta'] = df_anual['qtd'].pct_change() * 100
        df_anual_delta = df_anual.dropna(subset=['delta'])
        cores_delta = [COR_SECUNDARIA if v >= 0 else COR_PERIGO for v in df_anual_delta['delta']]
        # Typo corrigido
        cores_delta = [COR_SECUNDARIA if v >= 0 else COR_PERIGO for v in df_anual_delta['delta']]
        fig_delta = go.Figure(go.Bar(
            x=df_anual_delta['ano_extracao'],
            y=df_anual_delta['delta'].round(1),
            marker_color=cores_delta,
            text=df_anual_delta['delta'].apply(lambda v: f"{v:+.1f}%"),
            textposition='outside',
            textfont=dict(size=10, color="#C9D1D9"),
            hovertemplate="<b>%{x}</b><br>Variação: %{y:.1f}%<extra></extra>",
        ))
        fig_delta.update_layout(**layout_plotly("Variação Anual (%)"))
        fig_delta.update_xaxes(tickmode='linear', dtick=1)
        fig_delta.add_hline(y=0, line_dash="dash", line_color="#21262D")
        st.plotly_chart(fig_delta, use_container_width=True)

    st.markdown("---")

    col_c, col_d = st.columns(2)

    with col_c:
        # Heatmap mês × ano
        if 'mes_extracao' in df_f.columns:
            df_heat = df_f.groupby(['ano_extracao', 'mes_extracao']).size().reset_index(name='qtd')
            df_pivot = df_heat.pivot(index='mes_extracao', columns='ano_extracao', values='qtd').fillna(0)
            meses_pt = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
            df_pivot.index = [meses_pt[i-1] for i in df_pivot.index]
            fig_heat = go.Figure(go.Heatmap(
                z=df_pivot.values,
                x=[str(c) for c in df_pivot.columns],
                y=df_pivot.index,
                colorscale=[[0,'#0D1117'],[0.3,'#1C3F80'],[0.7,'#388BFD'],[1,'#A5D3FF']],
                hovertemplate="<b>%{y} %{x}</b><br>%{z:.0f} processos<extra></extra>",
                showscale=True,
                colorbar=dict(
                    tickfont=dict(color="#8B949E", size=10),
                    outlinewidth=0,
                    bgcolor="rgba(0,0,0,0)",
                ),
            ))
            fig_heat.update_layout(**layout_plotly("Distribuição Mensal (Heatmap)"))
            st.plotly_chart(fig_heat, use_container_width=True)

    with col_d:
        # Tendência trimestral
        if 'trimestre' in df_f.columns:
            df_trim = df_f.groupby('trimestre').size().reset_index(name='qtd').sort_values('trimestre')
            # Filtrar apenas com dados do período selecionado
            df_trim = df_trim.tail(20)
            fig_trim = go.Figure(go.Bar(
                x=df_trim['trimestre'],
                y=df_trim['qtd'],
                marker=dict(
                    color=df_trim['qtd'],
                    colorscale=[[0,'#1C3F80'],[1,'#58A6FF']],
                    showscale=False,
                ),
                hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
            ))
            fig_trim.update_layout(**layout_plotly("Evolução Trimestral"))
            fig_trim.update_xaxes(tickangle=45)
            st.plotly_chart(fig_trim, use_container_width=True)

# ══════════════════════════════════════════════
# ABA 2 — MAPA INTERATIVO DO RN (Choropleth por município)
# ══════════════════════════════════════════════

# ── Carregar GeoJSON dos municípios do RN (código IBGE UF 24) ──
import urllib.request

_GEOJSON_URL = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-24-mun.json"
# GeoJSON dos estados vizinhos (CE=23, PB=25, PE=26) — contorno estadual apenas
_GEOJSON_ESTADOS_URLS = {
    "Ceará": "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-23-mun.json",
    "Paraíba": "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-25-mun.json",
}

@st.cache_data(show_spinner=False)
def _carregar_geojson_rn():
    """Baixa e retorna o GeoJSON de municípios do RN."""
    req = urllib.request.Request(_GEOJSON_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

@st.cache_data(show_spinner=False)
def _carregar_geojson_vizinhos():
    """Baixa GeoJSON dos estados vizinhos e dissolve em contorno único por estado."""
    estados = {}
    for nome, url in _GEOJSON_ESTADOS_URLS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                # Coletar todas as coordenadas dos municípios como features individuais
                estados[nome] = data
        except Exception:
            pass
    return estados

# ── Mapeamento: município → comarca (jurisdição TRT21) ──
# Cada comarca atende a um conjunto de municípios do RN.
_MUNICIPIO_PARA_COMARCA = {
    # Grande Natal
    "Natal": "Natal", "Parnamirim": "Parnamirim",
    "São Gonçalo do Amarante": "São Gonçalo do Amarante",
    "Ceará-Mirim": "Ceará-Mirim", "Macaíba": "Macaíba",
    "Extremoz": "Natal", "São José de Mipibu": "Parnamirim",
    "Nísia Floresta": "Parnamirim", "Monte Alegre": "Parnamirim",
    "Ielmo Marinho": "Ceará-Mirim", "Taipu": "Ceará-Mirim",
    "Poço Branco": "Ceará-Mirim", "Bento Fernandes": "Ceará-Mirim",
    "Maxaranguape": "Ceará-Mirim", "Rio do Fogo": "Ceará-Mirim",
    "Touros": "Ceará-Mirim", "Pureza": "Ceará-Mirim",
    "São Pedro": "Macaíba",
    # Oeste — Mossoró
    "Mossoró": "Mossoró", "Baraúna": "Mossoró", "Grossos": "Mossoró",
    "Tibau": "Mossoró", "Areia Branca": "Mossoró", "Serra do Mel": "Mossoró",
    # Macau / Salineira
    "Macau": "Macau", "Guamaré": "Macau", "Galinhos": "Macau",
    "Porto do Mangue": "Macau", "Pendências": "Macau",
    "Alto do Rodrigues": "Macau", "Carnaubais": "Macau",
    "Jandaíra": "Macau", "Pedra Grande": "Macau",
    "São Bento do Norte": "Macau", "Caiçara do Norte": "Macau",
    "Parazinho": "Macau",
    # Vale do Açu
    "Açu": "Açu", "Assu": "Assu", "Ipanguaçu": "Assu",
    "São Rafael": "Assu", "Itajá": "Assu", "Paraú": "Assu",
    "Pedro Avelino": "Assu", "Angicos": "Assu",
    "Fernando Pedroza": "Assu", "Lajes": "Assu",
    "Jardim de Angicos": "Assu", "Afonso Bezerra": "Assu",
    "Bodó": "Assu",
    # Alto Oeste — Pau dos Ferros
    "Pau dos Ferros": "Pau dos Ferros", "São Francisco do Oeste": "Pau dos Ferros",
    "Portalegre": "Pau dos Ferros", "Viçosa": "Pau dos Ferros",
    "Riacho de Santana": "Pau dos Ferros", "Taboleiro Grande": "Pau dos Ferros",
    "Francisco Dantas": "Pau dos Ferros", "Encanto": "Pau dos Ferros",
    "Água Nova": "Pau dos Ferros", "Luís Gomes": "Pau dos Ferros",
    "Major Sales": "Pau dos Ferros", "José da Penha": "Pau dos Ferros",
    "Marcelino Vieira": "Pau dos Ferros", "Paraná": "Pau dos Ferros",
    "Coronel João Pessoa": "Pau dos Ferros", "Doutor Severiano": "Pau dos Ferros",
    "Rafael Fernandes": "Pau dos Ferros", "Pilões": "Pau dos Ferros",
    "Tenente Ananias": "Pau dos Ferros", "Alexandria": "Pau dos Ferros",
    "João Dias": "Pau dos Ferros",
    # Seridó — Caicó
    "Caicó": "Caicó", "São Fernando": "Caicó", "Timbaúba dos Batistas": "Caicó",
    "Jardim de Piranhas": "Caicó", "Serra Negra do Norte": "Caicó",
    "São João do Sabugi": "Caicó", "Ipueira": "Caicó",
    "Jardim do Seridó": "Caicó", "Ouro Branco": "Caicó",
    "São José do Seridó": "Caicó", "Cruzeta": "Caicó",
    # Seridó — Currais Novos
    "Currais Novos": "Currais Novos", "Acari": "Currais Novos",
    "Carnaúba dos Dantas": "Currais Novos", "Parelhas": "Currais Novos",
    "Equador": "Currais Novos", "Cerro Corá": "Currais Novos",
    "Lagoa Nova": "Currais Novos", "Florânia": "Currais Novos",
    "São Vicente": "Currais Novos", "Tenente Laurentino Cruz": "Currais Novos",
    "Santana do Matos": "Currais Novos",
    # Trairi — Santa Cruz
    "Santa Cruz": "Santa Cruz", "Tangará": "Santa Cruz",
    "São Paulo do Potengi": "São Paulo do Potengi",
    "Campo Redondo": "Santa Cruz", "Coronel Ezequiel": "Santa Cruz",
    "Jaçanã": "Santa Cruz", "São Bento do Trairi": "Santa Cruz",
    "Lajes Pintadas": "Santa Cruz", "Sítio Novo": "Santa Cruz",
    "Japi": "Santa Cruz", "São Tomé": "São Paulo do Potengi",
    "Barcelona": "São Paulo do Potengi", "Ruy Barbosa": "São Paulo do Potengi",
    "Senador Elói de Souza": "São Paulo do Potengi",
    "Lagoa de Velhos": "São Paulo do Potengi",
    "Santa Maria": "São Paulo do Potengi",
    "Caiçara do Rio do Vento": "São Paulo do Potengi",
    # Litoral Sul — Goianinha
    "Goianinha": "Goianinha", "Arês": "Goianinha",
    "Tibau do Sul": "Goianinha", "Senador Georgino Avelino": "Goianinha",
    "Espírito Santo": "Goianinha", "Vila Flor": "Goianinha",
    "Baía Formosa": "Goianinha", "Canguaretama": "Goianinha",
    "Pedro Velho": "Goianinha", "Montanhas": "Goianinha",
    "Várzea": "Goianinha",
    # Agreste — Nova Cruz
    "Nova Cruz": "Nova Cruz", "Passa e Fica": "Nova Cruz",
    "Lagoa d'Anta": "Nova Cruz", "Lagoa de Pedras": "Nova Cruz",
    "Lagoa Salgada": "Nova Cruz", "Brejinho": "Nova Cruz",
    "Januário Cicco": "Nova Cruz", "Passagem": "Nova Cruz",
    "Jundiá": "Nova Cruz", "Monte das Gameleiras": "Nova Cruz",
    "Serrinha": "Nova Cruz", "Serra de São Bento": "Nova Cruz",
    "Santo Antônio": "Nova Cruz", "Bom Jesus": "Nova Cruz",
    # Oeste — Caraúbas
    "Caraúbas": "Caraúbas", "Governador Dix-Sept Rosado": "Caraúbas",
    "Felipe Guerra": "Caraúbas", "Janduís": "Caraúbas",
    "Messias Targino": "Caraúbas", "Upanema": "Caraúbas",
    # Oeste — Apodi
    "Apodi": "Apodi", "Itaú": "Apodi", "Severiano Melo": "Apodi",
    "Rodolfo Fernandes": "Apodi", "Umarizal": "Apodi",
    "Olho-d'Água do Borges": "Apodi",
    # Agreste — João Câmara
    "João Câmara": "João Câmara", "Jandaíra": "João Câmara",
    "Pedra Preta": "João Câmara",
    # Restante — Patu, Almino Afonso, Lucrécia, Frutuoso Gomes, Martins, etc
    "Patu": "Caraúbas", "Almino Afonso": "Caraúbas",
    "Lucrécia": "Caraúbas", "Frutuoso Gomes": "Caraúbas",
    "Martins": "Caraúbas", "Antônio Martins": "Caraúbas",
    "São Miguel": "Pau dos Ferros",
    # Augusto Severo (Campo Grande) / Triunfo Potiguar
    "Augusto Severo": "Caraúbas", "Triunfo Potiguar": "Assu",
    "Jucurutu": "Caicó",
}

with aba2:

    # ── Dados base: respeita ano e sistema, ignora filtro de comarca ──
    _mask_mapa = pd.Series([True] * len(df), index=df.index)
    if anos_sel:
        _mask_mapa &= df['ano_extracao'].isin(anos_sel)
    if sistemas_sel:
        _mask_mapa &= df['sistema_nome'].isin(sistemas_sel)
    df_mapa_base = df[_mask_mapa].copy()

    # ── Recorte temporal interno do mapa ──
    anos_mapa_disp = ["Todos os anos"] + [str(a) for a in sorted(df_mapa_base['ano_extracao'].dropna().unique())]
    ano_mapa = st.selectbox("Recorte temporal", anos_mapa_disp, key="mapa_ano")

    if ano_mapa != "Todos os anos":
        df_fonte = df_mapa_base[df_mapa_base['ano_extracao'] == int(ano_mapa)]
    else:
        df_fonte = df_mapa_base

    # ── Georreferenciar comarcas ──
    df_cnt = df_fonte['municipio_comarca'].value_counts().reset_index()
    df_cnt.columns = ['comarca', 'processos']
    total_proc = df_cnt['processos'].sum()

    rows = []
    for _, row in df_cnt.iterrows():
        geo = _match_comarca(row['comarca'])
        if geo:
            top_ass = (
                df_fonte[df_fonte['municipio_comarca'] == row['comarca']]
                ['assunto_primario_nome'].value_counts().index[0]
                if 'assunto_primario_nome' in df_fonte.columns
                and df_fonte[df_fonte['municipio_comarca'] == row['comarca']]['assunto_primario_nome'].notna().any()
                else "—"
            )
            rows.append({
                "comarca":    row['comarca'],
                "nome":       geo["nome_geo"],
                "processos":  int(row['processos']),
                "pct":        round(row['processos'] / total_proc * 100, 1),
                "lat":        geo["lat"],
                "lon":        geo["lon"],
                "varas":      geo["varas"],
                "regiao":     geo["regiao"],
                "top_assunto": str(top_ass)[:45],
            })

    df_geo = pd.DataFrame(rows)

    if df_geo.empty:
        st.warning("Nenhuma comarca pôde ser georreferenciada com os filtros atuais.")
    else:
        # ── KPIs ──
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Comarcas no mapa",   len(df_geo))
        m2.metric("Comarca líder",      df_geo.loc[df_geo['processos'].idxmax(), 'nome'])
        m3.metric("Processos na líder", f"{df_geo['processos'].max():,}".replace(",","."))
        m4.metric("Regiões cobertas",   df_geo['regiao'].nunique())

        st.markdown("---")

        # ── Carregar GeoJSON e construir dados por município ──
        try:
            geojson_rn = _carregar_geojson_rn()
        except Exception:
            geojson_rn = None
            st.error("Não foi possível carregar o GeoJSON dos municípios do RN.")

        if geojson_rn is not None:
            # Criar lookup de comarca por nome normalizado
            _comarca_lookup_norm = {}
            for mun_name, com_name in _MUNICIPIO_PARA_COMARCA.items():
                _comarca_lookup_norm[_normalizar(mun_name)] = com_name

            # Criar lookup de info da comarca
            comarca_info = {}
            for _, r in df_geo.iterrows():
                comarca_info[r['nome']] = r
                comarca_info[r['comarca']] = r

            # Para cada feature do GeoJSON, associar à comarca
            mun_rows = []
            for feat in geojson_rn['features']:
                mun_name = feat['properties'].get('name', '')
                mun_id = feat['properties'].get('id', '')
                mun_norm = _normalizar(mun_name)

                # Encontrar comarca deste município
                comarca_nome = _comarca_lookup_norm.get(mun_norm)
                if comarca_nome is None:
                    # Tentar correspondência parcial no dicionário
                    for k_norm, v_com in _comarca_lookup_norm.items():
                        if k_norm in mun_norm or mun_norm in k_norm:
                            comarca_nome = v_com
                            break

                # Buscar dados da comarca
                info = None
                if comarca_nome:
                    # Tenta match exato e depois normalizado
                    info = comarca_info.get(comarca_nome)
                    if info is None:
                        cn = _normalizar(comarca_nome)
                        for k, v in comarca_info.items():
                            if _normalizar(k) == cn:
                                info = v
                                break

                if info is not None:
                    mun_rows.append({
                        'mun_id': mun_id,
                        'municipio': mun_name,
                        'comarca': info['nome'],
                        'processos': info['processos'],
                        'pct': info['pct'],
                        'varas': info['varas'],
                        'regiao': info['regiao'],
                        'top_assunto': info['top_assunto'],
                    })
                else:
                    mun_rows.append({
                        'mun_id': mun_id,
                        'municipio': mun_name,
                        'comarca': '—',
                        'processos': 0,
                        'pct': 0.0,
                        'varas': 0,
                        'regiao': '—',
                        'top_assunto': '—',
                    })

            df_mun = pd.DataFrame(mun_rows)

            # ── Mapa choropleth flat — RN com contexto dos estados vizinhos ──
            fig_mapa = px.choropleth_mapbox(
                df_mun,
                geojson=geojson_rn,
                locations='mun_id',
                featureidkey='properties.id',
                color='processos',
                color_continuous_scale=[
                    [0.0,  "#0D1F36"],
                    [0.15, "#1C3F80"],
                    [0.35, "#2958B3"],
                    [0.55, "#388BFD"],
                    [0.75, "#58A6FF"],
                    [1.0,  "#A5D3FF"],
                ],
                mapbox_style="carto-darkmatter",
                zoom=7.0,
                center={"lat": -5.80, "lon": -36.40},
                opacity=0.92,
                custom_data=['municipio', 'comarca', 'processos', 'pct', 'varas', 'regiao', 'top_assunto'],
            )

            fig_mapa.update_traces(
                marker_line_width=0.8,
                marker_line_color="#30363D",
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "─────────────────<br>"
                    "Comarca: <b>%{customdata[1]}</b><br>"
                    "Processos na comarca: <b>%{customdata[2]:,}</b> (%{customdata[3]}%)<br>"
                    "Varas do Trabalho: %{customdata[4]}<br>"
                    "Região: %{customdata[5]}<br>"
                    "Principal assunto:<br>%{customdata[6]}"
                    "<extra></extra>"
                ),
            )

            # ── Adicionar estados vizinhos como camada de contexto sutil ──
            try:
                estados_vizinhos = _carregar_geojson_vizinhos()
            except Exception:
                estados_vizinhos = {}

            mapbox_layers = []
            for nome_estado, geojson_estado in estados_vizinhos.items():
                # Preenchimento sutil para diferenciar do fundo
                mapbox_layers.append(dict(
                    sourcetype="geojson",
                    source=geojson_estado,
                    type="fill",
                    color="rgba(30, 37, 48, 0.6)",
                    below="traces",
                ))
                # Contorno estadual externo
                mapbox_layers.append(dict(
                    sourcetype="geojson",
                    source=geojson_estado,
                    type="line",
                    color="rgba(88, 166, 255, 0.15)",
                    line=dict(width=0.6),
                    below="traces",
                ))

            fig_mapa.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                mapbox=dict(
                    layers=mapbox_layers,
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=650,
                showlegend=False,
                coloraxis_colorbar=dict(
                    title=dict(text="Processos", font=dict(size=11, color="#8B949E")),
                    tickfont=dict(size=10, color="#8B949E"),
                    thickness=10,
                    len=0.5,
                    bgcolor="rgba(0,0,0,0)",
                    borderwidth=0,
                    x=1.0,
                ),
                hoverlabel=dict(
                    bgcolor="#1C2333",
                    bordercolor="#388BFD",
                    font=dict(family="Sora, sans-serif", size=12, color="#E6EDF3"),
                    align="left",
                ),
            )

            st.plotly_chart(fig_mapa, use_container_width=True)

            st.caption("🗺️ Mapa do Rio Grande do Norte · Municípios coloridos pelo volume de processos da comarca · Passe o mouse para ver detalhes do tribunal.")

        st.markdown("---")

        # ── Ranking + barras por região ──
        col_tab, col_bar = st.columns([1, 2])

        with col_tab:
            st.markdown("**Ranking de Comarcas**")
            df_rank = (
                df_geo[['nome','regiao','processos','pct','varas']]
                .sort_values('processos', ascending=False)
                .reset_index(drop=True)
            )
            df_rank.index += 1
            df_rank.columns = ['Comarca','Região','Processos','%','Varas']
            df_rank['Processos'] = df_rank['Processos'].apply(lambda v: f"{v:,}".replace(",","."))
            df_rank['%'] = df_rank['%'].apply(lambda v: f"{v}%")
            st.dataframe(df_rank, use_container_width=True, height=360)

        with col_bar:
            df_reg = df_geo.groupby('regiao')['processos'].sum().reset_index().sort_values('processos')
            fig_reg = go.Figure(go.Bar(
                x=df_reg['processos'],
                y=df_reg['regiao'],
                orientation='h',
                marker=dict(
                    color=df_reg['processos'],
                    colorscale=[[0,'#1C3F80'],[1,'#58A6FF']],
                    showscale=False,
                ),
                text=df_reg['processos'].apply(lambda v: f"{v:,}".replace(",",".")),
                textposition='outside',
                textfont=dict(size=10, color="#C9D1D9"),
                hovertemplate="<b>%{y}</b><br>%{x:,} processos<extra></extra>",
            ))
            fig_reg.update_layout(**layout_plotly("Processos por Região"))
            fig_reg.update_layout(height=360)
            fig_reg.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(fig_reg, use_container_width=True)

        # ── Evolução temporal das comarcas mapeadas ──
        st.markdown("---")
        comarcas_mapeadas = df_geo['comarca'].tolist()
        df_evo = (
            df_mapa_base[df_mapa_base['municipio_comarca'].isin(comarcas_mapeadas)]
            .groupby(['ano_extracao','municipio_comarca']).size()
            .reset_index(name='qtd')
        )
        df_evo['label'] = df_evo['municipio_comarca'].apply(
            lambda c: _match_comarca(c)['nome_geo'] if _match_comarca(c) else c
        )
        top8 = df_evo.groupby('label')['qtd'].sum().nlargest(8).index.tolist()
        df_evo_top = df_evo[df_evo['label'].isin(top8)]

        cores_evo = [COR_PRIMARIA, COR_ROXO, COR_CIANO, COR_LARANJA,
                     COR_SECUNDARIA, COR_ALERTA, COR_PERIGO, "#E879F9"]
        fig_evo = go.Figure()
        for i, c in enumerate(top8):
            d = df_evo_top[df_evo_top['label'] == c]
            fig_evo.add_trace(go.Scatter(
                x=d['ano_extracao'], y=d['qtd'],
                mode='lines+markers',
                name=c,
                line=dict(color=cores_evo[i % len(cores_evo)], width=2),
                marker=dict(size=5),
                hovertemplate=f"<b>{c}</b><br>%{{x}}: %{{y:,}} processos<extra></extra>",
            ))
        fig_evo.update_layout(**layout_plotly("Evolução das 8 Maiores Comarcas"))
        fig_evo.update_xaxes(tickmode='linear', dtick=1)
        st.plotly_chart(fig_evo, use_container_width=True)

# ══════════════════════════════════════════════
# ABA 3 — DISTRIBUIÇÃO GEOGRÁFICA (barras/treemap)
# ══════════════════════════════════════════════
with aba3:
    col_a, col_b = st.columns([3, 2])

    with col_a:
        df_comarca = df_f['municipio_comarca'].value_counts().reset_index()
        df_comarca.columns = ['comarca', 'qtd']
        df_comarca['pct'] = (df_comarca['qtd'] / df_comarca['qtd'].sum() * 100).round(1)
        df_comarca = df_comarca.head(20)

        fig_comarca = go.Figure(go.Bar(
            x=df_comarca['qtd'],
            y=df_comarca['comarca'],
            orientation='h',
            marker=dict(
                color=df_comarca['qtd'],
                colorscale=[[0,'#1C3F80'],[0.5,'#388BFD'],[1,'#58A6FF']],
                showscale=False,
            ),
            text=df_comarca.apply(lambda r: f"{r['qtd']:,}  ({r['pct']}%)".replace(",","."), axis=1),
            textposition='outside',
            textfont=dict(size=10, color="#C9D1D9"),
            hovertemplate="<b>%{y}</b><br>%{x:,} processos<extra></extra>",
        ))
        fig_comarca.update_layout(**layout_plotly("Volume por Comarca (Top 20)"))
        fig_comarca.update_layout(height=500)
        fig_comarca.update_yaxes(categoryorder='total ascending')
        st.plotly_chart(fig_comarca, use_container_width=True)

    with col_b:
        # Participação percentual — treemap
        fig_tree = px.treemap(
            df_comarca,
            path=['comarca'],
            values='qtd',
            color='qtd',
            color_continuous_scale=[[0,'#0C2D5A'],[0.5,'#388BFD'],[1,'#A5D3FF']],
            hover_data={'pct': True},
            custom_data=['pct'],
        )
        fig_tree.update_traces(
            hovertemplate="<b>%{label}</b><br>%{value:,} processos<br>%{customdata[0]:.1f}%<extra></extra>",
            textinfo='label+value',
            textfont=dict(size=11, family="Sora"),
        )
        fig_tree.update_layout(**layout_plotly("Participação por Comarca"))
        fig_tree.update_layout(
            height=500,
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=50, b=0),
        )
        st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown("---")

    # Evolução por comarca (top 5) ao longo do tempo
    top5_comarcas = df_f['municipio_comarca'].value_counts().head(5).index.tolist()
    df_ev_comarca = (
        df_f[df_f['municipio_comarca'].isin(top5_comarcas)]
        .groupby(['ano_extracao','municipio_comarca']).size()
        .reset_index(name='qtd')
    )
    cores_comarcas = [COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_ROXO, COR_CIANO]
    fig_ev = go.Figure()
    for i, c in enumerate(top5_comarcas):
        d = df_ev_comarca[df_ev_comarca['municipio_comarca'] == c]
        fig_ev.add_trace(go.Scatter(
            x=d['ano_extracao'], y=d['qtd'],
            mode='lines+markers',
            name=c,
            line=dict(color=cores_comarcas[i % len(cores_comarcas)], width=2),
            marker=dict(size=6),
            hovertemplate=f"<b>{c}</b><br>%{{x}}: %{{y:,}} processos<extra></extra>",
        ))
    fig_ev.update_layout(**layout_plotly("Evolução das 5 Principais Comarcas"))
    fig_ev.update_xaxes(tickmode='linear', dtick=1)
    st.plotly_chart(fig_ev, use_container_width=True)

# ══════════════════════════════════════════════
# ══════════════════════════════════════════════
# ABA 4 — ASSUNTOS & TIPOS
with aba4:
    col_a, col_b = st.columns(2)

    with col_a:
        if 'assunto_primario_nome' in df_f.columns:
            df_ass = df_f['assunto_primario_nome'].value_counts().head(15).reset_index()
            df_ass.columns = ['assunto','qtd']
            df_ass['pct'] = (df_ass['qtd'] / df_ass['qtd'].sum() * 100).round(1)
            # Truncar nomes longos
            df_ass['label'] = df_ass['assunto'].str[:45] + df_ass['assunto'].apply(lambda x: '…' if len(x)>45 else '')

            fig_ass = go.Figure(go.Bar(
                x=df_ass['qtd'],
                y=df_ass['label'],
                orientation='h',
                marker=dict(color=COR_ROXO, opacity=0.85),
                text=df_ass['qtd'].apply(lambda v: f"{v:,}".replace(",",".")),
                textposition='outside',
                textfont=dict(size=10, color="#C9D1D9"),
                hovertemplate="<b>%{y}</b><br>%{x:,} processos<extra></extra>",
            ))
            fig_ass.update_layout(**layout_plotly("Top 15 Assuntos Primários"))
            fig_ass.update_layout(height=520)
            fig_ass.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(fig_ass, use_container_width=True)

    with col_b:
        if 'assunto_primario_nome' in df_f.columns:
            # Donut chart top 8
            df_donut = df_f['assunto_primario_nome'].value_counts().head(8).reset_index()
            df_donut.columns = ['assunto','qtd']
            outros = df_f['assunto_primario_nome'].value_counts().iloc[8:].sum()
            if outros > 0:
                df_donut = pd.concat([df_donut, pd.DataFrame({'assunto':['Outros'],'qtd':[outros]})], ignore_index=True)
            df_donut['label'] = df_donut['assunto'].str[:30]

            fig_donut = go.Figure(go.Pie(
                labels=df_donut['label'],
                values=df_donut['qtd'],
                hole=0.55,
                marker=dict(
                    colors=[COR_PRIMARIA, COR_ROXO, COR_CIANO, COR_LARANJA, COR_SECUNDARIA,
                             COR_ALERTA, COR_PERIGO, "#E879F9", "#94A3B8"],
                    line=dict(color='#0D1117', width=2),
                ),
                hovertemplate="<b>%{label}</b><br>%{value:,}<br>%{percent}<extra></extra>",
                textinfo='percent',
                textfont=dict(size=11),
            ))
            fig_donut.update_layout(**layout_plotly("Participação por Assunto"))
            fig_donut.update_layout(
                height=520,
                annotations=[dict(
                    text=f"<b>{df_f.shape[0]:,}</b><br>total".replace(",","."),
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14, color="#C9D1D9", family="Sora"),
                )],
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("---")

    # Assuntos ao longo do tempo (Top 5)
    if 'assunto_primario_nome' in df_f.columns:
        top5_ass = df_f['assunto_primario_nome'].value_counts().head(5).index.tolist()
        df_ass_tempo = (
            df_f[df_f['assunto_primario_nome'].isin(top5_ass)]
            .groupby(['ano_extracao','assunto_primario_nome']).size()
            .reset_index(name='qtd')
        )
        fig_ass_t = px.area(
            df_ass_tempo, x='ano_extracao', y='qtd',
            color='assunto_primario_nome',
            color_discrete_sequence=[COR_PRIMARIA, COR_ROXO, COR_CIANO, COR_LARANJA, COR_SECUNDARIA],
        )
        fig_ass_t.update_layout(**layout_plotly("Evolução Temporal dos Top 5 Assuntos"))
        fig_ass_t.update_xaxes(tickmode='linear', dtick=1)
        fig_ass_t.update_traces(line_width=1.5)
        st.plotly_chart(fig_ass_t, use_container_width=True)

# ══════════════════════════════════════════════
# ══════════════════════════════════════════════
# ABA 5 — ANÁLISE POR SISTEMA
with aba5:
    col_a, col_b = st.columns(2)

    with col_a:
        df_sis = df_f['sistema_nome'].value_counts().reset_index()
        df_sis.columns = ['sistema','qtd']
        df_sis['pct'] = (df_sis['qtd'] / df_sis['qtd'].sum() * 100).round(1)

        fig_sis = go.Figure(go.Bar(
            x=df_sis['sistema'],
            y=df_sis['qtd'],
            marker=dict(
                color=[COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_ROXO, COR_CIANO, COR_LARANJA][:len(df_sis)],
            ),
            text=df_sis['qtd'].apply(lambda v: f"{v:,}".replace(",",".")),
            textposition='outside',
            textfont=dict(size=11, color="#C9D1D9"),
            hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
        ))
        fig_sis.update_layout(**layout_plotly("Volume por Sistema"))
        st.plotly_chart(fig_sis, use_container_width=True)

    with col_b:
        # Participação ao longo dos anos
        df_sis_ano = df_f.groupby(['ano_extracao','sistema_nome']).size().reset_index(name='qtd')
        fig_sis_area = px.bar(
            df_sis_ano, x='ano_extracao', y='qtd', color='sistema_nome',
            barmode='stack',
            color_discrete_sequence=[COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_ROXO, COR_CIANO, COR_LARANJA],
        )
        fig_sis_area.update_layout(**layout_plotly("Composição por Sistema por Ano"))
        fig_sis_area.update_xaxes(tickmode='linear', dtick=1)
        st.plotly_chart(fig_sis_area, use_container_width=True)

    st.markdown("---")

    # Tabela resumo por sistema
    df_sis_tab = df_f.groupby('sistema_nome').agg(
        Total=('sistema_nome','count'),
        Comarcas=('municipio_comarca', 'nunique'),
    ).reset_index().sort_values('Total', ascending=False)
    df_sis_tab['% do Total'] = (df_sis_tab['Total'] / df_sis_tab['Total'].sum() * 100).round(1).astype(str) + "%"
    df_sis_tab.columns = ['Sistema','Total de Processos','Comarcas Atendidas','% do Total']
    df_sis_tab['Total de Processos'] = df_sis_tab['Total de Processos'].apply(lambda v: f"{v:,}".replace(",","."))

    st.markdown("**Resumo por Sistema**")
    st.dataframe(df_sis_tab, use_container_width=True, hide_index=True)

    # Valor da causa (se disponível)
    if 'valor_causa' in df_f.columns and df_f['valor_causa'].notna().sum() > 0:
        st.markdown("---")
        st.markdown("**💰 Distribuição de Valor da Causa (R$)**")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            df_val = df_f['valor_causa'].dropna()
            p95 = df_val.quantile(0.95)
            df_val_clip = df_val[df_val <= p95]
            fig_hist = go.Figure(go.Histogram(
                x=df_val_clip,
                nbinsx=50,
                marker=dict(color=COR_CIANO, opacity=0.8, line=dict(color='#0D1117', width=0.5)),
                hovertemplate="R$ %{x:,.0f}<br>%{y} processos<extra></extra>",
            ))
            fig_hist.update_layout(**layout_plotly("Distribuição do Valor da Causa (até P95)"))
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_v2:
            df_vc_sis = df_f.groupby('sistema_nome')['valor_causa'].median().reset_index()
            df_vc_sis.columns = ['sistema','mediana']
            df_vc_sis = df_vc_sis.dropna().sort_values('mediana', ascending=True)
            fig_vc = go.Figure(go.Bar(
                x=df_vc_sis['mediana'],
                y=df_vc_sis['sistema'],
                orientation='h',
                marker=dict(color=COR_CIANO, opacity=0.8),
                text=df_vc_sis['mediana'].apply(lambda v: f"R$ {v:,.0f}"),
                textposition='outside',
                textfont=dict(size=10, color="#C9D1D9"),
                hovertemplate="<b>%{y}</b><br>Mediana: R$ %{x:,.0f}<extra></extra>",
            ))
            fig_vc.update_layout(**layout_plotly("Mediana do Valor da Causa por Sistema"))
            st.plotly_chart(fig_vc, use_container_width=True)

# ══════════════════════════════════════════════
# ══════════════════════════════════════════════
# ABA 6 — EXPLORAR DADOS
with aba6:
    st.markdown("**🔎 Pesquisa e Exportação**")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        filtro_comarca_exp = st.selectbox("Comarca", options=["Todas"] + comarcas_disp)
    with col_s2:
        filtro_ano_exp = st.selectbox("Ano", options=["Todos"] + [str(a) for a in anos_disp])
    with col_s3:
        filtro_sistema_exp = st.selectbox("Sistema", options=["Todos"] + sistemas_disp)

    df_exp = df_f.copy()
    if filtro_comarca_exp != "Todas":
        df_exp = df_exp[df_exp['municipio_comarca'] == filtro_comarca_exp]
    if filtro_ano_exp != "Todos":
        df_exp = df_exp[df_exp['ano_extracao'] == int(filtro_ano_exp)]
    if filtro_sistema_exp != "Todos":
        df_exp = df_exp[df_exp['sistema_nome'] == filtro_sistema_exp]

    st.markdown(f"**{len(df_exp):,} registros encontrados**".replace(",","."))

    # Ordenação
    col_ord1, col_ord2 = st.columns([3,1])
    with col_ord1:
        col_sort = st.selectbox("Ordenar por", options=df_exp.columns.tolist(), index=0)
    with col_ord2:
        ordem_asc = st.radio("Ordem", ["↑ Crescente", "↓ Decrescente"], horizontal=True) == "↑ Crescente"

    df_exp_sorted = df_exp.sort_values(col_sort, ascending=ordem_asc)

    st.dataframe(df_exp_sorted.head(1000), use_container_width=True, height=450)

    # Download CSV
    csv = df_exp_sorted.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="⬇️  Baixar CSV (filtrado)",
        data=csv,
        file_name=f"processos_trt21_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime='text/csv',
        use_container_width=True,
    )

    st.markdown("---")

# ─────────────────────────────────────────────
# RODAPÉ
# ─────────────────────────────────────────────
st.divider()
_footer_logo = f"<img src='{_LOGO_SRC}' style='width: 100px; border-radius: 8px; margin-bottom: 0.8rem; opacity: 0.92;' alt='ODSS DataLab'>" if _LOGO_B64 else ""
st.markdown(f"""
<div style='text-align: center; padding: 1.5rem 1rem; color: #8B949E; font-size: 0.78rem; line-height: 1.8;'>
    {_footer_logo}
    <div style='margin-bottom: 0.6rem;'>
        <span style='font-weight: 700; color: #58A6FF; letter-spacing: 0.03em;'>Jurimetria TRT21</span>
        <span style='color: #484F58;'> · </span>
        <span>Rio Grande do Norte</span>
    </div>
    <div style='margin-bottom: 0.8rem; color: #6E7681; font-size: 0.72rem;'>
        Desenvolvido por
        <span style='color: #C9D1D9;'>Kenia Guerreiro</span>,
        <span style='color: #C9D1D9;'>Pedro Nildo</span> e
        <span style='color: #C9D1D9;'>Vinicius Augusto</span><br>
        no âmbito do projeto
        <span style='color: #58A6FF; font-weight: 600;'>Observatório dos Direitos Sociais do Semiárido (ODSS)</span>
        · <span style='color: #C9D1D9;'>UFERSA</span>
    </div>
    <div style='display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; font-size: 0.68rem; color: #484F58;'>
        <span>📊 Dados: <span style='color: #6E7681;'>DataJud · CNJ (API pública)</span></span>
        <span>🤖 <span style='color: #6E7681;'>IA utilizada na implementação</span></span>
        <span>📅 <span style='color: #6E7681;'>{datetime.now().strftime('%d/%m/%Y %H:%M')}</span></span>
    </div>
</div>
""", unsafe_allow_html=True)
