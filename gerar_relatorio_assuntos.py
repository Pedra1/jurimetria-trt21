# -*- coding: utf-8 -*-
"""
Gerador de Relatório PDF — Evolução dos Assuntos Processuais (TRT 21ª Região)

Gera um relatório em PDF com qualidade de publicação, contendo:
  - Capa com resumo geral
  - Tabela de frequência dos assuntos selecionados
  - Gráfico de evolução semestral (todos os assuntos sobrepostos)
  - Heatmap de assuntos × semestres
  - Páginas individuais por assunto (linha + variação %)

Tema: Claro / Acadêmico (fundo branco)

Dependências: pandas, matplotlib, glob, re, os
Todos os textos em Português (Brasil).
"""

import glob
import os
import re
from datetime import datetime

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

# ──────────────────────────────────────────────
# Paleta e constantes de estilo (tema claro / acadêmico)
# ──────────────────────────────────────────────
_CORES_ASSUNTOS = [
    "#0969DA", "#8250DF", "#0598BC", "#BC4C00", "#1A7F37",
    "#9A6700", "#CF222E", "#BF3989", "#6E7781", "#D4A0D9",
]
_BG_FIGURA = "#FFFFFF"
_BG_EIXO = "#F6F8FA"
_COR_TITULO = "#1F2328"
_COR_ROTULO = "#57606A"
_COR_GRADE = "#D0D7DE"
_FONTE = "DejaVu Sans"
_DPI = 150
_TAM_FIGURA = (11.69, 8.27)  # A4 paisagem

# Cores do heatmap (claro → escuro em fundo branco)
_HEATMAP_CLARO = "#F0F4F8"
_HEATMAP_ESCURO = "#0969DA"


# ──────────────────────────────────────────────
# Funções auxiliares
# ──────────────────────────────────────────────

def _aplicar_tema_claro(fig, ax):
    """Aplica o tema claro/acadêmico padrão à figura e ao eixo."""
    fig.patch.set_facecolor(_BG_FIGURA)
    ax.set_facecolor(_BG_EIXO)
    ax.tick_params(colors=_COR_ROTULO, which="both")
    ax.xaxis.label.set_color(_COR_ROTULO)
    ax.yaxis.label.set_color(_COR_ROTULO)
    ax.title.set_color(_COR_TITULO)
    for spine in ax.spines.values():
        spine.set_color(_COR_GRADE)
    ax.grid(True, color=_COR_GRADE, linewidth=0.5, alpha=0.6)


def _semestre(dt):
    """Converte um datetime em rótulo de semestre: '2020-S1' ou '2020-S2'."""
    if pd.isna(dt):
        return None
    s = 1 if dt.month <= 6 else 2
    return f"{dt.year}-S{s}"


def _parsear_assuntos(texto):
    """
    Recebe string como '14000 - Multa do Art. 477 | 13998 - Multa de 40%'
    e devolve lista de tuplas (código, nome).
    """
    if pd.isna(texto) or not str(texto).strip():
        return []
    partes = str(texto).split("|")
    resultado = []
    padrao = re.compile(r"^\s*(\d+)\s*-\s*(.+?)\s*$")
    for p in partes:
        m = padrao.match(p)
        if m:
            resultado.append((m.group(1), m.group(2)))
        else:
            nome = p.strip()
            if nome:
                resultado.append(("", nome))
    return resultado


def _detectar_picos_vales(valores):
    """
    Detecta picos (▲) e vales (▼) por comparação simples com vizinhos.
    Retorna dois dicts {indice: valor}.
    """
    n = len(valores)
    picos = {}
    vales = {}
    if n == 0:
        return picos, vales
    if n == 1:
        return picos, vales
    for i in range(n):
        v = valores[i]
        if i == 0:
            if v > valores[i + 1]:
                picos[i] = v
            elif v < valores[i + 1]:
                vales[i] = v
        elif i == n - 1:
            if v > valores[i - 1]:
                picos[i] = v
            elif v < valores[i - 1]:
                vales[i] = v
        else:
            if v > valores[i - 1] and v > valores[i + 1]:
                picos[i] = v
            elif v < valores[i - 1] and v < valores[i + 1]:
                vales[i] = v
    return picos, vales


