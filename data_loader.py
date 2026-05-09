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


def carregar_todos():
    """Carrega e retorna dicionário com DataFrames de cada tribunal."""
    return {
        'TRT21': carregar_trt21(),
        'TJRN': carregar_tjrn(),
        'JFRN': carregar_jfrn(),
    }
