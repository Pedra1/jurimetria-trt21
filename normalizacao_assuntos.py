# ─────────────────────────────────────────────
# MÓDULO: Normalização e Consolidação de Assuntos
# ─────────────────────────────────────────────
"""
Resolve inconsistências na base de assuntos do TRT21:
1. Códigos com nome "N/A" → substituídos pelo nome real (quando o mesmo código
   aparece em outro registro com nome real)
2. Mesmo nome com códigos diferentes → unificados pelo nome canônico
3. Nomes similares (variações ortográficas) → mapeados para forma canônica
"""
import re
import pandas as pd


# ═══════════════════════════════════════════════
#  MAPA DE SIMILARIDADE — assuntos quase-idênticos
#  (forma variante → forma canônica)
# ═══════════════════════════════════════════════
_MAPA_SIMILARIDADE = {
    # Variações de barra/hífen/espaço
    "Complementação de Aposentadoria / Pensão": "Complementação de Aposentadoria/Pensão",
    "Natureza Jurídica da Parcela - Repercussão": "Natureza Jurídica da Parcela/Repercussão",
    "Supressão/Redução de Horas Extras Habituais - Indenização": "Supressão/Redução de Horas Extras/Indenização",

    # Singular/plural e variações menores
    "Adicional de Hora Extra": "Adicional de Horas Extras",
    "Alteração Contratual": "Alteração Contratual ou das Condições de Trabalho",
    "Prescrição e Decadência": "Prescrição e Decadência no Direito do Trabalho",
    "Repouso Semanal Remunerado": "Repouso Semanal Remunerado e Feriado",
}


def _construir_mapa_codigo_para_nome(df_assuntos: pd.DataFrame) -> dict:
    """
    A partir de um DataFrame com colunas 'codigo' e 'assunto',
    constrói um mapa {codigo → nome_real} resolvendo entradas N/A.

    Lógica: para cada código, se existem registros com nome real (não N/A)
    E registros com N/A, usa o nome real mais frequente.
    """
    mapa = {}
    for codigo, grp in df_assuntos.groupby('codigo'):
        nomes = grp['assunto'].value_counts()
        nomes_reais = {n: c for n, c in nomes.items() if n != 'N/A' and n.strip()}
        if nomes_reais:
            # Usa o nome mais frequente (excluindo N/A)
            mapa[codigo] = max(nomes_reais, key=nomes_reais.get)
        elif 'N/A' in nomes.index:
            mapa[codigo] = 'N/A'
        else:
            mapa[codigo] = nomes.index[0] if len(nomes) > 0 else 'Desconhecido'
    return mapa


def normalizar_assunto(nome: str) -> str:
    """Aplica normalização de similaridade a um nome de assunto."""
    nome = nome.strip()
    return _MAPA_SIMILARIDADE.get(nome, nome)


def explodir_assuntos(df: pd.DataFrame, consolidar: bool = False) -> pd.DataFrame:
    """
    Explode a coluna 'assuntos_str' em linhas individuais.

    Args:
        df: DataFrame com colunas 'assuntos_str', 'ano', 'municipio_comarca'
            e opcionalmente 'dataAjuizamento'
        consolidar: Se True, aplica normalização (resolve N/A, unifica similares)

    Returns:
        DataFrame com colunas: codigo, assunto, ano, comarca
        (e 'semestre' se 'dataAjuizamento' existir)
    """
    tem_data = 'dataAjuizamento' in df.columns
    cols = ['assuntos_str', 'ano', 'municipio_comarca']
    if tem_data:
        cols.append('dataAjuizamento')

    rows = []
    for _, row in df[cols].iterrows():
        if not isinstance(row['assuntos_str'], str) or not row['assuntos_str'].strip():
            continue
        sem = None
        if tem_data and pd.notna(row['dataAjuizamento']):
            dt = row['dataAjuizamento']
            sem = f"{int(row['ano'])}-S{'1' if dt.month <= 6 else '2'}"

        for parte in row['assuntos_str'].split('|'):
            parte = parte.strip()
            if not parte:
                continue
            m = re.match(r'(\d+)\s*-\s*(.+)', parte)
            if m:
                codigo = int(m.group(1))
                nome = m.group(2).strip()
            else:
                codigo = 0
                nome = parte

            entry = {
                'codigo': codigo,
                'assunto': nome,
                'ano': row['ano'],
                'comarca': row['municipio_comarca'],
            }
            if tem_data:
                entry['semestre'] = sem
            rows.append(entry)

    df_result = pd.DataFrame(rows)

    if consolidar and not df_result.empty:
        df_result = _consolidar_assuntos(df_result)

    return df_result


def _consolidar_assuntos(df_ass: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica 3 etapas de consolidação:
    1. Resolve N/A usando mapa código → nome
    2. Unifica códigos diferentes com mesmo nome
    3. Aplica mapa de similaridade
    """
    # Etapa 1: Resolver N/A via mapa código → nome
    mapa_cod_nome = _construir_mapa_codigo_para_nome(df_ass)
    mask_na = df_ass['assunto'] == 'N/A'
    if mask_na.any():
        df_ass.loc[mask_na, 'assunto'] = df_ass.loc[mask_na, 'codigo'].map(
            lambda c: mapa_cod_nome.get(c, 'N/A')
        )

    # Etapa 2: Aplicar mapa de similaridade
    df_ass['assunto'] = df_ass['assunto'].apply(normalizar_assunto)

    # Etapa 3: Para assuntos com mesmo nome mas códigos diferentes,
    # manter o nome unificado (o agrupamento posterior fará o resto)

    return df_ass


def gerar_estatisticas_consolidacao(df_original: pd.DataFrame, df_consolidado: pd.DataFrame) -> dict:
    """Calcula estatísticas de impacto da consolidação."""
    return {
        'mencoes_orig': len(df_original),
        'mencoes_cons': len(df_consolidado),
        'assuntos_orig': df_original['assunto'].nunique(),
        'assuntos_cons': df_consolidado['assunto'].nunique(),
        'codigos_orig': df_original['codigo'].nunique(),
        'na_orig': (df_original['assunto'] == 'N/A').sum(),
        'na_cons': (df_consolidado['assunto'] == 'N/A').sum(),
        'na_resolvidos': (df_original['assunto'] == 'N/A').sum() - (df_consolidado['assunto'] == 'N/A').sum(),
        'reducao_assuntos': df_original['assunto'].nunique() - df_consolidado['assunto'].nunique(),
    }