def _cor_assunto(indice):
    """Retorna a cor da paleta para um dado índice (cíclico)."""
    return _CORES_ASSUNTOS[indice % len(_CORES_ASSUNTOS)]


def _preparar_dados(df, assuntos_selecionados):
    """
    Prepara o DataFrame explodido e filtrado.
    Retorna (df_explodido, semestres_ordenados, contagens_pivot).
    """
    # Explodir assuntos
    registros = []
    for idx, row in df.iterrows():
        lista_assuntos = _parsear_assuntos(row.get("assuntos_str", ""))
        sem = _semestre(row.get("dataAjuizamento"))
        for codigo, nome in lista_assuntos:
            registros.append({
                "codigo_assunto": codigo,
                "assunto": nome,
                "semestre": sem,
            })

    df_exp = pd.DataFrame(registros)

    if df_exp.empty:
        return df_exp, [], pd.DataFrame()

    # Filtrar assuntos selecionados
    df_exp = df_exp[df_exp["assunto"].isin(assuntos_selecionados)].copy()

    if df_exp.empty:
        return df_exp, [], pd.DataFrame()

    # Ordenar semestres
    semestres_unicos = sorted(df_exp["semestre"].dropna().unique())

    # Pivot de contagens
    contagens = (
        df_exp.groupby(["assunto", "semestre"])
        .size()
        .reset_index(name="contagem")
    )
    pivot = contagens.pivot_table(
        index="assunto", columns="semestre", values="contagem", fill_value=0
    )
    # Reordenar colunas
    pivot = pivot.reindex(columns=semestres_unicos, fill_value=0)

    return df_exp, semestres_unicos, pivot


# ──────────────────────────────────────────────
# Páginas do relatório
# ──────────────────────────────────────────────

def _pagina_capa(pdf, total_processos, total_assuntos_analisados):
    """Página 1 — Capa do relatório."""
    fig, ax = plt.subplots(figsize=_TAM_FIGURA)
    fig.patch.set_facecolor(_BG_FIGURA)
    ax.set_facecolor(_BG_FIGURA)
    ax.axis("off")

    # Título principal
    fig.text(
        0.5, 0.68,
        "Relatório de Evolução dos\nAssuntos Processuais",
        ha="center", va="center",
        fontsize=32, fontweight="bold",
        color=_COR_TITULO, fontfamily=_FONTE,
    )
    # Subtítulo
    fig.text(
        0.5, 0.52,
        "TRT 21ª Região — Base Ulisses (2020–2024)",
        ha="center", va="center",
        fontsize=18, color="#0969DA", fontfamily=_FONTE,
    )
    # Data de geração
    data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")
    fig.text(
        0.5, 0.42,
        f"Gerado em {data_geracao}",
        ha="center", va="center",
        fontsize=13, color=_COR_ROTULO, fontfamily=_FONTE,
    )
    # Linha separadora decorativa
    fig.patches.append(
        plt.Rectangle(
            (0.25, 0.36), 0.50, 0.003,
            transform=fig.transFigure, facecolor="#0969DA",
            alpha=0.5, clip_on=False,
        )
    )
    # Estatísticas resumidas
    fig.text(
        0.5, 0.28,
        f"Total de processos na base: {total_processos:,}".replace(",", "."),
        ha="center", va="center",
        fontsize=14, color=_COR_TITULO, fontfamily=_FONTE,
    )
    fig.text(
        0.5, 0.22,
        f"Total de assuntos analisados: {total_assuntos_analisados}",
        ha="center", va="center",
        fontsize=14, color=_COR_TITULO, fontfamily=_FONTE,
    )

    pdf.savefig(fig, dpi=_DPI)
    plt.close(fig)


