import streamlit as st
import pandas as pd
import plotly.express as px
import glob

# 1. Configuração da página
st.set_page_config(page_title="Jurimetria TRT21 - Série Histórica", layout="wide")

# 2. Carregar TODOS os ficheiros Parquet da pasta
@st.cache_data
def carregar_dados_todos_anos():
    # Procura todos os ficheiros Parquet enriquecidos na sua pasta
    arquivos_parquet = glob.glob("processos_trt21_enriquecido_*.parquet")
    
    if not arquivos_parquet:
        st.error("Nenhum ficheiro Parquet encontrado na pasta. Verifique se foram gerados no R.")
        return pd.DataFrame()

    # Lê cada ficheiro e junta todos numa única lista
    lista_tabelas = [pd.read_parquet(arquivo) for arquivo in arquivos_parquet]
    
    # Empilha todas as tabelas numa só (Concatenação)
    df_completo = pd.concat(lista_tabelas, ignore_index=True)
    
    # Recria a coluna de ano extraindo-a diretamente da data otimizada
    df_completo['ano_extracao'] = df_completo['dataajuizamento_dt'].dt.year
    
    return df_completo

df = carregar_dados_todos_anos()

# Se o DataFrame não estiver vazio, constrói o painel
if not df.empty:
    
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros de Pesquisa")

    # Filtro por Ano
    anos_disponiveis = sorted(df['ano_extracao'].dropna().unique().tolist())
    anos_selecionados = st.sidebar.multiselect(
        "Selecione os Anos", 
        options=anos_disponiveis, 
        default=anos_disponiveis
    )

    # Filtro por Comarca
    comarcas = sorted(df['municipio_comarca'].dropna().unique().tolist())
    comarcas_selecionadas = st.sidebar.multiselect(
        "Selecione as Comarcas", 
        options=comarcas, 
        default=comarcas
    )
    
    # Filtro por Sistema (PJe, etc.)
    sistemas = sorted(df['sistema_nome'].dropna().unique().tolist())
    sistemas_selecionados = st.sidebar.multiselect(
        "Selecione os Sistemas", 
        options=sistemas, 
        default=sistemas
    )

    # Aplicar os filtros à tabela mestre
    df_filtrado = df[
        (df['ano_extracao'].isin(anos_selecionados)) & 
        (df['municipio_comarca'].isin(comarcas_selecionadas)) &
        (df['sistema_nome'].isin(sistemas_selecionados))
    ]

    # --- PAINEL PRINCIPAL ---
    st.title("📊 Painel de Jurimetria TRT21 (2020-2024)")
    st.markdown(f"Analisando um total de **{len(df_filtrado)}** processos no período selecionado.")

    # --- GRÁFICO DE LINHA DO TEMPO ---
    st.subheader("Evolução Histórica da Judicialização")
    # Agrupa por ano para ver a tendência
    df_tendencia = df_filtrado.groupby('ano_extracao').size().reset_index(name='quantidade_processos')
    
    fig_linha = px.line(
        df_tendencia, 
        x="ano_extracao", 
        y="quantidade_processos", 
        markers=True,
        title="Volume de Processos por Ano",
        labels={"ano_extracao": "Ano", "quantidade_processos": "Novos Processos"}
    )
    # Força o eixo X a mostrar apenas números inteiros (anos)
    fig_linha.update_layout(xaxis=dict(tickmode='linear', dtick=1))
    st.plotly_chart(fig_linha, use_container_width=True)

    # --- GRÁFICOS LATERAIS ---
    col1, col2 = st.columns(2)

    with col1:
        # Gráfico: Volume por Comarca
        df_vol = df_filtrado['municipio_comarca'].value_counts().reset_index()
        df_vol.columns = ['municipio_comarca', 'quantidade']
        fig_vol = px.bar(df_vol, x="municipio_comarca", y="quantidade", title="Acumulado por Comarca", text_auto=True)
        st.plotly_chart(fig_vol, use_container_width=True)

    with col2:
        # Gráfico: Distribuição por Sistema
        df_sis = df_filtrado['sistema_nome'].value_counts().reset_index()
        df_sis.columns = ['sistema_nome', 'quantidade']
        fig_sis = px.pie(df_sis, values="quantidade", names="sistema_nome", title="Proporção por Sistema")
        st.plotly_chart(fig_sis, use_container_width=True)

    # --- GRÁFICO DE ASSUNTOS (NOVO) ---
    st.subheader("Top 10 Assuntos Mais Recorrentes")
    
    # Conta os assuntos, agrupa e pega os 10 maiores
    df_assuntos = df_filtrado['assunto_primario_nome'].value_counts().reset_index()
    df_assuntos.columns = ['assunto_primario_nome', 'quantidade']
    df_assuntos_top10 = df_assuntos.head(10)

    fig_assuntos = px.bar(
        df_assuntos_top10, 
        x="quantidade", 
        y="assunto_primario_nome", 
        orientation='h', # Define como barra horizontal
        title="Principais Motivos de Ação Trabalhista",
        labels={"quantidade": "Número de Processos", "assunto_primario_nome": "Assunto Principal"},
        text_auto=True
    )
    # Inverte a ordem do eixo Y para o maior ficar no topo (padrão de leitura)
    fig_assuntos.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_assuntos, use_container_width=True)

    # --- TABELA DE DADOS COMPLETA ---
    st.subheader("📋 Base de Dados Consolidada")
    st.markdown("Navegue pela tabela completa com base nos filtros selecionados acima.")
    st.dataframe(df_filtrado, use_container_width=True)
