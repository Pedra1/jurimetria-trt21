# ─────────────────────────────────────────────
# SEÇÃO: TRT21 — JUSTIÇA DO TRABALHO
# ─────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import json
import urllib.request
from config import *

# ─────────────────────────────────────────────
# DICIONÁRIO GEOGRÁFICO — COMARCAS TRT21/RN
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


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip('#')
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


def render_trt21(df_raw: pd.DataFrame):
    """Renderiza seção completa do TRT21."""

    cor = CORES_TRIBUNAL["TRT21"]["primaria"]
    escala = CORES_TRIBUNAL["TRT21"]["escala"]

    st.caption("⚖️ Observatório dos Direitos Sociais do Semiárido · UFERSA")
    st.title("Judicialização dos Direitos Sociais no RN")
    st.markdown("Análise quantitativa da judicialização trabalhista · TRT 21ª Região · Rio Grande do Norte · 2020–2024")

    if df_raw.empty:
        st.warning("Nenhum dado disponível para TRT21.")
        return

    # ── Filtros na sidebar ──
    with st.sidebar:
        st.markdown("**📅 PERÍODO**")
        anos_disp = sorted(df_raw['ano'].dropna().unique().tolist())
        anos_sel = st.multiselect("Anos", options=anos_disp, default=anos_disp, label_visibility="collapsed", key="trt21_anos")

        st.markdown("**📍 COMARCA**")
        comarcas_disp = sorted(df_raw['municipio_comarca'].dropna().unique().tolist())
        comarcas_sel = st.multiselect("Comarcas", options=comarcas_disp, default=comarcas_disp, label_visibility="collapsed", key="trt21_comarcas")

        st.markdown("**💻 SISTEMA**")
        sistemas_disp = sorted(df_raw['sistema_nome'].dropna().unique().tolist())
        sistemas_sel = st.multiselect("Sistemas", options=sistemas_disp, default=sistemas_disp, label_visibility="collapsed", key="trt21_sistemas")

        if 'assunto_primario_nome' in df_raw.columns:
            st.markdown("**📂 ASSUNTO (Top 20)**")
            top_assuntos = df_raw['assunto_primario_nome'].value_counts().head(20).index.tolist()
            assuntos_sel = st.multiselect("Assuntos", options=top_assuntos, default=[], label_visibility="collapsed", key="trt21_assuntos")
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
    aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
        "📈  Evolução Temporal",
        "🗺️  Mapa Interativo",
        "📍  Distribuição Geográfica",
        "📂  Perfil das Demandas",
        "⚖️  Estrutura Judicial",
        "🔍  Explorar Dados",
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
                marker=dict(size=8, color=cor, line=dict(color="#0D1117", width=2)),
                fill='tozeroy', fillcolor='rgba(88,166,255,0.06)',
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
                textposition='outside', textfont=dict(size=10, color="#C9D1D9"),
                hovertemplate="<b>%{x}</b><br>Variação: %{y:.1f}%<extra></extra>",
            ))
            fig_delta.update_layout(**layout_plotly("Variação Anual (%)"))
            fig_delta.update_xaxes(tickmode='linear', dtick=1)
            fig_delta.add_hline(y=0, line_dash="dash", line_color="#21262D")
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
                colorscale=[[0,'#0D1117'],[0.3,'#1C3F80'],[0.7,'#388BFD'],[1,'#A5D3FF']],
                hovertemplate="<b>%{y} %{x}</b><br>%{z:.0f} processos<extra></extra>",
                showscale=True,
                colorbar=dict(tickfont=dict(color="#8B949E", size=10), outlinewidth=0, bgcolor="rgba(0,0,0,0)"),
            ))
            fig_heat.update_layout(**layout_plotly("Distribuição Mensal (Heatmap)"))
            st.plotly_chart(fig_heat, use_container_width=True)

        with col_d:
            if 'trimestre' in df_f.columns:
                df_trim = df_f.groupby('trimestre').size().reset_index(name='qtd').sort_values('trimestre').tail(20)
                fig_trim = go.Figure(go.Bar(
                    x=df_trim['trimestre'], y=df_trim['qtd'],
                    marker=dict(color=df_trim['qtd'], colorscale=[[0,'#1C3F80'],[1,'#58A6FF']], showscale=False),
                    hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
                ))
                fig_trim.update_layout(**layout_plotly("Evolução Trimestral"))
                fig_trim.update_xaxes(tickangle=45)
                st.plotly_chart(fig_trim, use_container_width=True)

        # ═══════════ ABA 2: MAPA INTERATIVO ═══════════
    with aba2:

        # ── Dados base: respeita ano e sistema, ignora filtro de comarca ──
        _mask_mapa = pd.Series([True] * len(df_raw), index=df_raw.index)
        if anos_sel:
            _mask_mapa &= df_raw['ano'].isin(anos_sel)
        if sistemas_sel:
            _mask_mapa &= df_raw['sistema_nome'].isin(sistemas_sel)
        df_mapa_base = df_raw[_mask_mapa].copy()

        # ── Recorte temporal interno do mapa ──
        anos_mapa_disp = ["Todos os anos"] + [str(a) for a in sorted(df_mapa_base['ano'].dropna().unique())]
        ano_mapa = st.selectbox("Recorte temporal", anos_mapa_disp, key="mapa_ano")

        if ano_mapa != "Todos os anos":
            df_fonte = df_mapa_base[df_mapa_base['ano'] == int(ano_mapa)]
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
                .groupby(['ano','municipio_comarca']).size()
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
                    x=d['ano'], y=d['qtd'],
                    mode='lines+markers',
                    name=c,
                    line=dict(color=cores_evo[i % len(cores_evo)], width=2),
                    marker=dict(size=5),
                    hovertemplate=f"<b>{c}</b><br>%{{x}}: %{{y:,}} processos<extra></extra>",
                ))
            fig_evo.update_layout(**layout_plotly("Evolução das 8 Maiores Comarcas"))
            fig_evo.update_xaxes(tickmode='linear', dtick=1)
            st.plotly_chart(fig_evo, use_container_width=True)


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
        <div style='background: linear-gradient(135deg, rgba(28,63,128,0.15), rgba(88,166,255,0.08)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #388BFD;'>
            <span style='font-size: 0.78rem; color: #8B949E;'>
                📋 Perfil descritivo das ações judiciais trabalhistas — assuntos primários e classes processuais
                (Rito Ordinário, Sumaríssimo e Sumário) — variáveis relevantes para a análise da judicialização.
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Seção 1: Assuntos Primários ──
        st.markdown("### 📂 Assuntos Primários")
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
                    textfont=dict(size=10, color="#C9D1D9"),
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
            st.markdown("### ⚖️ Classes Processuais (Ritos)")
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
                    textfont=dict(size=11, color="#C9D1D9"),
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
                        line=dict(color='#0D1117', width=2),
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
        <div style='background: linear-gradient(135deg, rgba(28,63,128,0.15), rgba(88,166,255,0.08)); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid #388BFD;'>
            <span style='font-size: 0.78rem; color: #8B949E;'>
                🏛️ Estrutura dos órgãos julgadores da Justiça do Trabalho no RN — distribuição de processos
                por vara, formato e sistema processual.
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Seção 1: Distribuição por Órgão Julgador (Varas) ──
        st.markdown("### 🏛️ Órgãos Julgadores (Varas do Trabalho)")

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
                        colorscale=[[0,'#1C3F80'],[0.5,'#388BFD'],[1,'#58A6FF']],
                        showscale=False,
                    ),
                    text=df_vara_top.apply(lambda r: f"{r['qtd']:,} ({r['pct']}%)".replace(",","."), axis=1),
                    textposition='outside',
                    textfont=dict(size=10, color="#C9D1D9"),
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
                        line=dict(color='#0D1117', width=2),
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
                        font=dict(size=14, color="#C9D1D9", family="Sora"),
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
        st.markdown("### 💻 Sistema Processual")

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
                textfont=dict(size=11, color="#C9D1D9"),
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


    # ═══════════ ABA 6: EXPLORAR DADOS ═══════════
    with aba6:
        st.markdown("**🔎 Pesquisa e Exportação**")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            filtro_comarca_exp = st.selectbox("Comarca", options=["Todas"] + comarcas_disp, key="trt21_exp_comarca")
        with col_s2:
            filtro_ano_exp = st.selectbox("Ano", options=["Todos"] + [str(a) for a in anos_disp], key="trt21_exp_ano")
        with col_s3:
            filtro_sistema_exp = st.selectbox("Sistema", options=["Todos"] + sistemas_disp, key="trt21_exp_sistema")

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
            col_sort = st.selectbox("Ordenar por", options=df_exp.columns.tolist(), index=0, key="trt21_sort")
        with col_ord2:
            ordem_asc = st.radio("Ordem", ["↑ Crescente", "↓ Decrescente"], horizontal=True, key="trt21_ordem") == "↑ Crescente"

        df_exp_sorted = df_exp.sort_values(col_sort, ascending=ordem_asc)
        st.dataframe(df_exp_sorted.head(1000), use_container_width=True, height=450)

        from datetime import datetime
        csv = df_exp_sorted.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="⬇️  Baixar CSV (filtrado)",
            data=csv,
            file_name=f"processos_trt21_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime='text/csv',
            use_container_width=True,
            key="trt21_download",
        )