def _pagina_tabela_frequencia(pdf, pivot, total_ocorrencias):
    """Página 2 — Tabela de frequência dos assuntos selecionados."""
    fig, ax = plt.subplots(figsize=_TAM_FIGURA)
    _aplicar_tema_claro(fig, ax)
    ax.axis("off")
    ax.set_title(
        "Tabela de Frequência dos Assuntos Selecionados",
        fontsize=20, fontweight="bold", color=_COR_TITULO,
        fontfamily=_FONTE, pad=20,
    )

    # Calcular frequências
    freq = pivot.sum(axis=1).sort_values(ascending=False).astype(int)
    total_soma = freq.sum()

    # Dados da tabela
    dados_tabela = []
    for assunto, contagem in freq.items():
        perc = (contagem / total_soma * 100) if total_soma > 0 else 0
        dados_tabela.append([
            assunto,
            f"{contagem:,}".replace(",", "."),
            f"{perc:.1f}%",
        ])

    colunas = ["Assunto", "Frequência Absoluta", "% do Total"]

    # Cores alternadas (tema claro)
    n_linhas = len(dados_tabela)
    cores_celulas = []
    for i in range(n_linhas):
        cor_fundo = "#F6F8FA" if i % 2 == 0 else "#FFFFFF"
        cores_celulas.append([cor_fundo] * 3)

    tabela = ax.table(
        cellText=dados_tabela,
        colLabels=colunas,
        loc="center",
        cellLoc="center",
    )
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(10)

    # Estilizar cabeçalho
    for j in range(3):
        celula = tabela[0, j]
        celula.set_facecolor("#E8ECF0")
        celula.set_text_props(
            color=_COR_TITULO, fontweight="bold", fontfamily=_FONTE
        )
        celula.set_edgecolor(_COR_GRADE)

    # Estilizar dados
    for i in range(n_linhas):
        for j in range(3):
            celula = tabela[i + 1, j]
            celula.set_facecolor(cores_celulas[i][j])
            celula.set_text_props(color=_COR_ROTULO, fontfamily=_FONTE)
            celula.set_edgecolor(_COR_GRADE)
            if j == 0:  # Coluna Assunto alinhada à esquerda
                celula.set_text_props(
                    color=_COR_TITULO, fontfamily=_FONTE, ha="left"
                )

    # Ajustar larguras
    tabela.auto_set_column_width([0, 1, 2])
    tabela.scale(1.0, 1.8)

    fig.tight_layout(rect=[0.05, 0.05, 0.95, 0.92])
    pdf.savefig(fig, dpi=_DPI)
    plt.close(fig)


def _pagina_evolucao_geral(pdf, pivot, semestres):
    """Página 3 — Gráfico de evolução semestral (todos sobrepostos)."""
    fig, ax = plt.subplots(figsize=_TAM_FIGURA)
    _aplicar_tema_claro(fig, ax)

    ax.set_title(
        "Evolução Semestral dos Assuntos Selecionados",
        fontsize=18, fontweight="bold", color=_COR_TITULO,
        fontfamily=_FONTE, pad=15,
    )

    for i, (assunto, row) in enumerate(pivot.iterrows()):
        cor = _cor_assunto(i)
        valores = row.values.tolist()
        x = list(range(len(semestres)))

        ax.plot(x, valores, marker="o", color=cor, linewidth=2,
                markersize=6, label=assunto, zorder=3)

        # Picos e vales
        picos, vales = _detectar_picos_vales(valores)
        for idx_p, val_p in picos.items():
            ax.annotate(
                "▲", (x[idx_p], val_p),
                textcoords="offset points", xytext=(0, 10),
                fontsize=10, color=cor, ha="center", fontweight="bold",
            )
        for idx_v, val_v in vales.items():
            ax.annotate(
                "▼", (x[idx_v], val_v),
                textcoords="offset points", xytext=(0, -14),
                fontsize=10, color=cor, ha="center", fontweight="bold",
            )

    ax.set_xticks(range(len(semestres)))
    ax.set_xticklabels(semestres, rotation=45, ha="right", fontsize=9)
    ax.set_xlabel("Semestre", fontsize=12, fontfamily=_FONTE)
    ax.set_ylabel("Quantidade de Processos", fontsize=12, fontfamily=_FONTE)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    # Legenda fora do gráfico
    ax.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        fontsize=8, frameon=True, facecolor=_BG_FIGURA,
        edgecolor=_COR_GRADE, labelcolor=_COR_ROTULO,
    )

    fig.tight_layout(rect=[0.0, 0.05, 0.78, 0.95])
    pdf.savefig(fig, dpi=_DPI)
    plt.close(fig)


