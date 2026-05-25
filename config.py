# ─────────────────────────────────────────────
# CONFIGURAÇÕES E CONSTANTES COMPARTILHADAS
# Tema claro / acadêmico
# ─────────────────────────────────────────────
import unicodedata

# Cores por tribunal
CORES_TRIBUNAL = {
    "TRT21": {"primaria": "#0969DA", "escala": ["#F0F4F8","#BDDDF5","#80BDE8","#4BA0DC","#1A7FCF","#0969DA","#0550AE","#033D8B"], "icon": "⚖️", "nome": "Justiça do Trabalho", "subtitulo": "TRT 21ª Região"},
    "TRT21_ULISSES": {"primaria": "#0969DA", "escala": ["#F0F4F8","#BDDDF5","#80BDE8","#4BA0DC","#1A7FCF","#0969DA","#0550AE","#033D8B"], "icon": "📋", "nome": "Justiça do Trabalho (Ulisses)", "subtitulo": "TRT 21ª Região · Base Capa"},
    "TJRN":  {"primaria": "#1A7F37", "escala": ["#F0FFF4","#B5E8C3","#6FD085","#3FB950","#1A7F37","#116329","#0A3D19","#052B0F"], "icon": "🏛️", "nome": "Justiça Estadual", "subtitulo": "Tribunal de Justiça do RN"},
    "JFRN":  {"primaria": "#8250DF", "escala": ["#F5F0FF","#DDD0F7","#BC8CFF","#A371F7","#8250DF","#6639BA","#4E2F8F","#362065"], "icon": "🇧🇷", "nome": "Justiça Federal", "subtitulo": "JFRN · TRF 5ª Região"},
}

# Paleta geral — tons acadêmicos (boa visibilidade em fundo branco)
COR_PRIMARIA   = "#0969DA"
COR_SECUNDARIA = "#1A7F37"
COR_ALERTA     = "#9A6700"
COR_PERIGO     = "#CF222E"
COR_ROXO       = "#8250DF"
COR_CIANO      = "#0598BC"
COR_LARANJA    = "#BC4C00"
FUNDO_PLOT     = "rgba(255,255,255,0)"
FUNDO_PAPEL    = "rgba(255,255,255,0)"
FONTE_PLOT     = dict(family="Sora, sans-serif", size=12, color="#57606A")
LINHA_GRADE    = "#D0D7DE"
TEXTO_EIXO     = "#57606A"
CORES_MULTI    = [COR_PRIMARIA, COR_ROXO, COR_CIANO, COR_LARANJA, COR_SECUNDARIA, COR_ALERTA, COR_PERIGO, "#BF3989", "#6E7781", "#D4A0D9"]

def layout_plotly(titulo=""):
    return dict(
        title=dict(text=titulo, font=dict(family="Sora, sans-serif", size=14, color="#1F2328"), x=0.01, xanchor="left"),
        paper_bgcolor=FUNDO_PAPEL, plot_bgcolor=FUNDO_PLOT, font=FONTE_PLOT,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(bgcolor="rgba(246,248,250,0.9)", bordercolor="#D0D7DE", borderwidth=1, font=dict(color="#57606A", size=11)),
        xaxis=dict(gridcolor=LINHA_GRADE, tickcolor=LINHA_GRADE, tickfont=dict(color=TEXTO_EIXO, size=11), linecolor="#D0D7DE", zerolinecolor="#D0D7DE"),
        yaxis=dict(gridcolor=LINHA_GRADE, tickcolor=LINHA_GRADE, tickfont=dict(color=TEXTO_EIXO, size=11), linecolor="#D0D7DE", zerolinecolor="#D0D7DE"),
        hoverlabel=dict(bgcolor="#F6F8FA", bordercolor="#0969DA", font=dict(family="Sora, sans-serif", size=12, color="#1F2328")),
    )

def _normalizar(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper().strip()

def fmt_num(v):
    return f"{v:,}".replace(",", ".")
