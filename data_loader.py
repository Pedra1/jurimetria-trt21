# ─────────────────────────────────────────────
# CARREGAMENTO DE DADOS — MULTI-TRIBUNAL
# ─────────────────────────────────────────────
import streamlit as st
import pandas as pd
import glob


@st.cache_data(show_spinner=False)
def carregar_trt21():
    arquivos = glob.glob("processos_trt21_enriquecido_*.parquet")
    if not arquivos:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)
    df['tribunal'] = 'TRT21'
    df['ano'] = df['dataajuizamento_dt'].dt.year
    df['mes'] = df['dataajuizamento_dt'].dt.month
    df['trimestre'] = df['dataajuizamento_dt'].dt.to_period('Q').astype(str)
    df['mes_ano'] = df['dataajuizamento_dt'].dt.to_period('M').astype(str)
    if 'valor_da_causa' in df.columns and 'valor_causa' not in df.columns:
        df['valor_causa'] = pd.to_numeric(df['valor_da_causa'], errors='coerce')
    elif 'valor_causa' in df.columns:
        df['valor_causa'] = pd.to_numeric(df['valor_causa'], errors='coerce')
    # Normalizar PJe/Pje/PJE → PJe
    if 'sistema_nome' in df.columns:
        df['sistema_nome'] = df['sistema_nome'].apply(
            lambda x: 'PJe' if isinstance(x, str) and x.upper() == 'PJE' else x
        )
    return df


@st.cache_data(show_spinner=False)
def carregar_tjrn():
    arquivos = glob.glob("processos_tjrn_saude_*.parquet")
    if not arquivos:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)
    df['tribunal'] = 'TJRN'
    df['ano'] = df['dataajuizamento_dt'].dt.year
    df['mes'] = df['dataajuizamento_dt'].dt.month
    df['trimestre'] = df['dataajuizamento_dt'].dt.to_period('Q').astype(str)
    df['mes_ano'] = df['dataajuizamento_dt'].dt.to_period('M').astype(str)
    if 'valor_da_causa' in df.columns and 'valor_causa' not in df.columns:
        df['valor_causa'] = pd.to_numeric(df['valor_da_causa'], errors='coerce')
    # Capitalizar municipio_comarca para consistência visual
    if 'municipio_comarca' in df.columns:
        df['municipio_comarca'] = df['municipio_comarca'].str.title()
    return df


@st.cache_data(show_spinner=False)
def carregar_jfrn():
    arquivos = glob.glob("processos_jfrn_saude_*.parquet")
    if not arquivos:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)
    df['tribunal'] = 'JFRN'
    df['ano'] = df['dataajuizamento_dt'].dt.year
    df['mes'] = df['dataajuizamento_dt'].dt.month
    df['trimestre'] = df['dataajuizamento_dt'].dt.to_period('Q').astype(str)
    df['mes_ano'] = df['dataajuizamento_dt'].dt.to_period('M').astype(str)
    if 'valor_da_causa' in df.columns and 'valor_causa' not in df.columns:
        df['valor_causa'] = pd.to_numeric(df['valor_da_causa'], errors='coerce')
    # Capitalizar municipio_comarca para consistência visual
    if 'municipio_comarca' in df.columns:
        df['municipio_comarca'] = df['municipio_comarca'].str.title()
    return df


@st.cache_data(show_spinner=False)
def carregar_trt21_ulisses():
    """Carrega os dados TRT21 dos arquivos XLSX 'capa' (base Ulisses)."""
    import re
    arquivos = glob.glob("trt21_*_capa.xlsx")
    if not arquivos:
        return pd.DataFrame()
    dfs = []
    for a in arquivos:
        dfs.append(pd.read_excel(a))
    df = pd.concat(dfs, ignore_index=True)
    df['tribunal'] = 'TRT21'

    # ── Data de ajuizamento ──
    if 'dataAjuizamento' in df.columns:
        df['dataAjuizamento'] = pd.to_datetime(df['dataAjuizamento'], errors='coerce')
        df['ano'] = df['dataAjuizamento'].dt.year
        df['mes'] = df['dataAjuizamento'].dt.month
        df['trimestre'] = df['dataAjuizamento'].dt.to_period('Q').astype(str)
        df['mes_ano'] = df['dataAjuizamento'].dt.to_period('M').astype(str)

    # ── Normalizar sistema_nome ──
    if 'sistema_nome' in df.columns:
        df['sistema_nome'] = df['sistema_nome'].apply(
            lambda x: 'PJe' if isinstance(x, str) and x.upper() == 'PJE' else x
        )

    # ── Derivar municipio_comarca a partir de orgaoJulgador_nome ──
    def _extrair_comarca(nome_vara: str) -> str:
        if not isinstance(nome_vara, str):
            return 'Desconhecido'
        # Ex: "1ª Vara do Trabalho de Natal" → "Natal"
        #     "Vara do Trabalho de Ceará Mirim" → "Ceará Mirim"
        #     "Gabinete do Desembargador..." → "Tribunal (2ª Instância)"
        m = re.search(r'Vara do Trabalho de\s+(.+)', nome_vara, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        if 'Gabinete' in nome_vara or 'Desembarg' in nome_vara:
            return 'Tribunal (2ª Instância)'
        return 'Outros'

    if 'orgaoJulgador_nome' in df.columns:
        df['municipio_comarca'] = df['orgaoJulgador_nome'].apply(_extrair_comarca)

    # ── Derivar assunto_primario_nome a partir de assuntos_str ──
    def _extrair_assunto_primario(assuntos: str) -> str:
        if not isinstance(assuntos, str) or not assuntos.strip():
            return 'Não informado'
        # Formato: "14000 - Multa do Artigo 477 da CLT | 13998 - Multa de 40% do FGTS"
        primeiro = assuntos.split('|')[0].strip()
        # Remove código numérico: "14000 - Multa..." → "Multa..."
        m = re.match(r'\d+\s*-\s*(.+)', primeiro)
        if m:
            return m.group(1).strip()
        return primeiro

    if 'assuntos_str' in df.columns:
        df['assunto_primario_nome'] = df['assuntos_str'].apply(_extrair_assunto_primario)

    return df


def carregar_todos():
    """Carrega e retorna dicionário com DataFrames de cada tribunal."""
    return {
        'TRT21': carregar_trt21(),
        'TRT21_ULISSES': carregar_trt21_ulisses(),
        'TJRN': carregar_tjrn(),
        'JFRN': carregar_jfrn(),
    }