def _pagina_heatmap(pdf, pivot, semestres):
    """Página 4 — Heatmap de assuntos × semestres."""
    fig, ax = plt.subplots(figsize=_TAM_FIGURA)
    _aplicar_tema_claro(fig, ax)

    ax.set_title(
        "Mapa de Calor — Distribuição Semestral por Assunto",
        fontsize=18, fontweight="bold", color=_COR_TITULO,
        fontfamily=_FONTE, pad=15,
    )

    dados = pivot.values
    n_assuntos = dados.shape[0]
    n_semestres = dados.shape[1]

    # Colormap personalizado (claro → escuro para fundo branco)
    from matplotlib.colors import LinearSegmentedColormap
    cmap_custom = LinearSegmentedColormap.from_list(
        "heatmap_trt", [_HEATMAP_CLARO, _HEATMAP_ESCURO]
    )

    im = ax.imshow(dados, aspect="auto", cmap=cmap_custom, interpolation="nearest")

    # Eixos
    ax.set_xticks(range(n_semestres))
    ax.set_xticklabels(semestres, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(n_assuntos))

    # Truncar nomes longos para o eixo Y
    nomes_assuntos = list(pivot.index)
    nomes_truncados = [
        n if len(n) <= 45 else n[:42] + "..." for n in nomes_assuntos
    ]
    ax.set_yticklabels(nomes_truncados, fontsize=8, fontfamily=_FONTE)

    # Anotações com valores
    vmax = dados.max() if dados.max() > 0 else 1
    for i in range(n_assuntos):
        for j in range(n_semestres):
            valor = int(dados[i, j])
            cor_texto = "#FFFFFF" if dados[i, j] > vmax * 0.6 else _COR_TITULO
            ax.text(
                j, i, str(valor),
                ha="center", va="center",
                fontsize=9, color=cor_texto, fontfamily=_FONTE,
            )

    # Barra de cores
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.ax.tick_params(colors=_COR_ROTULO)
    cbar.outline.set_edgecolor(_COR_GRADE)

    fig.tight_layout(rect=[0.0, 0.05, 0.95, 0.95])
    pdf.savefig(fig, dpi=_DPI)
    plt.close(fig)


