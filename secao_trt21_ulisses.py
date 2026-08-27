# ─────────────────────────────────────────────
# SEÇÃO: TRT21 — ULISSES (BASE CAPA)
# ─────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import json
import urllib.request
from config import *
from dados_ibge_rn import (
    carregar_dados_ibge, obter_vara_municipio, obter_idhm,
    _VARA_MUNICIPIOS, _MUNICIPIO_PARA_VARA, _CORES_VARA, _normalizar,
)
from normalizacao_assuntos import (
    explodir_assuntos, gerar_estatisticas_consolidacao,
)

# ─────────────────────────────────────────────
# DICIONÁRIO GEOGRÁFICO — COMARCAS TRT21/RN
# ─────────────────────────────────────────────
COMARCAS_GEO = {
    "Natal": {"lat": -5.7945, "lon": -35.2110, "varas": 13, "regiao": "Grande Natal"},
    "Parnamirim": {"lat": -5.9148, "lon": -35.2633, "varas": 1, "regiao": "Grande Natal"},
    "São Gonçalo do Amarante": {"lat": -5.7939, "lon": -35.3314, "varas": 1, "regiao": "Grande Natal"},
    "Ceará-Mirim": {"lat": -5.6381, "lon": -35.4253, "varas": 1, "regiao": "Grande Natal"},
    "Macaíba": {"lat": -5.8569, "lon": -35.3564, "varas": 1, "regiao": "Grande Natal"},
    "Mossoró": {"lat": -5.1879, "lon": -37.3441, "varas": 4, "regiao": "Oeste"},
    "Macau": {"lat": -5.1101, "lon": -36.6322, "varas": 2, "regiao": "Salineira"},
    "Assu": {"lat": -5.5719, "lon": -36.9075, "varas": 1, "regiao": "Vale do Açu"},
    "Pau dos Ferros": {"lat": -6.1108, "lon": -38.2042, "varas": 1, "regiao": "Alto Oeste"},
    "Caicó": {"lat": -6.4583, "lon": -37.0972, "varas": 1, "regiao": "Seridó"},
    "Currais Novos": {"lat": -6.2597, "lon": -36.5158, "varas": 1, "regiao": "Seridó"},
    "Santa Cruz": {"lat": -6.2239, "lon": -35.8244, "varas": 1, "regiao": "Trairi"},
    "Goianinha": {"lat": -6.2692, "lon": -35.2011, "varas": 1, "regiao": "Litoral Sul"},
    "Nova Cruz": {"lat": -6.2503, "lon": -35.4253, "varas": 1, "regiao": "Agreste"},
    "Caraúbas": {"lat": -5.7842, "lon": -37.5567, "varas": 1, "regiao": "Oeste"},
    "Apodi": {"lat": -5.6597, "lon": -37.7958, "varas": 1, "regiao": "Oeste"},
    "João Câmara": {"lat": -5.5392, "lon": -35.8136, "varas": 1, "regiao": "Agreste"},
    "São Paulo do Potengi": {"lat": -5.8992, "lon": -35.6419, "varas": 1, "regiao": "Agreste"},
    "Açu": {"lat": -5.5719, "lon": -36.9075, "varas": 1, "regiao": "Vale do Açu"},
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

# ─────────────────────────────────────────────
# GEOJSON — MAPA DO RN
# ─────────────────────────────────────────────
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


# ── Mapeamento: município → comarca ──
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
    "João Câmara": "Ceará-Mirim",  # CSV: Vara de Ceará-Mirim
    "Pedra Preta": "Ceará-Mirim",  # CSV: Vara de Ceará-Mirim
    "Parazinho": "Ceará-Mirim",    # CSV: Vara de Ceará-Mirim
    "Pedra Grande": "Ceará-Mirim", # CSV: Vara de Ceará-Mirim
    "São Pedro": "Macaíba",
    # Oeste — Mossoró
    "Mossoró": "Mossoró", "Baraúna": "Mossoró", "Grossos": "Mossoró",
    "Tibau": "Mossoró", "Areia Branca": "Mossoró", "Serra do Mel": "Mossoró",
    # Macau / Salineira
    "Macau": "Macau", "Guamaré": "Macau", "Galinhos": "Macau",
    "Pendências": "Macau",
    "Alto do Rodrigues": "Macau", "Jandaíra": "Macau",
    "São Bento do Norte": "Macau", "Caiçara do Norte": "Macau",
    "Pedro Avelino": "Macau",  # CSV: Vara de Macau
    # Vale do Açu
    "Açu": "Assu", "Assu": "Assu", "Ipanguaçu": "Assu",
    "São Rafael": "Assu", "Itajá": "Assu", "Paraú": "Assu",
    "Angicos": "Assu",
    "Fernando Pedroza": "Assu", "Lajes": "Assu",
    "Jardim de Angicos": "Assu", "Afonso Bezerra": "Assu",
    "Carnaubais": "Assu",     # CSV: Vara de Assu
    "Porto do Mangue": "Assu",  # CSV: Vara de Assu
    "Santana do Matos": "Assu",  # CSV: "Santana dos Matos" – Vara de Assu
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
    "Bodó": "Currais Novos",  # CSV: Vara de Currais Novos
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
    # Oeste — Mossoró (Caraúbas)
    # Nota: Janduís e Upanema pertencem à Vara de Assu (CSV oficial), não à de Mossoró/Caraúbas
    "Caraúbas": "Mossoró", "Governador Dix-Sept Rosado": "Mossoró",
    "Felipe Guerra": "Mossoró", "Messias Targino": "Mossoró",
    # Alto Oeste — Pau dos Ferros (municípios antes erroneamente em Caraúbas)
    "Patu": "Pau dos Ferros", "Almino Afonso": "Pau dos Ferros",
    "Lucrécia": "Pau dos Ferros", "Frutuoso Gomes": "Pau dos Ferros",
    "Martins": "Pau dos Ferros", "Antônio Martins": "Pau dos Ferros",
    "São Miguel": "Pau dos Ferros",
    # Augusto Severo (Campo Grande) / Janduís / Upanema / Triunfo Potiguar → Vara de Assu
    "Augusto Severo": "Assu",    # CSV: Campo Grande (Augusto Severo) – Vara de Assu
    "Campo Grande": "Assu",      # Nome oficial IBGE/GeoJSON do município Augusto Severo
    "Janduís": "Assu",           # CSV: Vara de Assu
    "Upanema": "Assu",           # CSV: Vara de Assu
    "Triunfo Potiguar": "Assu",  # CSV: Vara de Assu
    "Jucurutu": "Caicó",         # CSV: Vara de Caicó
}


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip('#')
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


