# ─────────────────────────────────────────────
# CONFIGURAÇÕES E CONSTANTES COMPARTILHADAS
# ─────────────────────────────────────────────
import unicodedata

# Cores por tribunal
CORES_TRIBUNAL = {
    "TRT21": {"primaria": "#58A6FF", "escala": ["#0D1F36","#0C2D5A","#1C3F80","#2958B3","#388BFD","#58A6FF","#79BFFF","#A5D3FF"], "icon": "⚖️", "nome": "Justiça do Trabalho", "subtitulo": "TRT 21ª Região"},
    "TRT21_ULISSES": {"primaria": "#79BFFF", "escala": ["#0D1F36","#0C2D5A","#1C3F80","#2958B3","#388BFD","#58A6FF","#79BFFF","#A5D3FF"], "icon": "📋", "nome": "Justiça do Trabalho (Ulisses)", "subtitulo": "TRT 21ª Região · Base Capa"},
    "TJRN":  {"primaria": "#3FB950", "escala": ["#0D1F14","#0C3D1A","#1C6030","#29804A","#38A865","#3FB950","#6BD07A","#A5E8B5"], "icon": "🏛️", "nome": "Justiça Estadual", "subtitulo": "Tribunal de Justiça do RN"},
    "JFRN":  {"primaria": "#BC8CFF", "escala": ["#1A0D36","#2D0C5A","#3F1C80","#5829B3","#7B38FD","#BC8CFF","#D4AFFF","#E8D3FF"], "icon": "🇧🇷", "nome": "Justiça Federal", "subtitulo": "JFRN · TRF 5ª Região"},
}

# Paleta geral
COR_PRIMARIA   = "#58A6FF"
COR_SECUNDARIA = "#3FB950"
COR_ALERTA     = "#D29922"
COR_PERIGO     = "#F85149"
COR_ROXO       = "#BC8CFF"
COR_CIANO      = "#39D3F0"
COR_LARANJA    = "#FF7B54"
FUNDO_PLOT     = "rgba(0,0,0,0)"
FUNDO_PAPEL    = "rgba(22,27,34,0)"
FONTE_PLOT     = dict(family="Sora, sans-serif", size=12, color="#8B949E")
LINHA_GRADE    = "#21262D"
TEXTO_EIXO     = "#8B949E"
CORES_MULTI    = [COR_PRIMARIA, COR_ROXO, COR_CIANO, COR_LARANJA, COR_SECUNDARIA, COR_ALERTA, COR_PERIGO, "#E879F9", "#94A3B8", "#F0ABFC"]

def layout_plotly(titulo=""):
    return dict(
        title=dict(text=titulo, font=dict(family="Sora, sans-serif", size=14, color="#C9D1D9"), x=0.01, xanchor="left"),
        paper_bgcolor=FUNDO_PAPEL, plot_bgcolor=FUNDO_PLOT, font=FONTE_PLOT,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(bgcolor="rgba(22,27,34,0.8)", bordercolor="#21262D", borderwidth=1, font=dict(color="#8B949E", size=11)),
        xaxis=dict(gridcolor=LINHA_GRADE, tickcolor=LINHA_GRADE, tickfont=dict(color=TEXTO_EIXO, size=11), linecolor="#21262D", zerolinecolor="#21262D"),
        yaxis=dict(gridcolor=LINHA_GRADE, tickcolor=LINHA_GRADE, tickfont=dict(color=TEXTO_EIXO, size=11), linecolor="#21262D", zerolinecolor="#21262D"),
        hoverlabel=dict(bgcolor="#21262D", bordercolor="#388BFD", font=dict(family="Sora, sans-serif", size=12, color="#E6EDF3")),
    )

def _normalizar(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper().strip()

def fmt_num(v):
    return f"{v:,}".replace(",", ".")