def _pagina_assunto_individual(pdf, assunto, semestres, valores, cor):
    """Páginas 5+ — Análise individual de cada assunto."""
    fig = plt.figure(figsize=_TAM_FIGURA)
    fig.patch.set_facecolor(_BG_FIGURA)

    # ── Gráfico de linha (parte superior) ──
    ax1 = fig.add_axes([0.08, 0.48, 0.84, 0.40])
    _aplicar_tema_claro(fig, ax1)

    # Truncar título se muito longo
    titulo_assunto = assunto if len(assunto) <= 70 else assunto[:67] + "..."
    ax1.set_title(
        titulo_assunto,
        fontsize=16, fontweight="bold", color=_COR_TITULO,
        fontfamily=_FONTE, pad=12,
    )

    x = list(range(len(semestres)))
    ax1.plot(x, valores, marker="o", color=cor, linewidth=2.5,
             markersize=8, zorder=3)
    ax1.fill_between(x, valores, alpha=0.10, color=cor)

    # Picos e vales anotados
    picos, vales = _detectar_picos_vales(valores)
    for idx_p, val_p in picos.items():
        ax1.annotate(
            f"▲ Pico: {val_p}",
            (x[idx_p], val_p),
            textcoords="offset points", xytext=(0, 14),
            fontsize=9, color="#1A7F37", ha="center",
            fontweight="bold", fontfamily=_FONTE,
        )
    for idx_v, val_v in vales.items():
        ax1.annotate(
            f"▼ Vale: {val_v}",
            (x[idx_v], val_v),
            textcoords="offset points", xytext=(0, -18),
            fontsize=9, color="#CF222E", ha="center",
            fontweight="bold", fontfamily=_FONTE,
        )

    ax1.set_xticks(x)
    ax1.set_xticklabels(semestres, rotation=45, ha="right", fontsize=9)
    ax1.set_ylabel("Quantidade", fontsize=11, fontfamily=_FONTE)
    ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    # ── Gráfico de barras de variação % (parte inferior) ──
    ax2 = fig.add_axes([0.08, 0.12, 0.84, 0.28])
    _aplicar_tema_claro(fig, ax2)
    ax2.set_title(
        "Variação Semestral (%)",
        fontsize=13, fontweight="bold", color=_COR_TITULO,
        fontfamily=_FONTE, pad=10,
    )

    variacoes = []
    for i in range(1, len(valores)):
        anterior = valores[i - 1]
        if anterior > 0:
            var = ((valores[i] - anterior) / anterior) * 100
        else:
            var = 0.0
        variacoes.append(var)

    x_var = list(range(1, len(semestres)))
    cores_barra = ["#1A7F37" if v >= 0 else "#CF222E" for v in variacoes]

    if variacoes:
        ax2.bar(x_var, variacoes, color=cores_barra, width=0.6, zorder=3)
        ax2.axhline(0, color=_COR_GRADE, linewidth=1)
        # Rótulos percentuais nas barras
        for xi, vi in zip(x_var, variacoes):
            offset = 3 if vi >= 0 else -3
            ax2.annotate(
                f"{vi:+.1f}%",
                (xi, vi),
                textcoords="offset points",
                xytext=(0, offset),
                fontsize=8, color=_COR_ROTULO, ha="center",
                va="bottom" if vi >= 0 else "top",
                fontfamily=_FONTE,
            )

    ax2.set_xticks(x_var)
    ax2.set_xticklabels(
        [semestres[i] for i in x_var], rotation=45, ha="right", fontsize=9
    )
    ax2.set_ylabel("Variação (%)", fontsize=11, fontfamily=_FONTE)

    # ── Estatísticas resumo ──
    total = sum(valores)
    media = total / len(valores) if valores else 0
    maximo = max(valores) if valores else 0
    minimo = min(valores) if valores else 0
    tendencia = "Crescente" if len(valores) >= 2 and valores[-1] >= valores[0] else "Decrescente"

    resumo = (
        f"Total: {total:,}  |  Média: {media:,.1f}  |  "
        f"Máx: {maximo:,}  |  Mín: {minimo:,}  |  "
        f"Tendência: {tendencia}"
    ).replace(",", ".")

    fig.text(
        0.50, 0.44, resumo,
        ha="center", va="center",
        fontsize=10, color="#0969DA",
        fontfamily=_FONTE,
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor="#F0F4F8",
            edgecolor=_COR_GRADE,
        ),
    )

    pdf.savefig(fig, dpi=_DPI)
    plt.close(fig)


# ──────────────────────────────────────────────
# Função principal (pode ser chamada pelo Streamlit)
# ──────────────────────────────────────────────