def render_trt21_ulisses(df_raw: pd.DataFrame):
    """Renderiza seção completa do TRT21 — Base Ulisses (dados capa)."""

    cor = CORES_TRIBUNAL["TRT21"]["primaria"]
    escala = CORES_TRIBUNAL["TRT21"]["escala"]

    st.caption(" Observatório dos Direitos Sociais do Semiárido · UFERSA")
    st.title("TRT21 — Base Ulisses")
    st.markdown("Análise quantitativa da judicialização trabalhista · TRT 21ª Região · Base de dados capa · 2020–2024")

    if df_raw.empty:
        st.warning("Nenhum dado disponível para TRT21 — Ulisses.")
        return

    # ── Filtros na sidebar ──
    with st.sidebar:
        st.markdown("** PERÍODO**")
        anos_disp = sorted(df_raw['ano'].dropna().unique().tolist())
        anos_sel = st.multiselect("Anos", options=anos_disp, default=anos_disp, label_visibility="collapsed", key="ulisses_anos")

        st.markdown("** COMARCA**")
        comarcas_disp = sorted(df_raw['municipio_comarca'].dropna().unique().tolist())
        comarcas_sel = st.multiselect("Comarcas", options=comarcas_disp, default=comarcas_disp, label_visibility="collapsed", key="ulisses_comarcas")

        st.markdown("** SISTEMA**")
        sistemas_disp = sorted(df_raw['sistema_nome'].dropna().unique().tolist())
        sistemas_sel = st.multiselect("Sistemas", options=sistemas_disp, default=sistemas_disp, label_visibility="collapsed", key="ulisses_sistemas")

        if 'assunto_primario_nome' in df_raw.columns:
            st.markdown("** ASSUNTO (Top 20)**")
            top_assuntos = df_raw['assunto_primario_nome'].value_counts().head(20).index.tolist()
            assuntos_sel = st.multiselect("Assuntos", options=top_assuntos, default=[], label_visibility="collapsed", key="ulisses_assuntos")
        else:
            assuntos_sel = []

    # ── Aplicar filtros ──
    mask = (
        df_raw['ano'].isin(anos_sel) &
        df_raw['municipio_comarca'].isin(comarcas_sel) &
        df_raw['sistema_nome'].isin(sistemas_sel)
    )
    if assuntos_sel:
        mask &= df_raw['assunto_primario_nome'].isin(assuntos_sel)
    df_f = df_raw[mask].copy()

    if df_f.empty:
        st.warning("Nenhum processo encontrado com os filtros selecionados.")
        return

    # ── KPIs ──
    total = len(df_f)
    n_ano = df_f.groupby('ano').size()
    delta_p = ((n_ano.iloc[-1] - n_ano.iloc[-2]) / n_ano.iloc[-2] * 100) if len(n_ano) >= 2 else 0
    media_ano = int(n_ano.mean()) if not n_ano.empty else 0
    n_comarcas = df_f['municipio_comarca'].nunique()
    n_classes = df_f['classe_nome'].nunique() if 'classe_nome' in df_f.columns else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total de Processos", fmt_num(total), help="Processos no filtro selecionado")
    k2.metric("Variação (último ano)", f"{delta_p:+.1f}%", delta=f"{delta_p:+.1f}%")
    k3.metric("Média Anual", fmt_num(media_ano))
    k4.metric("Comarcas Analisadas", f"{n_comarcas}")
    k5.metric("Classes Processuais", f"{n_classes}", help="Tipos de ação identificados")

    st.markdown("---")

    # ── Abas ──
    aba1, aba2, aba3, aba4, aba5, aba6, aba7, aba8, aba9, aba10, aba11 = st.tabs([
        " Evolução Temporal",
        " Mapa Interativo",
        " Distribuição Geográfica",
        " Perfil das Demandas",
        " Estrutura Judicial",
        " Explorar Dados",
        " Lista de Assuntos",
        " Evolução de Assuntos",
        " Saúde do Trabalhador",
        " Ritos Processuais",
        " Notas Técnicas",
    ])

    # ═══════════ ABA 1: EVOLUÇÃO TEMPORAL ═══════════
    with aba1:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            df_anual = df_f.groupby('ano').size().reset_index(name='qtd')
            fig_linha = go.Figure()
            fig_linha.add_trace(go.Scatter(
                x=df_anual['ano'], y=df_anual['qtd'],
                mode='lines+markers+text',
                text=df_anual['qtd'].apply(fmt_num),
                textposition='top center', textfont=dict(size=10, color=cor),
                line=dict(color=cor, width=2.5),
                marker=dict(size=8, color=cor, line=dict(color="#FFFFFF", width=2)),
                fill='tozeroy', fillcolor='rgba(9,105,218,0.06)',
                name='Processos',
                hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
            ))
            fig_linha.update_layout(**layout_plotly("Evolução Anual de Processos"))
            fig_linha.update_xaxes(tickmode='linear', dtick=1)
            st.plotly_chart(fig_linha, use_container_width=True)

        with col_b:
            df_anual['delta'] = df_anual['qtd'].pct_change() * 100
            df_anual_delta = df_anual.dropna(subset=['delta'])
            cores_delta = [COR_SECUNDARIA if v >= 0 else COR_PERIGO for v in df_anual_delta['delta']]
            fig_delta = go.Figure(go.Bar(
                x=df_anual_delta['ano'], y=df_anual_delta['delta'].round(1),
                marker_color=cores_delta,
                text=df_anual_delta['delta'].apply(lambda v: f"{v:+.1f}%"),
                textposition='outside', textfont=dict(size=10, color="#1F2328"),
                hovertemplate="<b>%{x}</b><br>Variação: %{y:.1f}%<extra></extra>",
            ))
            fig_delta.update_layout(**layout_plotly("Variação Anual (%)"))
            fig_delta.update_xaxes(tickmode='linear', dtick=1)
            fig_delta.add_hline(y=0, line_dash="dash", line_color="#D0D7DE")
            st.plotly_chart(fig_delta, use_container_width=True)

        st.markdown("---")
        col_c, col_d = st.columns(2)
        with col_c:
            df_heat = df_f.groupby(['ano', 'mes']).size().reset_index(name='qtd')
            df_pivot = df_heat.pivot(index='mes', columns='ano', values='qtd').fillna(0)
            meses_pt = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
            df_pivot.index = [meses_pt[i-1] for i in df_pivot.index]
            fig_heat = go.Figure(go.Heatmap(
                z=df_pivot.values, x=[str(c) for c in df_pivot.columns], y=df_pivot.index,
                colorscale=[[0,'#F6F8FA'],[0.3,'#BDDDF5'],[0.7,'#4BA0DC'],[1,'#0550AE']],
                hovertemplate="<b>%{y} %{x}</b><br>%{z:.0f} processos<extra></extra>",
                showscale=True,
                colorbar=dict(tickfont=dict(color="#57606A", size=10), outlinewidth=0, bgcolor="rgba(255,255,255,0)"),
            ))
            fig_heat.update_layout(**layout_plotly("Distribuição Mensal (Heatmap)"))
            st.plotly_chart(fig_heat, use_container_width=True)

        with col_d:
            if 'trimestre' in df_f.columns:
                df_trim = df_f.groupby('trimestre').size().reset_index(name='qtd').sort_values('trimestre').tail(20)
                fig_trim = go.Figure(go.Bar(
                    x=df_trim['trimestre'], y=df_trim['qtd'],
                    marker=dict(color=df_trim['qtd'], colorscale=[[0,'#BDDDF5'],[1,'#0550AE']], showscale=False),
                    hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
                ))
                fig_trim.update_layout(**layout_plotly("Evolução Trimestral"))
                fig_trim.update_xaxes(tickangle=45)
                st.plotly_chart(fig_trim, use_container_width=True)

        # ═══════════ ABA 2: MAPA INTERATIVO (POR VARA) ═══════════
    with aba2:

        st.markdown("""
        <div style='background: linear-gradient(135deg, rgba(9,105,218,0.08), rgba(188,140,255,0.06)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #0969DA;'>
            <span style='font-size: 0.78rem; color: #57606A;'>
                Mapa interativo dos <b>167 municipios</b> do Rio Grande do Norte agrupados por <b>Vara Trabalhista</b>.
                Municipios da mesma vara compartilham a mesma cor. Passe o mouse para ver dados socioeconomicos
                (populacao, PIB per capita, IDHM) obtidos via <b>API do IBGE</b>.
            </span>
        </div>
        """, unsafe_allow_html=True)

        # -- Dados base: respeita ano e sistema, ignora filtro de comarca --
        _mask_mapa = pd.Series([True] * len(df_raw), index=df_raw.index)
        if anos_sel:
            _mask_mapa &= df_raw['ano'].isin(anos_sel)
        if sistemas_sel:
            _mask_mapa &= df_raw['sistema_nome'].isin(sistemas_sel)
        df_mapa_base = df_raw[_mask_mapa].copy()

        # -- Recorte temporal interno do mapa --
        anos_mapa_disp = ["Todos os anos"] + [str(a) for a in sorted(df_mapa_base['ano'].dropna().unique())]
        ano_mapa = st.selectbox("Recorte temporal", anos_mapa_disp, key="ulisses_mapa_ano")

        if ano_mapa != "Todos os anos":
            df_fonte = df_mapa_base[df_mapa_base['ano'] == int(ano_mapa)]
        else:
            df_fonte = df_mapa_base

        # -- Processos por comarca (para enrichment) --
        df_cnt = df_fonte['municipio_comarca'].value_counts().reset_index()
        df_cnt.columns = ['comarca', 'processos']
        total_proc = df_cnt['processos'].sum()
        proc_por_comarca = dict(zip(df_cnt['comarca'], df_cnt['processos']))

        # -- Assunto principal por comarca --
        assunto_por_comarca = {}
        if 'assunto_primario_nome' in df_fonte.columns:
            for comarca_name in df_cnt['comarca']:
                sub = df_fonte[df_fonte['municipio_comarca'] == comarca_name]['assunto_primario_nome'].dropna()
                if not sub.empty:
                    assunto_por_comarca[comarca_name] = str(sub.value_counts().index[0])[:45]

        # -- Processos por vara (soma de todas as comarcas da vara) --
        proc_por_vara = {}
        for vara, muns_vara in _VARA_MUNICIPIOS.items():
            total = 0
            for comarca_name, n_proc in proc_por_comarca.items():
                cn = _normalizar(comarca_name)
                for mv in muns_vara:
                    if _normalizar(mv) == cn or _normalizar(vara) == cn:
                        total += n_proc
                        break
            proc_por_vara[vara] = total

        # -- Carregar dados socioeconomicos do IBGE --
        dados_ibge = carregar_dados_ibge()

        # -- KPIs --
        pop_total = sum(d['populacao'] for d in dados_ibge.values())
        vara_lider = max(proc_por_vara, key=proc_por_vara.get) if proc_por_vara else "-"
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Varas Trabalhistas", len(_VARA_MUNICIPIOS))
        m2.metric("Municipios Mapeados", sum(len(v) for v in _VARA_MUNICIPIOS.values()))
        m3.metric("Populacao Total (RN)", f"{pop_total:,}".replace(",", "."))
        m4.metric("Vara c/ Mais Processos", vara_lider)

        st.markdown("---")

        # -- Carregar GeoJSON --
        try:
            geojson_rn = _carregar_geojson_rn()
        except Exception:
            geojson_rn = None
            st.error("Nao foi possivel carregar o GeoJSON dos municipios do RN.")

        if geojson_rn is not None:
            # Construir dataframe por municipio do GeoJSON
            mun_rows = []
            for feat in geojson_rn['features']:
                mun_name = feat['properties'].get('name', '')
                mun_id = feat['properties'].get('id', '')

                vara = obter_vara_municipio(mun_name)
                idhm = obter_idhm(mun_name)

                # Dados IBGE
                ibge = dados_ibge.get(mun_name, {})
                if not ibge:
                    # Tentar match normalizado
                    mn = _normalizar(mun_name)
                    for k, v in dados_ibge.items():
                        if _normalizar(k) == mn:
                            ibge = v
                            break

                populacao = ibge.get('populacao', 0)
                pib_pc = ibge.get('pib_pc', 0.0)
                area = ibge.get('area', 0.0)

                # Processos da vara
                n_proc_vara = proc_por_vara.get(vara, 0) if vara else 0

                # Assunto principal da comarca/vara
                top_ass = '—'
                if vara:
                    # Tenta match da comarca pelo nome do municipio
                    for com_key, ass in assunto_por_comarca.items():
                        if _normalizar(com_key) == _normalizar(vara) or _normalizar(com_key) == _normalizar(mun_name):
                            top_ass = ass
                            break

                # Densidade demografica
                dens = round(populacao / area, 1) if area > 0 else 0.0

                mun_rows.append({
                    'mun_id': mun_id,
                    'municipio': mun_name,
                    'vara': vara or 'Sem vara',
                    'vara_idx': list(_CORES_VARA.keys()).index(vara) if vara and vara in _CORES_VARA else -1,
                    'populacao': populacao,
                    'pop_fmt': f"{populacao:,}".replace(",", "."),
                    'pib_pc': pib_pc,
                    'pib_fmt': f"R$ {pib_pc:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    'idhm': idhm or 0,
                    'idhm_fmt': f"{idhm:.3f}" if idhm else '—',
                    'area': area,
                    'area_fmt': f"{area:,.1f} km²".replace(",", "X").replace(".", ",").replace("X", "."),
                    'densidade': dens,
                    'dens_fmt': f"{dens:,.1f} hab/km²".replace(",", "X").replace(".", ",").replace("X", "."),
                    'processos_vara': n_proc_vara,
                    'proc_fmt': f"{n_proc_vara:,}".replace(",", "."),
                    'top_assunto': top_ass,
                    'cor': _CORES_VARA.get(vara, '#D0D7DE'),
                })

            df_mun = pd.DataFrame(mun_rows)

            # -- Mapa choropleth discreto por vara --
            fig_mapa = go.Figure()

            for vara_nome, cor in _CORES_VARA.items():
                df_vara = df_mun[df_mun['vara'] == vara_nome]
                if df_vara.empty:
                    continue

                fig_mapa.add_trace(go.Choroplethmap(
                    geojson=geojson_rn,
                    locations=df_vara['mun_id'],
                    featureidkey='properties.id',
                    z=[1] * len(df_vara),  # dummy uniform value
                    colorscale=[[0, cor], [1, cor]],
                    showscale=False,
                    name=vara_nome,
                    marker=dict(opacity=0.85, line=dict(width=0.8, color='#FFFFFF')),
                    customdata=df_vara[[
                        'municipio', 'vara', 'pop_fmt', 'pib_fmt',
                        'idhm_fmt', 'area_fmt', 'dens_fmt',
                        'proc_fmt', 'top_assunto',
                    ]].values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "━━━━━━━━━━━━━━━━━━━━<br>"
                        "Vara: <b>%{customdata[1]}</b><br>"
                        "━━━━━━━━━━━━━━━━━━━━<br>"
                        "Populacao: <b>%{customdata[2]}</b><br>"
                        "PIB per capita: <b>%{customdata[3]}</b><br>"
                        "IDHM (2010): <b>%{customdata[4]}</b><br>"
                        "Area: %{customdata[5]}<br>"
                        "Densidade: %{customdata[6]}<br>"
                        "━━━━━━━━━━━━━━━━━━━━<br>"
                        "Processos na vara: <b>%{customdata[7]}</b><br>"
                        "Assunto principal: %{customdata[8]}"
                        "<extra></extra>"
                    ),
                ))

            # Municipios sem vara (se houver)
            df_sem = df_mun[df_mun['vara'] == 'Sem vara']
            if not df_sem.empty:
                fig_mapa.add_trace(go.Choroplethmap(
                    geojson=geojson_rn,
                    locations=df_sem['mun_id'],
                    featureidkey='properties.id',
                    z=[1] * len(df_sem),
                    colorscale=[[0, '#D0D7DE'], [1, '#D0D7DE']],
                    showscale=False,
                    name='Sem vara definida',
                    marker=dict(opacity=0.5, line=dict(width=0.5, color='#E1E4E8')),
                    customdata=df_sem[[
                        'municipio', 'vara', 'pop_fmt', 'pib_fmt',
                        'idhm_fmt', 'area_fmt', 'dens_fmt',
                        'proc_fmt', 'top_assunto',
                    ]].values,
                    hovertemplate="<b>%{customdata[0]}</b><br>Sem vara definida<extra></extra>",
                ))

            # -- Estados vizinhos --
            try:
                estados_vizinhos = _carregar_geojson_vizinhos()
            except Exception:
                estados_vizinhos = {}

            map_layers = []
            for nome_estado, geojson_estado in estados_vizinhos.items():
                map_layers.append(dict(
                    sourcetype="geojson", source=geojson_estado,
                    type="fill", color="rgba(240, 244, 248, 0.6)", below="traces",
                ))
                map_layers.append(dict(
                    sourcetype="geojson", source=geojson_estado,
                    type="line", color="rgba(189, 221, 245, 0.5)",
                    line=dict(width=0.6), below="traces",
                ))

            fig_mapa.update_layout(
                paper_bgcolor="rgba(255,255,255,0)",
                plot_bgcolor="rgba(255,255,255,0)",
                map=dict(
                    style="carto-positron",
                    zoom=7.0,
                    center={"lat": -5.80, "lon": -36.40},
                    layers=map_layers,
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=680,
                showlegend=True,
                legend=dict(
                    title=dict(text="Varas Trabalhistas", font=dict(size=12, color="#1F2328")),
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="#D0D7DE",
                    borderwidth=1,
                    font=dict(size=11, color="#1F2328"),
                    x=0.01, y=0.99,
                    xanchor='left', yanchor='top',
                ),
                hoverlabel=dict(
                    bgcolor="#F6F8FA",
                    bordercolor="#0969DA",
                    font=dict(family="Sora, sans-serif", size=12, color="#1F2328"),
                    align="left",
                ),
            )

            st.plotly_chart(fig_mapa, use_container_width=True)

            st.caption("Mapa do Rio Grande do Norte · Municipios coloridos por Vara Trabalhista · Dados socioeconomicos via API IBGE (atualizados).")

        st.markdown("---")

        # -- Ranking de varas + barras --
        col_tab, col_bar = st.columns([1, 2])

        with col_tab:
            st.markdown("**Ranking de Varas**")
            vara_rows = []
            for vara, muns_v in _VARA_MUNICIPIOS.items():
                n_proc = proc_por_vara.get(vara, 0)
                pop_vara = sum(dados_ibge.get(m, {}).get('populacao', 0) for m in muns_v)
                vara_rows.append({
                    'Vara': vara,
                    'Municipios': len(muns_v),
                    'Processos': n_proc,
                    '%': round(n_proc / total_proc * 100, 1) if total_proc > 0 else 0,
                    'Populacao': pop_vara,
                })
            df_rank_vara = pd.DataFrame(vara_rows).sort_values('Processos', ascending=False).reset_index(drop=True)
            df_rank_vara.index += 1
            df_rank_display = df_rank_vara.copy()
            df_rank_display['Processos'] = df_rank_display['Processos'].apply(lambda v: f"{v:,}".replace(",", "."))
            df_rank_display['%'] = df_rank_display['%'].apply(lambda v: f"{v}%")
            df_rank_display['Populacao'] = df_rank_display['Populacao'].apply(lambda v: f"{v:,}".replace(",", "."))
            st.dataframe(df_rank_display, use_container_width=True, height=380)

        with col_bar:
            df_bar_vara = df_rank_vara.sort_values('Processos', ascending=True)
            cores_bar = [_CORES_VARA.get(v, '#D0D7DE') for v in df_bar_vara['Vara']]
            fig_bv = go.Figure(go.Bar(
                x=df_bar_vara['Processos'],
                y=df_bar_vara['Vara'],
                orientation='h',
                marker=dict(color=cores_bar),
                text=df_bar_vara['Processos'].apply(lambda v: f"{v:,}".replace(",", ".")),
                textposition='outside',
                textfont=dict(size=10, color="#1F2328"),
                hovertemplate="<b>%{y}</b><br>%{x:,} processos<extra></extra>",
            ))
            fig_bv.update_layout(**layout_plotly("Processos por Vara Trabalhista"))
            fig_bv.update_layout(height=380)
            fig_bv.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(fig_bv, use_container_width=True)

        # -- Evolucao temporal por vara --
        st.markdown("---")
        df_evo_vara = []
        for vara, muns_v in _VARA_MUNICIPIOS.items():
            muns_norm = {_normalizar(m) for m in muns_v}
            muns_norm.add(_normalizar(vara))  # sede da vara
            mask = df_mapa_base['municipio_comarca'].apply(lambda c: _normalizar(str(c)) in muns_norm)
            sub = df_mapa_base[mask].groupby('ano').size().reset_index(name='qtd')
            sub['vara'] = vara
            df_evo_vara.append(sub)

        if df_evo_vara:
            df_evo_all = pd.concat(df_evo_vara, ignore_index=True)
            top_varas = df_evo_all.groupby('vara')['qtd'].sum().nlargest(9).index.tolist()
            fig_evo_v = go.Figure()
            for vara_nome in top_varas:
                d = df_evo_all[df_evo_all['vara'] == vara_nome].sort_values('ano')
                cor = _CORES_VARA.get(vara_nome, '#999')
                fig_evo_v.add_trace(go.Scatter(
                    x=d['ano'], y=d['qtd'],
                    mode='lines+markers',
                    name=vara_nome,
                    line=dict(color=cor, width=2.5),
                    marker=dict(size=6, color=cor),
                    hovertemplate=f"<b>{vara_nome}</b><br>%{{x}}: %{{y:,}} processos<extra></extra>",
                ))
            fig_evo_v.update_layout(**layout_plotly("Evolucao Temporal por Vara"))
            fig_evo_v.update_xaxes(tickmode='linear', dtick=1)
            st.plotly_chart(fig_evo_v, use_container_width=True)


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
                    colorscale=[[0,'#BDDDF5'],[0.5,'#0969DA'],[1,'#0550AE']],
                    showscale=False,
                ),
                text=df_comarca.apply(lambda r: f"{r['qtd']:,} ({r['pct']}%)".replace(",","."), axis=1),
                textposition='outside',
                textfont=dict(size=10, color="#1F2328"),
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
                color_continuous_scale=[[0,'#D6ECFA'],[0.5,'#0969DA'],[1,'#0550AE']],
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
            .groupby(['ano','municipio_comarca']).size()
            .reset_index(name='qtd')
        )
        cores_comarcas = [COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_ROXO, COR_CIANO]
        fig_ev = go.Figure()
        for i, c in enumerate(top5_comarcas):
            d = df_ev_comarca[df_ev_comarca['municipio_comarca'] == c]
            fig_ev.add_trace(go.Scatter(
                x=d['ano'], y=d['qtd'],
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

    # ABA 4 — PERFIL DAS DEMANDAS
    with aba4:
        st.markdown("""
        <div style='background: linear-gradient(135deg, rgba(9,105,218,0.06), rgba(9,105,218,0.03)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #0969DA;'>
            <span style='font-size: 0.78rem; color: #57606A;'>
                Perfil descritivo das ações judiciais trabalhistas — assuntos primários e classes processuais
                (Rito Ordinário, Sumaríssimo e Sumário) — variáveis relevantes para a análise da judicialização.
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Seção 1: Assuntos Primários ──
        st.markdown("### Assuntos Primários")
        col_a, col_b = st.columns(2)

        with col_a:
            if 'assunto_primario_nome' in df_f.columns:
                df_ass = df_f['assunto_primario_nome'].value_counts().head(15).reset_index()
                df_ass.columns = ['assunto','qtd']
                df_ass['pct'] = (df_ass['qtd'] / df_ass['qtd'].sum() * 100).round(1)
                df_ass['label'] = df_ass['assunto'].str[:45] + df_ass['assunto'].apply(lambda x: '…' if len(x)>45 else '')

                fig_ass = go.Figure(go.Bar(
                    x=df_ass['qtd'],
                    y=df_ass['label'],
                    orientation='h',
                    marker=dict(color=COR_ROXO, opacity=0.85),
                    text=df_ass['qtd'].apply(lambda v: f"{v:,}".replace(",",".")),
                    textposition='outside',
                    textfont=dict(size=10, color="#1F2328"),
                    hovertemplate="<b>%{y}</b><br>%{x:,} processos<extra></extra>",
                ))
                fig_ass.update_layout(**layout_plotly("Top 15 Assuntos Primários"))
                fig_ass.update_layout(height=520)
                fig_ass.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_ass, use_container_width=True)

        with col_b:
            if 'assunto_primario_nome' in df_f.columns:
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
                        line=dict(color='#FFFFFF', width=2),
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
                        font=dict(size=14, color="#1F2328", family="Sora"),
                    )],
                )
                st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("---")

        # Assuntos ao longo do tempo (Top 5)
        if 'assunto_primario_nome' in df_f.columns:
            top5_ass = df_f['assunto_primario_nome'].value_counts().head(5).index.tolist()
            df_ass_tempo = (
                df_f[df_f['assunto_primario_nome'].isin(top5_ass)]
                .groupby(['ano','assunto_primario_nome']).size()
                .reset_index(name='qtd')
            )
            fig_ass_t = px.area(
                df_ass_tempo, x='ano', y='qtd',
                color='assunto_primario_nome',
                color_discrete_sequence=[COR_PRIMARIA, COR_ROXO, COR_CIANO, COR_LARANJA, COR_SECUNDARIA],
            )
            fig_ass_t.update_layout(**layout_plotly("Evolução Temporal dos Top 5 Assuntos"))
            fig_ass_t.update_xaxes(tickmode='linear', dtick=1)
            fig_ass_t.update_traces(line_width=1.5)
            st.plotly_chart(fig_ass_t, use_container_width=True)

        st.markdown("---")

        # ── Seção 2: Classes Processuais (Ritos) ──
        if 'classe_nome' in df_f.columns:
            st.markdown("### Classes Processuais (Ritos)")
            st.caption("A classificação por rito (Ordinário, Sumaríssimo, Sumário) indica o tipo de procedimento e o valor/complexidade da causa.")

            col_c1, col_c2 = st.columns(2)

            with col_c1:
                df_classe = df_f['classe_nome'].value_counts().reset_index()
                df_classe.columns = ['classe', 'qtd']
                df_classe['pct'] = (df_classe['qtd'] / df_classe['qtd'].sum() * 100).round(1)

                cores_classe = [COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_ROXO, COR_CIANO]
                fig_classe = go.Figure(go.Bar(
                    x=df_classe['classe'],
                    y=df_classe['qtd'],
                    marker=dict(color=cores_classe[:len(df_classe)]),
                    text=df_classe.apply(lambda r: f"{r['qtd']:,} ({r['pct']}%)".replace(",","."), axis=1),
                    textposition='outside',
                    textfont=dict(size=11, color="#1F2328"),
                    hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
                ))
                fig_classe.update_layout(**layout_plotly("Volume por Classe Processual"))
                fig_classe.update_layout(height=400)
                st.plotly_chart(fig_classe, use_container_width=True)

            with col_c2:
                fig_classe_pie = go.Figure(go.Pie(
                    labels=df_classe['classe'].str.replace('Ação Trabalhista - ', '', regex=False),
                    values=df_classe['qtd'],
                    hole=0.55,
                    marker=dict(
                        colors=cores_classe[:len(df_classe)],
                        line=dict(color='#FFFFFF', width=2),
                    ),
                    hovertemplate="<b>%{label}</b><br>%{value:,}<br>%{percent}<extra></extra>",
                    textinfo='label+percent',
                    textfont=dict(size=11),
                ))
                fig_classe_pie.update_layout(**layout_plotly("Composição por Rito"))
                fig_classe_pie.update_layout(height=400)
                st.plotly_chart(fig_classe_pie, use_container_width=True)

            # Evolução por classe ao longo do tempo
            df_classe_tempo = df_f.groupby(['ano', 'classe_nome']).size().reset_index(name='qtd')
            fig_classe_t = px.bar(
                df_classe_tempo, x='ano', y='qtd', color='classe_nome',
                barmode='stack',
                color_discrete_sequence=[COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_ROXO],
                labels={'classe_nome': 'Classe', 'ano': 'Ano', 'qtd': 'Processos'},
            )
            fig_classe_t.update_layout(**layout_plotly("Evolução das Classes Processuais por Ano"))
            fig_classe_t.update_xaxes(tickmode='linear', dtick=1)
            st.plotly_chart(fig_classe_t, use_container_width=True)



    # ABA 5 — ESTRUTURA JUDICIAL
    with aba5:
        st.markdown("""
        <div style='background: linear-gradient(135deg, rgba(9,105,218,0.06), rgba(9,105,218,0.03)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #0969DA;'>
            <span style='font-size: 0.78rem; color: #57606A;'>
                Estrutura dos órgãos julgadores da Justiça do Trabalho no RN — distribuição de processos
                por vara, formato e sistema processual.
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Seção 1: Distribuição por Órgão Julgador (Varas) ──
        st.markdown("### Órgãos Julgadores (Varas do Trabalho)")

        if 'orgaoJulgador_nome' in df_f.columns:
            col_a, col_b = st.columns([3, 2])

            with col_a:
                df_vara = df_f['orgaoJulgador_nome'].value_counts().reset_index()
                df_vara.columns = ['vara', 'qtd']
                df_vara['pct'] = (df_vara['qtd'] / df_vara['qtd'].sum() * 100).round(1)
                df_vara_top = df_vara.head(20)

                fig_vara = go.Figure(go.Bar(
                    x=df_vara_top['qtd'],
                    y=df_vara_top['vara'],
                    orientation='h',
                    marker=dict(
                        color=df_vara_top['qtd'],
                        colorscale=[[0,'#BDDDF5'],[0.5,'#0969DA'],[1,'#0550AE']],
                        showscale=False,
                    ),
                    text=df_vara_top.apply(lambda r: f"{r['qtd']:,} ({r['pct']}%)".replace(",","."), axis=1),
                    textposition='outside',
                    textfont=dict(size=10, color="#1F2328"),
                    hovertemplate="<b>%{y}</b><br>%{x:,} processos<extra></extra>",
                ))
                fig_vara.update_layout(**layout_plotly("Ranking de Varas do Trabalho por Volume"))
                fig_vara.update_layout(height=550)
                fig_vara.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_vara, use_container_width=True)

            with col_b:
                # Donut por vara (top 10 + outros)
                df_vara_donut = df_vara.head(10).copy()
                outros_vara = df_vara.iloc[10:]['qtd'].sum() if len(df_vara) > 10 else 0
                if outros_vara > 0:
                    df_vara_donut = pd.concat([df_vara_donut, pd.DataFrame({'vara':['Demais varas'],'qtd':[outros_vara],'pct':[0]})], ignore_index=True)
                df_vara_donut['label'] = df_vara_donut['vara'].str.replace('Vara do Trabalho de ', '', regex=False).str.replace('ª Vara do Trabalho de ', 'ª VT ', regex=False)

                fig_vara_pie = go.Figure(go.Pie(
                    labels=df_vara_donut['label'],
                    values=df_vara_donut['qtd'],
                    hole=0.5,
                    marker=dict(
                        colors=[COR_PRIMARIA, COR_ROXO, COR_CIANO, COR_LARANJA, COR_SECUNDARIA,
                                 COR_ALERTA, COR_PERIGO, "#E879F9", "#94A3B8", "#F0ABFC", "#6B7280"],
                        line=dict(color='#FFFFFF', width=2),
                    ),
                    hovertemplate="<b>%{label}</b><br>%{value:,}<br>%{percent}<extra></extra>",
                    textinfo='percent',
                    textfont=dict(size=10),
                ))
                fig_vara_pie.update_layout(**layout_plotly("Distribuição por Vara"))
                fig_vara_pie.update_layout(
                    height=550,
                    annotations=[dict(
                        text=f"<b>{df_f['orgaoJulgador_nome'].nunique()}</b><br>varas",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=14, color="#1F2328", family="Sora"),
                    )],
                )
                st.plotly_chart(fig_vara_pie, use_container_width=True)

            st.markdown("---")

            # Evolução das top 10 varas ao longo do tempo
            top10_varas = df_f['orgaoJulgador_nome'].value_counts().head(10).index.tolist()
            df_vara_evo = (
                df_f[df_f['orgaoJulgador_nome'].isin(top10_varas)]
                .groupby(['ano','orgaoJulgador_nome']).size()
                .reset_index(name='qtd')
            )
            df_vara_evo['label'] = df_vara_evo['orgaoJulgador_nome'].str.replace('Vara do Trabalho de ', '', regex=False).str.replace('ª Vara do Trabalho de ', 'ª VT ', regex=False)

            cores_varas = [COR_PRIMARIA, COR_ROXO, COR_CIANO, COR_LARANJA,
                           COR_SECUNDARIA, COR_ALERTA, COR_PERIGO, "#E879F9", "#94A3B8", "#F0ABFC"]
            fig_vara_evo = go.Figure()
            for i, v in enumerate(top10_varas):
                d = df_vara_evo[df_vara_evo['orgaoJulgador_nome'] == v]
                label = d['label'].iloc[0] if not d.empty else v
                fig_vara_evo.add_trace(go.Scatter(
                    x=d['ano'], y=d['qtd'],
                    mode='lines+markers',
                    name=label,
                    line=dict(color=cores_varas[i % len(cores_varas)], width=2),
                    marker=dict(size=5),
                    hovertemplate=f"<b>{label}</b><br>%{{x}}: %{{y:,}} processos<extra></extra>",
                ))
            fig_vara_evo.update_layout(**layout_plotly("Evolução das 10 Maiores Varas"))
            fig_vara_evo.update_xaxes(tickmode='linear', dtick=1)
            st.plotly_chart(fig_vara_evo, use_container_width=True)

        st.markdown("---")

        # ── Seção 2: Resumo por Sistema (informação secundária) ──
        st.markdown("### Sistema Processual")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
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
                textfont=dict(size=11, color="#1F2328"),
                hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
            ))
            fig_sis.update_layout(**layout_plotly("Volume por Sistema"))
            st.plotly_chart(fig_sis, use_container_width=True)

        with col_s2:
            df_sis_ano = df_f.groupby(['ano','sistema_nome']).size().reset_index(name='qtd')
            fig_sis_area = px.bar(
                df_sis_ano, x='ano', y='qtd', color='sistema_nome',
                barmode='stack',
                color_discrete_sequence=[COR_PRIMARIA, COR_SECUNDARIA, COR_ALERTA, COR_ROXO, COR_CIANO, COR_LARANJA],
            )
            fig_sis_area.update_layout(**layout_plotly("Composição por Sistema por Ano"))
            fig_sis_area.update_xaxes(tickmode='linear', dtick=1)
            st.plotly_chart(fig_sis_area, use_container_width=True)

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
            st.markdown("** Distribuição de Valor da Causa (R$)**")
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                df_val = df_f['valor_causa'].dropna()
                p95 = df_val.quantile(0.95)
                df_val_clip = df_val[df_val <= p95]
                fig_hist = go.Figure(go.Histogram(
                    x=df_val_clip,
                    nbinsx=50,
                    marker=dict(color=COR_CIANO, opacity=0.8, line=dict(color='#FFFFFF', width=0.5)),
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
                    textfont=dict(size=10, color="#1F2328"),
                    hovertemplate="<b>%{y}</b><br>Mediana: R$ %{x:,.0f}<extra></extra>",
                ))
                fig_vc.update_layout(**layout_plotly("Mediana do Valor da Causa por Sistema"))
                st.plotly_chart(fig_vc, use_container_width=True)


    # ═══════════ ABA 6: EXPLORAR DADOS ═══════════
    with aba6:
        st.markdown("** Pesquisa e Exportação**")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            filtro_comarca_exp = st.selectbox("Comarca", options=["Todas"] + comarcas_disp, key="ulisses_exp_comarca")
        with col_s2:
            filtro_ano_exp = st.selectbox("Ano", options=["Todos"] + [str(a) for a in anos_disp], key="ulisses_exp_ano")
        with col_s3:
            filtro_sistema_exp = st.selectbox("Sistema", options=["Todos"] + sistemas_disp, key="ulisses_exp_sistema")

        df_exp = df_f.copy()
        if filtro_comarca_exp != "Todas":
            df_exp = df_exp[df_exp['municipio_comarca'] == filtro_comarca_exp]
        if filtro_ano_exp != "Todos":
            df_exp = df_exp[df_exp['ano'] == int(filtro_ano_exp)]
        if filtro_sistema_exp != "Todos":
            df_exp = df_exp[df_exp['sistema_nome'] == filtro_sistema_exp]

        st.markdown(f"**{fmt_num(len(df_exp))} registros encontrados**")

        col_ord1, col_ord2 = st.columns([3,1])
        with col_ord1:
            col_sort = st.selectbox("Ordenar por", options=df_exp.columns.tolist(), index=0, key="ulisses_sort")
        with col_ord2:
            ordem_asc = st.radio("Ordem", ["↑ Crescente", "↓ Decrescente"], horizontal=True, key="ulisses_ordem") == "↑ Crescente"

        df_exp_sorted = df_exp.sort_values(col_sort, ascending=ordem_asc)
        st.dataframe(df_exp_sorted.head(1000), use_container_width=True, height=450)

        from datetime import datetime
        csv = df_exp_sorted.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label=" Baixar CSV (filtrado)",
            data=csv,
            file_name=f"processos_trt21_ulisses_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime='text/csv',
            use_container_width=True,
            key="ulisses_download",
        )

    # ═══════════ ABA 7: LISTA DE ASSUNTOS ═══════════
    with aba7:
        import re as _re

        st.markdown("""
        <div style='background: linear-gradient(135deg, rgba(130,80,223,0.06), rgba(9,105,218,0.03)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #8250DF;'>
            <span style='font-size: 0.78rem; color: #57606A;'>
                Lista completa de todos os assuntos encontrados nos processos. Cada processo pode conter multiplos
                assuntos separados por <code>|</code> na coluna <code>assuntos_str</code>. A aba <b>Dados Originais</b>
                mostra os dados brutos; a aba <b>Dados Consolidados</b> aplica normalizacao (resolve N/A via
                codigo, unifica assuntos duplicados e corrige variacoes ortograficas).
            </span>
        </div>
        """, unsafe_allow_html=True)

        if 'assuntos_str' in df_f.columns:
            # Explodir: original e consolidada
            df_ass_orig = explodir_assuntos(df_f, consolidar=False)
            df_ass_cons = explodir_assuntos(df_f, consolidar=True)

            if df_ass_orig.empty:
                st.warning("Nenhum assunto encontrado nos dados filtrados.")
            else:
                # KPIs de impacto da consolidacao
                stats = gerar_estatisticas_consolidacao(df_ass_orig, df_ass_cons)
                ka1, ka2, ka3, ka4 = st.columns(4)
                ka1.metric("Mencoes Totais", fmt_num(stats['mencoes_orig']))
                ka2.metric("Assuntos Originais", fmt_num(stats['assuntos_orig']))
                ka3.metric("Assuntos Consolidados", fmt_num(stats['assuntos_cons']),
                           delta=f"-{stats['reducao_assuntos']}", delta_color="normal")
                ka4.metric("N/A Resolvidos", fmt_num(stats['na_resolvidos']),
                           delta=f"{stats['na_cons']} restantes", delta_color="off")

                st.markdown("---")

                # Sub-abas: Original vs Consolidada
                sub7a, sub7b = st.tabs(["Dados Originais", "Dados Consolidados"])

                # Filtro de busca (compartilhado)
                busca = st.text_input("Buscar assunto", placeholder="Digite para filtrar...", key="ulisses_busca_assunto")

                # === SUB-ABA: DADOS ORIGINAIS ===
                with sub7a:
                    df_tab_orig = (
                        df_ass_orig
                        .groupby(['codigo', 'assunto'])
                        .agg(Freq=('assunto', 'count'), Comarcas=('comarca', 'nunique'), Anos=('ano', 'nunique'))
                        .reset_index()
                        .sort_values('Freq', ascending=False)
                        .reset_index(drop=True)
                    )
                    df_tab_orig.index += 1
                    df_tab_orig['%'] = (df_tab_orig['Freq'] / df_tab_orig['Freq'].sum() * 100).round(2)
                    df_tab_orig = df_tab_orig[['codigo', 'assunto', 'Freq', '%', 'Comarcas', 'Anos']]
                    df_tab_orig.columns = ['Codigo', 'Assunto', 'Ocorrencias', '% do Total', 'Comarcas', 'Anos']

                    if busca:
                        df_tab_orig = df_tab_orig[df_tab_orig['Assunto'].str.contains(busca, case=False, na=False)]

                    st.markdown(f"**{fmt_num(len(df_tab_orig))} assuntos** (dados brutos, sem tratamento)")
                    st.dataframe(df_tab_orig, use_container_width=True, height=500, hide_index=False)

                    from datetime import datetime as _dt
                    csv_orig = df_tab_orig.to_csv(index=True, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="Baixar dados originais (CSV)",
                        data=csv_orig,
                        file_name=f"assuntos_originais_{_dt.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime='text/csv',
                        use_container_width=True,
                        key="ulisses_download_assuntos_orig",
                    )

                # === SUB-ABA: DADOS CONSOLIDADOS ===
                with sub7b:
                    df_tab_cons = (
                        df_ass_cons
                        .groupby('assunto')
                        .agg(
                            Freq=('assunto', 'count'),
                            Codigos=('codigo', lambda x: ', '.join(str(c) for c in sorted(x.unique()))),
                            N_Codigos=('codigo', 'nunique'),
                            Comarcas=('comarca', 'nunique'),
                            Anos=('ano', 'nunique'),
                        )
                        .reset_index()
                        .sort_values('Freq', ascending=False)
                        .reset_index(drop=True)
                    )
                    df_tab_cons.index += 1
                    df_tab_cons['%'] = (df_tab_cons['Freq'] / df_tab_cons['Freq'].sum() * 100).round(2)
                    df_tab_cons = df_tab_cons[['assunto', 'Freq', '%', 'N_Codigos', 'Codigos', 'Comarcas', 'Anos']]
                    df_tab_cons.columns = ['Assunto', 'Ocorrencias', '% do Total', 'Codigos Unificados', 'Codigos', 'Comarcas', 'Anos']

                    if busca:
                        df_tab_cons = df_tab_cons[df_tab_cons['Assunto'].str.contains(busca, case=False, na=False)]

                    st.markdown(f"**{fmt_num(len(df_tab_cons))} assuntos** (consolidados: N/A resolvidos, similares unificados)")

                    # Highlight: assuntos que foram unificados (mais de 1 codigo)
                    st.dataframe(df_tab_cons, use_container_width=True, height=500, hide_index=False)

                    # Info sobre consolidacao
                    with st.expander("Detalhes da consolidacao aplicada"):
                        st.markdown(f"""
**Etapas de normalizacao:**

1. **Resolucao de N/A** ({stats['na_resolvidos']} registros corrigidos): quando um codigo
   aparece com nome real em alguns registros e como "N/A" em outros, o nome real e adotado.

2. **Unificacao de similares** ({stats['reducao_assuntos']} assuntos reduzidos): variacoes
   ortograficas (ex: "Adicional de Hora Extra" e "Adicional de Horas Extras") sao mapeadas
   para a forma canonica.

3. **Agrupamento por nome**: assuntos com nomes identicos mas codigos diferentes sao
   contabilizados juntos (coluna "Codigos Unificados" mostra quantos codigos foram agrupados).
                        """)

                    csv_cons = df_tab_cons.to_csv(index=True, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="Baixar dados consolidados (CSV)",
                        data=csv_cons,
                        file_name=f"assuntos_consolidados_{_dt.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime='text/csv',
                        use_container_width=True,
                        key="ulisses_download_assuntos_cons",
                    )
        else:
            st.warning("Coluna 'assuntos_str' nao encontrada nos dados.")

    # ═══════════ ABA 8: EVOLUÇÃO DE ASSUNTOS ═══════════
    with aba8:
        import re as _re8

        st.markdown("""
        <div style='background: linear-gradient(135deg, rgba(9,105,218,0.06), rgba(130,80,223,0.04)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #0969DA;'>
            <span style='font-size: 0.78rem; color: #57606A;'>
                Analise da evolucao temporal dos assuntos processuais agrupados por <b>semestre</b>.
                Selecione os assuntos de interesse para visualizar tendencias, picos e vales ao longo do periodo 2020-2024.
                Os dados utilizam a base <b>consolidada</b> (assuntos normalizados e N/A resolvidos).
            </span>
        </div>
        """, unsafe_allow_html=True)

        if 'assuntos_str' not in df_f.columns or 'dataAjuizamento' not in df_f.columns:
            st.warning("Colunas necessarias ('assuntos_str', 'dataAjuizamento') nao encontradas.")
        else:
            # Usar funcao centralizada com consolidacao
            df_exp_sem = explodir_assuntos(df_f, consolidar=True)

            if df_exp_sem.empty:
                st.warning("Nenhum assunto encontrado nos dados filtrados.")
            else:
                # ── Tabela de frequências ──
                freq_total = df_exp_sem['assunto'].value_counts().reset_index()
                freq_total.columns = ['Assunto', 'Frequência']
                freq_total['%'] = (freq_total['Frequência'] / freq_total['Frequência'].sum() * 100).round(2)

                # ── KPIs ──
                kk1, kk2, kk3, kk4 = st.columns(4)
                kk1.metric("Total de Menções", fmt_num(len(df_exp_sem)))
                kk2.metric("Assuntos Únicos", fmt_num(df_exp_sem['assunto'].nunique()))
                semestres_unicos = sorted(df_exp_sem['semestre'].unique())
                kk3.metric("Semestres", len(semestres_unicos))
                kk4.metric("Período", f"{semestres_unicos[0]} a {semestres_unicos[-1]}")

                st.markdown("---")

                # ── Filtro de assuntos ──
                top_assuntos_list = freq_total['Assunto'].head(30).tolist()
                assuntos_evo_sel = st.multiselect(
                    " Selecione os assuntos para análise",
                    options=freq_total['Assunto'].tolist(),
                    default=top_assuntos_list[:5],
                    key="ulisses_evo_assuntos",
                    help="Selecione um ou mais assuntos para visualizar a evolução semestral",
                )

                if not assuntos_evo_sel:
                    st.info("Selecione ao menos um assunto acima para visualizar a análise.")
                else:
                    # ── Tabela de frequências dos selecionados ──
                    with st.expander(" Tabela de Frequências", expanded=False):
                        df_freq_sel = freq_total[freq_total['Assunto'].isin(assuntos_evo_sel)].reset_index(drop=True)
                        df_freq_sel.index += 1
                        st.dataframe(df_freq_sel, use_container_width=True, hide_index=False)

                    # ── Preparar dados semestrais ──
                    df_sem = (
                        df_exp_sem[df_exp_sem['assunto'].isin(assuntos_evo_sel)]
                        .groupby(['assunto', 'semestre']).size()
                        .reset_index(name='qtd')
                    )
                    # Garantir todos os semestres para cada assunto
                    idx = pd.MultiIndex.from_product(
                        [assuntos_evo_sel, semestres_unicos],
                        names=['assunto', 'semestre']
                    )
                    df_sem = df_sem.set_index(['assunto', 'semestre']).reindex(idx, fill_value=0).reset_index()

                    # ── Detecção de picos e vales ──
                    def _detectar_picos_vales(valores):
                        """Detecta picos e vales em série curta por comparação com vizinhos."""
                        picos, vales = [], []
                        n = len(valores)
                        if n < 3:
                            return picos, vales
                        for i in range(n):
                            v = valores[i]
                            esq = valores[i - 1] if i > 0 else float('-inf')
                            dir_ = valores[i + 1] if i < n - 1 else float('-inf')
                            if v > esq and v > dir_:
                                picos.append(i)
                            esq_v = valores[i - 1] if i > 0 else float('inf')
                            dir_v = valores[i + 1] if i < n - 1 else float('inf')
                            if v < esq_v and v < dir_v:
                                vales.append(i)
                        return picos, vales

                    # ═══ GRÁFICO 1: Evolução Semestral (linhas) ═══
                    st.markdown("### Evolução Semestral por Assunto")
                    fig_evo = go.Figure()
                    for i, assunto in enumerate(assuntos_evo_sel):
                        d = df_sem[df_sem['assunto'] == assunto].sort_values('semestre')
                        cor_linha = CORES_MULTI[i % len(CORES_MULTI)]
                        valores = d['qtd'].tolist()
                        sems = d['semestre'].tolist()
                        picos, vales = _detectar_picos_vales(valores)

                        # Linha principal
                        fig_evo.add_trace(go.Scatter(
                            x=sems, y=valores,
                            mode='lines+markers',
                            name=assunto[:40],
                            line=dict(color=cor_linha, width=2.5),
                            marker=dict(size=7, color=cor_linha, line=dict(color='#FFFFFF', width=1.5)),
                            hovertemplate=f"<b>{assunto[:40]}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
                        ))
                        # Marcadores de picos
                        if picos:
                            fig_evo.add_trace(go.Scatter(
                                x=[sems[p] for p in picos], y=[valores[p] for p in picos],
                                mode='markers+text',
                                marker=dict(symbol='triangle-up', size=14, color=COR_SECUNDARIA, line=dict(color='#FFFFFF', width=1)),
                                text=[f"▲ {fmt_num(valores[p])}" for p in picos],
                                textposition='top center', textfont=dict(size=9, color=COR_SECUNDARIA),
                                showlegend=False,
                                hovertemplate=f"<b>PICO — {assunto[:30]}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
                            ))
                        # Marcadores de vales
                        if vales:
                            fig_evo.add_trace(go.Scatter(
                                x=[sems[v] for v in vales], y=[valores[v] for v in vales],
                                mode='markers+text',
                                marker=dict(symbol='triangle-down', size=14, color=COR_PERIGO, line=dict(color='#FFFFFF', width=1)),
                                text=[f"▼ {fmt_num(valores[v])}" for v in vales],
                                textposition='bottom center', textfont=dict(size=9, color=COR_PERIGO),
                                showlegend=False,
                                hovertemplate=f"<b>VALE — {assunto[:30]}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
                            ))

                    fig_evo.update_layout(**layout_plotly("Evolução Semestral dos Assuntos Selecionados"))
                    fig_evo.update_layout(height=500, xaxis_tickangle=45)
                    st.plotly_chart(fig_evo, use_container_width=True)

                    # ═══ GRÁFICO 2: Heatmap Semestral ═══
                    st.markdown("### Heatmap — Intensidade por Semestre")
                    df_heat_pivot = df_sem.pivot(index='assunto', columns='semestre', values='qtd').fillna(0)
                    # Ordenar por total
                    df_heat_pivot['_total'] = df_heat_pivot.sum(axis=1)
                    df_heat_pivot = df_heat_pivot.sort_values('_total', ascending=True).drop(columns='_total')
                    # Labels truncados
                    labels_y = [a[:35] + ('…' if len(a) > 35 else '') for a in df_heat_pivot.index]

                    fig_heat = go.Figure(go.Heatmap(
                        z=df_heat_pivot.values,
                        x=[str(c) for c in df_heat_pivot.columns],
                        y=labels_y,
                        colorscale=[[0, '#F0F4F8'], [0.3, '#BDDDF5'], [0.6, '#4BA0DC'], [1, '#0550AE']],
                        hovertemplate="<b>%{y}</b><br>%{x}: %{z:,.0f} menções<extra></extra>",
                        showscale=True,
                        colorbar=dict(tickfont=dict(color='#57606A', size=10), outlinewidth=0),
                        text=df_heat_pivot.values.astype(int),
                        texttemplate='%{text:,}',
                        textfont=dict(size=9, color='#1F2328'),
                    ))
                    h_heat = max(350, len(assuntos_evo_sel) * 35 + 100)
                    fig_heat.update_layout(**layout_plotly("Volume de Menções por Assunto × Semestre"))
                    fig_heat.update_layout(height=h_heat, margin=dict(l=200))
                    st.plotly_chart(fig_heat, use_container_width=True)

                    # ═══ GRÁFICO 3: Variação % Semestral ═══
                    st.markdown("### Variação Percentual entre Semestres")
                    var_rows = []
                    for assunto in assuntos_evo_sel:
                        d = df_sem[df_sem['assunto'] == assunto].sort_values('semestre')
                        vals = d['qtd'].tolist()
                        sems = d['semestre'].tolist()
                        for j in range(1, len(vals)):
                            prev = vals[j - 1]
                            delta = ((vals[j] - prev) / prev * 100) if prev > 0 else 0
                            var_rows.append({'assunto': assunto, 'semestre': sems[j], 'variacao': round(delta, 1)})
                    df_var = pd.DataFrame(var_rows)

                    if not df_var.empty:
                        # Se muitos assuntos, mostrar barras agrupadas
                        fig_var = go.Figure()
                        for i, assunto in enumerate(assuntos_evo_sel):
                            dv = df_var[df_var['assunto'] == assunto]
                            cores_var = [COR_SECUNDARIA if v >= 0 else COR_PERIGO for v in dv['variacao']]
                            fig_var.add_trace(go.Bar(
                                x=dv['semestre'], y=dv['variacao'],
                                name=assunto[:35],
                                marker_color=CORES_MULTI[i % len(CORES_MULTI)],
                                text=dv['variacao'].apply(lambda v: f"{v:+.1f}%"),
                                textposition='outside', textfont=dict(size=8, color='#1F2328'),
                                hovertemplate=f"<b>{assunto[:35]}</b><br>%{{x}}: %{{y:+.1f}}%<extra></extra>",
                            ))
                        fig_var.update_layout(**layout_plotly("Variação (%) entre Semestres Consecutivos"))
                        fig_var.update_layout(height=450, barmode='group', xaxis_tickangle=45)
                        fig_var.add_hline(y=0, line_dash='dash', line_color='#D0D7DE')
                        st.plotly_chart(fig_var, use_container_width=True)

                    # ═══ RESUMO ESTATÍSTICO ═══
                    st.markdown("### Resumo Estatístico")
                    resumo_rows = []
                    for assunto in assuntos_evo_sel:
                        d = df_sem[df_sem['assunto'] == assunto].sort_values('semestre')
                        vals = d['qtd'].tolist()
                        sems = d['semestre'].tolist()
                        picos, vales = _detectar_picos_vales(vals)
                        tendencia = 'Crescente ↑' if len(vals) >= 2 and vals[-1] > vals[0] else ('Decrescente ↓' if len(vals) >= 2 and vals[-1] < vals[0] else 'Estável →')
                        var_total = ((vals[-1] - vals[0]) / vals[0] * 100) if vals[0] > 0 and len(vals) >= 2 else 0
                        resumo_rows.append({
                            'Assunto': assunto[:45],
                            'Total': sum(vals),
                            'Média Sem.': round(np.mean(vals), 1),
                            'Máximo': max(vals),
                            'Sem. Pico': sems[vals.index(max(vals))],
                            'Mínimo': min(vals),
                            'Sem. Vale': sems[vals.index(min(vals))],
                            'Tendência': tendencia,
                            'Var. Total (%)': f"{var_total:+.1f}%",
                            'Picos': len(picos),
                            'Vales': len(vales),
                        })
                    df_resumo = pd.DataFrame(resumo_rows)
                    st.dataframe(df_resumo, use_container_width=True, hide_index=True)

                    # ═══ EXPORTAR PDF ═══
                    st.markdown("---")
                    st.markdown("### Exportar Relatório PDF")
                    st.markdown("Gere um relatório PDF completo com todos os gráficos e análises dos assuntos selecionados.")

                    if st.button(" Gerar Relatório PDF", key="ulisses_gerar_pdf", use_container_width=True, type="primary"):
                        try:
                            from gerar_relatorio_assuntos import gerar_relatorio_pdf
                            import tempfile, os
                            with st.spinner("Gerando relatório PDF..."):
                                tmp_dir = tempfile.mkdtemp()
                                pdf_path = os.path.join(tmp_dir, "relatorio_assuntos_trt21_ulisses.pdf")
                                gerar_relatorio_pdf(assuntos_evo_sel, df_f, pdf_path)
                                with open(pdf_path, 'rb') as f:
                                    pdf_bytes = f.read()
                            st.success(f" Relatório gerado com sucesso! ({len(pdf_bytes)//1024} KB)")
                            from datetime import datetime as _dt2
                            st.download_button(
                                label=" Baixar Relatório PDF",
                                data=pdf_bytes,
                                file_name=f"relatorio_assuntos_trt21_{_dt2.now().strftime('%Y%m%d_%H%M')}.pdf",
                                mime='application/pdf',
                                use_container_width=True,
                                key="ulisses_download_pdf",
                            )
                        except Exception as e:
                            st.error(f"Erro ao gerar PDF: {e}")

    # ═══════════ ABA 9: SAÚDE DO TRABALHADOR ═══════════
    with aba9:
        import re as _re9

        st.markdown("""
        <div style='background: linear-gradient(135deg, rgba(207,34,46,0.06), rgba(9,105,218,0.03)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #CF222E;'>
            <span style='font-size: 0.78rem; color: #57606A;'>
                Analise focada em processos relacionados a <b>saude do trabalhador</b>: acidentes de trabalho,
                doencas ocupacionais, insalubridade, periculosidade, assedio, danos morais/materiais/esteticos e outros.
                Os dados sao filtrados automaticamente a partir dos assuntos processuais da base consolidada.
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Codigos e nomes de assuntos relacionados a saude do trabalhador
        _CODIGOS_SAUDE = {
            13875, 13877, 13885, 13889, 13782,  # Insalubridade/Periculosidade
            14016, 14012, 14048,                  # Acidente de trabalho
            14024, 14014,                          # Doenca ocupacional
            14010, 14033,                          # Dano moral
            14009, 14032,                          # Dano material
            14008,                                 # Dano estetico
            14011,                                 # Dano moral coletivo
            14018, 14019,                          # Assedio moral/sexual
            13390,                                 # Dano moral/material
            13963,                                 # Morte
            13853, 13605,                          # Plano de saude
            12612,                                 # COVID-19
            12871,                                 # Licenca saude
        }

        _PATTERN_SAUDE = r'sa[uú]de|doen[cç]a|acidente|insalubr|periculosid|dano|ass[eé]dio|morte|[oó]bito|les[aã]o|incapac|COVID'

        if 'assuntos_str' in df_f.columns:
            # Explodir assuntos e filtrar os de saude
            df_saude_exp = explodir_assuntos(df_f, consolidar=True)

            if not df_saude_exp.empty:
                mask_saude = (
                    df_saude_exp['codigo'].isin(_CODIGOS_SAUDE) |
                    df_saude_exp['assunto'].str.contains(_PATTERN_SAUDE, case=False, regex=True, na=False)
                )
                df_saude = df_saude_exp[mask_saude].copy()
                df_todos = df_saude_exp.copy()

                # KPIs
                total_saude = len(df_saude)
                total_geral = len(df_todos)
                pct_saude = round(total_saude / total_geral * 100, 1) if total_geral > 0 else 0
                assuntos_saude_unicos = df_saude['assunto'].nunique()

                ks1, ks2, ks3, ks4 = st.columns(4)
                ks1.metric("Mencoes de Saude", fmt_num(total_saude))
                ks2.metric("% do Total", f"{pct_saude}%")
                ks3.metric("Assuntos de Saude", fmt_num(assuntos_saude_unicos))
                ks4.metric("Comarcas Afetadas", fmt_num(df_saude['comarca'].nunique()))

                st.markdown("---")

                # Ranking de assuntos de saude
                col_rank, col_chart = st.columns([1, 2])

                with col_rank:
                    st.markdown("**Ranking de Assuntos de Saude**")
                    df_rank_saude = (
                        df_saude.groupby('assunto')
                        .agg(Freq=('assunto', 'count'), Comarcas=('comarca', 'nunique'))
                        .reset_index()
                        .sort_values('Freq', ascending=False)
                        .reset_index(drop=True)
                    )
                    df_rank_saude.index += 1
                    df_rank_saude['%'] = (df_rank_saude['Freq'] / df_rank_saude['Freq'].sum() * 100).round(1)
                    df_rank_saude.columns = ['Assunto', 'Ocorrencias', 'Comarcas', '%']
                    st.dataframe(df_rank_saude[['Assunto', 'Ocorrencias', '%', 'Comarcas']],
                                 use_container_width=True, height=400)

                with col_chart:
                    df_bar_saude = df_rank_saude.head(12).sort_values('Ocorrencias', ascending=True)
                    fig_bar_s = go.Figure(go.Bar(
                        x=df_bar_saude['Ocorrencias'],
                        y=df_bar_saude['Assunto'].apply(lambda a: a[:35]),
                        orientation='h',
                        marker=dict(
                            color=df_bar_saude['Ocorrencias'],
                            colorscale=[[0, '#FFCDD2'], [1, '#CF222E']],
                            showscale=False,
                        ),
                        text=df_bar_saude['Ocorrencias'].apply(lambda v: fmt_num(v)),
                        textposition='outside',
                        textfont=dict(size=10, color='#1F2328'),
                        hovertemplate="<b>%{y}</b><br>%{x:,} mencoes<extra></extra>",
                    ))
                    fig_bar_s.update_layout(**layout_plotly("Top 12 Assuntos de Saude do Trabalhador"))
                    fig_bar_s.update_layout(height=400)
                    st.plotly_chart(fig_bar_s, use_container_width=True)

                st.markdown("---")

                # Evolucao temporal
                st.markdown("### Evolucao Temporal — Saude do Trabalhador")

                if 'semestre' in df_saude.columns:
                    df_evo_saude = df_saude.groupby('semestre').size().reset_index(name='qtd')
                    df_evo_saude = df_evo_saude.sort_values('semestre')

                    fig_evo_s = go.Figure()
                    fig_evo_s.add_trace(go.Scatter(
                        x=df_evo_saude['semestre'], y=df_evo_saude['qtd'],
                        mode='lines+markers+text',
                        line=dict(color='#CF222E', width=3),
                        marker=dict(size=8, color='#CF222E'),
                        text=df_evo_saude['qtd'].apply(lambda v: fmt_num(v)),
                        textposition='top center',
                        textfont=dict(size=9, color='#57606A'),
                        hovertemplate="<b>%{x}</b><br>%{y:,} mencoes<extra></extra>",
                        fill='tozeroy',
                        fillcolor='rgba(207,34,46,0.08)',
                    ))
                    fig_evo_s.update_layout(**layout_plotly("Volume Semestral de Assuntos de Saude"))
                    fig_evo_s.update_layout(height=400)
                    st.plotly_chart(fig_evo_s, use_container_width=True)

                # Top 5 assuntos de saude por semestre
                st.markdown("### Evolucao dos 5 Principais Assuntos")
                top5_saude = df_saude['assunto'].value_counts().head(5).index.tolist()

                if 'semestre' in df_saude.columns and top5_saude:
                    df_top5_sem = (
                        df_saude[df_saude['assunto'].isin(top5_saude)]
                        .groupby(['semestre', 'assunto']).size()
                        .reset_index(name='qtd')
                    )
                    cores_saude = ['#CF222E', '#E16F24', '#8250DF', '#0969DA', '#1A7F37']
                    fig_top5 = go.Figure()
                    for i, ass in enumerate(top5_saude):
                        d = df_top5_sem[df_top5_sem['assunto'] == ass].sort_values('semestre')
                        fig_top5.add_trace(go.Scatter(
                            x=d['semestre'], y=d['qtd'],
                            mode='lines+markers',
                            name=ass[:35],
                            line=dict(color=cores_saude[i], width=2.5),
                            marker=dict(size=6),
                            hovertemplate=f"<b>{ass[:35]}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
                        ))
                    fig_top5.update_layout(**layout_plotly("Evolucao Semestral — Top 5 Saude"))
                    fig_top5.update_layout(height=420)
                    st.plotly_chart(fig_top5, use_container_width=True)

                # Distribuicao por comarca
                st.markdown("---")
                st.markdown("### Distribuicao Geografica — Saude do Trabalhador")
                col_com_s, col_donut_s = st.columns([2, 1])

                with col_com_s:
                    df_com_saude = df_saude.groupby('comarca').size().reset_index(name='qtd')
                    df_com_saude = df_com_saude.sort_values('qtd', ascending=True).tail(10)
                    fig_com_s = go.Figure(go.Bar(
                        x=df_com_saude['qtd'],
                        y=df_com_saude['comarca'],
                        orientation='h',
                        marker=dict(color='#CF222E'),
                        text=df_com_saude['qtd'].apply(lambda v: fmt_num(v)),
                        textposition='outside',
                        textfont=dict(size=10),
                        hovertemplate="<b>%{y}</b><br>%{x:,} mencoes<extra></extra>",
                    ))
                    fig_com_s.update_layout(**layout_plotly("Top 10 Comarcas — Saude"))
                    fig_com_s.update_layout(height=380)
                    st.plotly_chart(fig_com_s, use_container_width=True)

                with col_donut_s:
                    # Donut: categorias de saude
                    categorias = {
                        'Insalubridade/Periculosidade': ['Adicional de Insalubridade', 'Adicional de Periculosidade',
                                                          'Outros Agentes Insalubres', 'Cumulação com Adicional de Insalubridade',
                                                          'Compensação em Atividade Insalubre'],
                        'Acidente/Doença': ['Acidente de Trabalho', 'Acidente de trabalho', 'Doença Ocupacional', 'COVID-19'],
                        'Danos': ['Indenização por Dano Moral', 'Indenização por Dano Material',
                                  'Indenização por Dano Estético', 'Indenização por Dano Moral Coletivo',
                                  'Dano Moral / Material'],
                        'Assédio': ['Assédio Moral', 'Assédio Sexual'],
                        'Outros': ['Morte', 'Plano de Saúde', 'Licença Saúde'],
                    }
                    cat_vals = []
                    for cat, nomes in categorias.items():
                        total_cat = df_saude[df_saude['assunto'].isin(nomes)]['assunto'].count()
                        cat_vals.append({'Categoria': cat, 'Total': total_cat})
                    df_cat = pd.DataFrame(cat_vals)
                    df_cat = df_cat[df_cat['Total'] > 0].sort_values('Total', ascending=False)

                    fig_donut_s = go.Figure(go.Pie(
                        labels=df_cat['Categoria'],
                        values=df_cat['Total'],
                        hole=0.5,
                        marker=dict(colors=['#CF222E', '#E16F24', '#8250DF', '#0969DA', '#57606A']),
                        textinfo='label+percent',
                        textfont=dict(size=11),
                        hovertemplate="<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>",
                    ))
                    fig_donut_s.update_layout(**layout_plotly("Categorias de Saude"))
                    fig_donut_s.update_layout(height=380, showlegend=False)
                    st.plotly_chart(fig_donut_s, use_container_width=True)
            else:
                st.warning("Nenhum dado de assuntos encontrado.")
        else:
            st.warning("Coluna 'assuntos_str' nao encontrada.")

    # ═══════════ ABA 10: RITOS PROCESSUAIS ═══════════
    with aba10:
        st.markdown("""
        <div style='background: linear-gradient(135deg, rgba(26,127,55,0.06), rgba(9,105,218,0.03)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #1A7F37;'>
            <span style='font-size: 0.78rem; color: #57606A;'>
                Analise da distribuicao processual por <b>rito</b> (Sumarissimo, Ordinario, Sumario).
                A variavel <code>rito</code> e derivada de <code>classe_nome</code>, preservando a coluna original.
            </span>
        </div>
        """, unsafe_allow_html=True)

        if 'rito' in df_f.columns:
            # KPIs
            rito_counts = df_f['rito'].value_counts()
            kr1, kr2, kr3 = st.columns(3)
            kr1.metric("Rito Sumarissimo", fmt_num(rito_counts.get('Rito Sumaríssimo', 0)),
                       delta=f"{round(rito_counts.get('Rito Sumaríssimo', 0) / len(df_f) * 100, 1)}%",
                       delta_color="off")
            kr2.metric("Rito Ordinario", fmt_num(rito_counts.get('Rito Ordinário', 0)),
                       delta=f"{round(rito_counts.get('Rito Ordinário', 0) / len(df_f) * 100, 1)}%",
                       delta_color="off")
            kr3.metric("Rito Sumario", fmt_num(rito_counts.get('Rito Sumário', 0)),
                       delta=f"{round(rito_counts.get('Rito Sumário', 0) / len(df_f) * 100, 1)}%",
                       delta_color="off")

            st.markdown("---")

            col_rito1, col_rito2 = st.columns([1, 1])

            with col_rito1:
                # Donut
                df_rito = rito_counts.reset_index()
                df_rito.columns = ['Rito', 'Quantidade']
                cores_rito = {'Rito Sumaríssimo': '#1A7F37', 'Rito Ordinário': '#0969DA', 'Rito Sumário': '#E16F24', 'Outro': '#D0D7DE'}
                fig_rito_donut = go.Figure(go.Pie(
                    labels=df_rito['Rito'],
                    values=df_rito['Quantidade'],
                    hole=0.5,
                    marker=dict(colors=[cores_rito.get(r, '#D0D7DE') for r in df_rito['Rito']]),
                    textinfo='label+percent',
                    textfont=dict(size=12),
                    hovertemplate="<b>%{label}</b><br>%{value:,} processos (%{percent})<extra></extra>",
                ))
                fig_rito_donut.update_layout(**layout_plotly("Distribuicao por Rito"))
                fig_rito_donut.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_rito_donut, use_container_width=True)

            with col_rito2:
                # Evolucao temporal
                df_rito_evo = df_f.groupby(['ano', 'rito']).size().reset_index(name='qtd')
                fig_rito_evo = go.Figure()
                for rito_nome in sorted(df_rito_evo['rito'].unique()):
                    d = df_rito_evo[df_rito_evo['rito'] == rito_nome].sort_values('ano')
                    cor = cores_rito.get(rito_nome, '#D0D7DE')
                    fig_rito_evo.add_trace(go.Scatter(
                        x=d['ano'], y=d['qtd'],
                        mode='lines+markers',
                        name=rito_nome,
                        line=dict(color=cor, width=2.5),
                        marker=dict(size=7, color=cor),
                        hovertemplate=f"<b>{rito_nome}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
                    ))
                fig_rito_evo.update_layout(**layout_plotly("Evolucao Anual por Rito"))
                fig_rito_evo.update_layout(height=400)
                fig_rito_evo.update_xaxes(tickmode='linear', dtick=1)
                st.plotly_chart(fig_rito_evo, use_container_width=True)

            st.markdown("---")

            # Rito por comarca
            st.markdown("### Distribuicao por Comarca")
            df_rito_com = df_f.groupby(['municipio_comarca', 'rito']).size().reset_index(name='qtd')
            df_rito_com_total = df_rito_com.groupby('municipio_comarca')['qtd'].sum().nlargest(10).index
            df_rito_com_top = df_rito_com[df_rito_com['municipio_comarca'].isin(df_rito_com_total)]

            fig_rito_bar = px.bar(
                df_rito_com_top.sort_values(['municipio_comarca', 'qtd']),
                x='qtd', y='municipio_comarca', color='rito',
                orientation='h',
                color_discrete_map=cores_rito,
                labels={'qtd': 'Processos', 'municipio_comarca': 'Comarca', 'rito': 'Rito'},
            )
            fig_rito_bar.update_layout(**layout_plotly("Ritos nas 10 Maiores Comarcas"))
            fig_rito_bar.update_layout(height=420, barmode='stack')
            fig_rito_bar.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(fig_rito_bar, use_container_width=True)

            # Tabela comparativa por rito
            st.markdown("---")
            st.markdown("### Tabela Comparativa — Dados Originais e Derivados")
            sub_tab_r1, sub_tab_r2 = st.tabs(["Classe Original", "Rito Derivado"])

            with sub_tab_r1:
                if 'classe_nome' in df_f.columns:
                    df_classe_orig = df_f['classe_nome'].value_counts().reset_index()
                    df_classe_orig.columns = ['Classe Processual (Original)', 'Quantidade']
                    df_classe_orig['%'] = (df_classe_orig['Quantidade'] / df_classe_orig['Quantidade'].sum() * 100).round(1)
                    df_classe_orig.index += 1
                    st.dataframe(df_classe_orig, use_container_width=True)

            with sub_tab_r2:
                df_rito_tab = rito_counts.reset_index()
                df_rito_tab.columns = ['Rito (Derivado)', 'Quantidade']
                df_rito_tab['%'] = (df_rito_tab['Quantidade'] / df_rito_tab['Quantidade'].sum() * 100).round(1)
                df_rito_tab.index += 1
                st.dataframe(df_rito_tab, use_container_width=True)
        else:
            st.info("Coluna 'rito' nao encontrada. Verifique se o data_loader esta atualizado.")

    # ═══════════ ABA 11: NOTAS TÉCNICAS ═══════════
    with aba11:
        st.markdown("""
        <div style='background: linear-gradient(135deg, rgba(87,96,106,0.06), rgba(9,105,218,0.03)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #57606A;'>
            <span style='font-size: 0.78rem; color: #57606A;'>
                Documentacao das decisoes metodologicas aplicadas ao tratamento dos dados.
                Todas as transformacoes, limpezas e derivacoes estao registradas abaixo para
                garantir <b>transparencia</b> e <b>reprodutibilidade</b> da analise.
            </span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 1. Fonte dos Dados")
        st.markdown("""
| Item | Descricao |
|------|-----------|
| **Origem** | Base de dados do TRT21 (21a Regiao — Rio Grande do Norte) |
| **Periodo** | 2020 a 2024 |
| **Arquivos** | `trt21_2020_capa.xlsx` a `trt21_2024_capa.xlsx` |
| **Tipo** | Dados de capa processual (metadados) |
| **Total de registros** | ~78.353 processos |
| **Sistema** | PJe (Processo Judicial Eletronico) |
        """)

        st.markdown("---")
        st.markdown("### 2. Variaveis Derivadas")
        st.markdown("""
As seguintes variaveis **nao existem nos dados originais** e foram criadas durante o processamento:

| Variavel | Origem | Logica de Derivacao |
|----------|--------|---------------------|
| `municipio_comarca` | `orgaoJulgador_nome` | Regex extrai cidade apos "Vara do Trabalho de". Gabinetes → "Tribunal (2a Instancia)". |
| `assunto_primario_nome` | `assuntos_str` | Primeiro assunto da lista separada por `\\|`, removendo o codigo numerico. |
| `rito` | `classe_nome` | Extrai o tipo de rito (Sumarissimo, Ordinario, Sumario) da classe processual. A coluna `classe_nome` original e **preservada intacta**. |
| `ano`, `mes`, `trimestre`, `mes_ano` | `dataAjuizamento` | Decomposicao da data de ajuizamento em componentes temporais. |
        """)

        st.markdown("---")
        st.markdown("### 3. Normalizacao de Assuntos")
        st.markdown("""
A base original apresenta inconsistencias nos assuntos processuais. Aplicamos 3 etapas de normalizacao
(modulo `normalizacao_assuntos.py`), preservando os dados originais na aba "Lista de Assuntos > Dados Originais":

**Etapa 1 — Resolucao de "N/A":** Muitos codigos aparecem com o nome "N/A" em alguns registros e com
nome real em outros. Quando um codigo possui nome real em pelo menos 1 registro, todos os "N/A" daquele
codigo sao substituidos pelo nome real.

**Etapa 2 — Unificacao de similares:** Variacoes ortograficas sao mapeadas para a forma canonica. Exemplos:
- "Adicional de Hora Extra" → "Adicional de Horas Extras"
- "Complementacao de Aposentadoria / Pensao" → "Complementacao de Aposentadoria/Pensao"
- "Supressao/Reducao de Horas Extras Habituais - Indenizacao" → "Supressao/Reducao de Horas Extras/Indenizacao"

**Etapa 3 — Agrupamento por nome:** Assuntos com nomes identicos mas codigos diferentes sao contabilizados juntos.
        """)

        st.markdown("---")
        st.markdown("### 4. Saude do Trabalhador — Criterios de Filtro")
        st.markdown("""
A aba "Saude do Trabalhador" filtra processos com base em **dois criterios combinados** (OR):

1. **Por codigo:** Codigos especificos pre-mapeados (insalubridade, acidente, doenca ocupacional, danos, assedio, etc.)
2. **Por nome:** Regex que captura termos como: saude, doenca, acidente, insalubr, periculosid, dano, assedio, morte, COVID, etc.

**Categorias identificadas:**
- Insalubridade/Periculosidade (adicional, cumulacao, compensacao)
- Acidente de Trabalho e Doenca Ocupacional
- Danos (moral, material, estetico, coletivo)
- Assedio (moral e sexual)
- Outros (morte, plano de saude, COVID-19)
        """)

        st.markdown("---")
        st.markdown("### 5. Dados Socioeconomicos do Mapa")
        st.markdown("""
| Indicador | Fonte | Atualizacao |
|-----------|-------|-------------|
| **Populacao** | API IBGE (Tabela 6579) | Estimativa mais recente disponivel |
| **PIB per capita** | API IBGE (Tabela 5938) | Calculado: PIB total * 1000 / Populacao |
| **Area territorial** | API IBGE (Tabela 1301) | Dados oficiais |
| **IDHM** | Atlas Brasil / PNUD | **Censo 2010** (ultimo disponivel em nivel municipal) |

> **Nota sobre o IDHM:** O Indice de Desenvolvimento Humano Municipal (IDHM) utilizado e proveniente
> do Censo Demografico de 2010, que e a **unica fonte publica de IDHM em nivel municipal** disponivel
> no Brasil. O Censo 2022 ainda nao publicou IDHM municipalizado. Quando disponibilizado, os dados
> serao atualizados. Os valores estao armazenados estaticamente no modulo `dados_ibge_rn.py`.
        """)

        st.markdown("---")
        st.markdown("### 6. Estrutura de Varas Trabalhistas")
        st.markdown("""
O mapeamento de municipios para varas trabalhistas segue o arquivo oficial
`TRT21 - Pagina1 (1).csv`, que define a jurisdicao de cada uma das **9 varas** do RN.
Todos os 167 municipios do estado estao mapeados.
        """)

        st.markdown("---")
        st.caption("Ultima atualizacao das notas tecnicas: Junho/2025 · Observatorio dos Direitos Sociais do Semiarido · UFERSA")