def gerar_relatorio_pdf(
    assuntos_selecionados: list[str],
    df: pd.DataFrame,
    output_path: str,
) -> str:
    """
    Gera o relatório PDF completo de evolução dos assuntos processuais.

    Parâmetros
    ----------
    assuntos_selecionados : list[str]
        Lista de nomes de assuntos a incluir no relatório.
    df : pd.DataFrame
        DataFrame já carregado contendo ao menos as colunas
        ``assuntos_str`` e ``dataAjuizamento``.
    output_path : str
        Caminho completo para salvar o arquivo PDF gerado.

    Retorna
    -------
    str
        Caminho do PDF gerado.
    """
    # Garantir que dataAjuizamento é datetime
    if "dataAjuizamento" in df.columns:
        df["dataAjuizamento"] = pd.to_datetime(
            df["dataAjuizamento"], errors="coerce"
        )

    total_processos = len(df)
    total_assuntos_analisados = len(assuntos_selecionados)

    # Preparar dados
    df_exp, semestres, pivot = _preparar_dados(df, assuntos_selecionados)

    if pivot.empty:
        raise ValueError(
            "Nenhum dado encontrado para os assuntos selecionados. "
            "Verifique se os nomes correspondem ao conteúdo da coluna 'assuntos_str'."
        )

    # Garantir diretório de saída
    dir_saida = os.path.dirname(output_path)
    if dir_saida:
        os.makedirs(dir_saida, exist_ok=True)

    # Total de ocorrências (para cálculo de %)
    total_ocorrencias = int(pivot.values.sum())

    with PdfPages(output_path) as pdf:
        # Página 1 — Capa
        _pagina_capa(pdf, total_processos, total_assuntos_analisados)

        # Página 2 — Tabela de frequência
        _pagina_tabela_frequencia(pdf, pivot, total_ocorrencias)

        # Página 3 — Evolução geral
        _pagina_evolucao_geral(pdf, pivot, semestres)

        # Página 4 — Heatmap
        _pagina_heatmap(pdf, pivot, semestres)

        # Páginas 5+ — Análise individual por assunto
        for i, assunto in enumerate(pivot.index):
            valores = pivot.loc[assunto].values.tolist()
            cor = _cor_assunto(i)
            _pagina_assunto_individual(pdf, assunto, semestres, valores, cor)

    print(f"✅ Relatório salvo com sucesso em: {output_path}")
    return output_path


# ──────────────────────────────────────────────
# Execução standalone
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # Diretório do próprio script
    diretorio_script = os.path.dirname(os.path.abspath(__file__))

    # Carregar todos os XLSX que seguem o padrão trt21_*_capa.xlsx
    padrao_glob = os.path.join(diretorio_script, "trt21_*_capa.xlsx")
    arquivos = glob.glob(padrao_glob)

    if not arquivos:
        print(
            f"⚠️  Nenhum arquivo encontrado com o padrão '{padrao_glob}'.\n"
            "Verifique se os arquivos XLSX estão no mesmo diretório do script."
        )
        raise SystemExit(1)

    print(f"📂 {len(arquivos)} arquivo(s) encontrado(s):")
    for arq in arquivos:
        print(f"   • {os.path.basename(arq)}")

    # Concatenar todos os DataFrames
    lista_dfs = []
    for arq in arquivos:
        try:
            df_temp = pd.read_excel(arq)
            lista_dfs.append(df_temp)
            print(f"   ✔ {os.path.basename(arq)}: {len(df_temp):,} linhas".replace(",", "."))
        except Exception as e:
            print(f"   ✖ Erro ao ler {os.path.basename(arq)}: {e}")

    if not lista_dfs:
        print("❌ Nenhum arquivo pôde ser carregado.")
        raise SystemExit(1)

    df_completo = pd.concat(lista_dfs, ignore_index=True)
    print(f"\n📊 Total de registros carregados: {len(df_completo):,}".replace(",", "."))

    # Converter data
    if "dataAjuizamento" in df_completo.columns:
        df_completo["dataAjuizamento"] = pd.to_datetime(
            df_completo["dataAjuizamento"], errors="coerce"
        )

    # Extrair todos os assuntos únicos e selecionar os 10 mais frequentes
    todos_assuntos = []
    for texto in df_completo["assuntos_str"].dropna():
        for _, nome in _parsear_assuntos(texto):
            todos_assuntos.append(nome)

    contagem_assuntos = pd.Series(todos_assuntos).value_counts()
    top_10 = contagem_assuntos.head(10).index.tolist()

    print(f"\n🏆 Top 10 assuntos selecionados para o relatório:")
    for i, a in enumerate(top_10, 1):
        freq = contagem_assuntos[a]
        print(f"   {i:>2}. {a} ({freq:,} ocorrências)".replace(",", "."))

    # Gerar PDF
    caminho_pdf = os.path.join(diretorio_script, "relatorio_assuntos_trt21.pdf")
    print(f"\n⏳ Gerando relatório PDF...")
    gerar_relatorio_pdf(top_10, df_completo, caminho_pdf)
