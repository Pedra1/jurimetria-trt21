# ─────────────────────────────────────────────
# MÓDULO: Dados IBGE e Mapeamento de Varas – RN
# ─────────────────────────────────────────────
"""
Fornece dados socioeconômicos dos 167 municípios do RN via API IBGE
e mapeamento de varas trabalhistas do TRT21 a partir do CSV oficial.
"""
import streamlit as st
import pandas as pd
import urllib.request
import gzip
import json
import re
import os
import unicodedata


# ═══════════════════════════════════════════════
#  IDHM – Atlas Brasil / PNUD (Censo 2010)
#  Não há API pública; dados hardcoded.
# ═══════════════════════════════════════════════
_IDHM_RN = {
    "Parnamirim": 0.766, "Natal": 0.763, "Mossoró": 0.720, "Caicó": 0.710,
    "São José do Seridó": 0.694, "Currais Novos": 0.691, "Areia Branca": 0.682,
    "Ipueira": 0.654, "Acari": 0.679, "Pau dos Ferros": 0.678,
    "Parelhas": 0.676, "Alto do Rodrigues": 0.673, "Macau": 0.665,
    "Rafael Godeiro": 0.660, "Grossos": 0.664, "Jardim do Seridó": 0.660,
    "São Gonçalo do Amarante": 0.660, "Açu": 0.658, "Assu": 0.658, "Extremoz": 0.660,
    "Carnaúba dos Dantas": 0.659, "São João do Sabugi": 0.657,
    "Cruzeta": 0.652, "Lucrecia": 0.652, "Tibau do Sul": 0.649,
    "Ouro Branco": 0.649, "Messias Targino": 0.648, "São Vicente": 0.647,
    "Santana do Seridó": 0.645, "Florânia": 0.643, "Timbaúba dos Batistas": 0.642,
    "Macaíba": 0.640, "Apodi": 0.639, "Goianinha": 0.637,
    "Caraúbas": 0.635, "Felipe Guerra": 0.633, "Tibau": 0.632,
    "Santa Cruz": 0.635, "Pendências": 0.630, "Nova Cruz": 0.628,
    "Encanto": 0.620, "Bodó": 0.600, "São Francisco do Oeste": 0.614,
    "Várzea": 0.613, "Guamaré": 0.632, "Campo Redondo": 0.613,
    "Lajes Pintadas": 0.608, "Lajes": 0.608, "Itajá": 0.611,
    "Angicos": 0.623, "Almino Afonso": 0.608, "Tenente Laurentino Cruz": 0.600,
    "Equador": 0.616, "São Paulo do Potengi": 0.634, "Nísia Floresta": 0.628,
    "Martins": 0.623, "Portalegre": 0.622, "Doutor Severiano": 0.617,
    "Campo Grande": 0.611, "Augusto Severo": 0.611,  # mesmo município, nomes diferentes (IBGE vs GeoJSON)
    "Santo Antônio": 0.617, "Umarizal": 0.616,
    "Patu": 0.614, "Major Sales": 0.608, "Ceará-Mirim": 0.616,
    "Água Nova": 0.601, "São José do Campestre": 0.614,
    "Janduís": 0.609, "Serra do Mel": 0.603, "Pilões": 0.607,
    "Itaú": 0.612, "Taboleiro Grande": 0.593, "São Rafael": 0.604,
    "São José de Mipibu": 0.611, "Monte Alegre": 0.600,
    "Marcelino Vieira": 0.604, "Baía Formosa": 0.603, "Tangará": 0.602,
    "São Fernando": 0.601, "Rafael Fernandes": 0.596,
    "Maxaranguape": 0.595, "Luís Gomes": 0.593, "José da Penha": 0.592,
    "São Miguel": 0.606, "Passa e Fica": 0.591,
    "Francisco Dantas": 0.590, "Cerro Corá": 0.590, "Arês": 0.606, "Arez": 0.606,
    "Alexandria": 0.606, "Ruy Barbosa": 0.590,
    "Severiano Melo": 0.588, "Rodolfo Fernandes": 0.591,
    "Jaçanã": 0.588, "Jardim de Piranhas": 0.586,
    "Paraú": 0.586, "Ipanguaçu": 0.585, "Triunfo Potiguar": 0.582,
    "Lagoa d'Anta": 0.585, "Jucurutu": 0.583,
    "Serrinha dos Pintos": 0.579, "Monte das Gameleiras": 0.586,
    "Serra Negra do Norte": 0.598, "Frutuoso Gomes": 0.583,
    "Fernando Pedroza": 0.580, "Upanema": 0.577,
    "São Bento do Trairi": 0.580, "Jundiá": 0.577,
    "João Câmara": 0.576, "Viçosa": 0.573, "Tenente Ananias": 0.574,
    "Serrinha": 0.573, "Riachuelo": 0.570,
    "Governador Dix-Sept Rosado": 0.570, "Brejinho": 0.568,
    "Santana do Matos": 0.568, "São Miguel do Gostoso": 0.577,
    "Riacho de Santana": 0.571, "Santa Maria": 0.567,
    "Porto do Mangue": 0.569, "São Pedro": 0.565,
    "Passagem": 0.565, "Paraná": 0.562, "Lagoa de Velhos": 0.561,
    "Carnaubais": 0.559, "Vera Cruz": 0.558, "Poço Branco": 0.563,
    "Coronel Ezequiel": 0.560, "Caiçara do Rio do Vento": 0.558,
    "São Tomé": 0.557, "Olho-d'Água do Borges": 0.556, "Olho d'Água do Borges": 0.556,
    "Lagoa Nova": 0.556, "Afonso Bezerra": 0.554,
    "Riacho da Cruz": 0.555, "Bom Jesus": 0.554,
    "Senador Elói de Souza": 0.552, "Serra de São Bento": 0.549,
    "Pedro Avelino": 0.547, "Lagoa Salgada": 0.549,
    "Bento Fernandes": 0.550, "Canguaretama": 0.551,
    "Coronel João Pessoa": 0.549, "Antônio Martins": 0.546,
    "Vila Flor": 0.545, "Caiçara do Norte": 0.543,
    "Januário Cicco": 0.542, "Baraúna": 0.574,
    "Touros": 0.554, "Sítio Novo": 0.548,
    "Senador Georgino Avelino": 0.548, "Taipu": 0.545,
    "Rio do Fogo": 0.543, "Japi": 0.541, "Jandaíra": 0.540,
    "Pedro Velho": 0.543, "Pureza": 0.539,
    "Barcelona": 0.536, "Jardim de Angicos": 0.540,
    "Galinhos": 0.536, "Presidente Juscelino": 0.537, "Serra Caiada": 0.537,
    "Pedra Grande": 0.530, "Pedra Preta": 0.533,
    "Espírito Santo": 0.539, "Montanhas": 0.537,
    "Venha-Ver": 0.531, "São Bento do Norte": 0.533,
    "Lagoa de Pedras": 0.534, "Ielmo Marinho": 0.532,
    "Parazinho": 0.530, "João Dias": 0.530,
}


# ═══════════════════════════════════════════════
#  MAPEAMENTO: VARA → MUNICÍPIOS (do CSV oficial)
# ═══════════════════════════════════════════════
# Nota: nomes dos municípios são os do GeoJSON do IBGE para matching perfeito

_VARA_MUNICIPIOS = {
    "Assu": [
        "Açu", "Angicos", "Campo Grande", "Augusto Severo",  # Campo Grande = Augusto Severo (nome GeoJSON IBGE)
        "Carnaubais", "Fernando Pedroza",
        "Ipanguaçu", "Itajá", "Janduís", "Lajes", "Paraú",
        "Porto do Mangue", "Santana do Matos", "São Rafael",
        "Triunfo Potiguar", "Upanema",
    ],
    "Caicó": [
        "Caicó", "Cruzeta", "Equador", "Ipueira", "Jardim de Piranhas",
        "Jardim do Seridó", "Jucurutu", "Ouro Branco", "Parelhas",
        "Santana do Seridó", "São Fernando", "São João do Sabugi",
        "São José do Seridó", "Serra Negra do Norte", "Timbaúba dos Batistas",
    ],
    "Ceará-Mirim": [
        "Ceará-Mirim", "Bento Fernandes", "Jardim de Angicos", "João Câmara",
        "Maxaranguape", "Parazinho", "Pedra Grande", "Pedra Preta",
        "Poço Branco", "Pureza", "Rio do Fogo", "São Miguel do Gostoso",
        "Taipu", "Touros",
    ],
    "Currais Novos": [
        "Currais Novos", "Acari", "Bodó", "Campo Redondo",
        "Carnaúba dos Dantas", "Cerro Corá", "Coronel Ezequiel",
        "Florânia", "Jaçanã", "Japi", "Lagoa Nova", "Lajes Pintadas",
        "Santa Cruz", "São Bento do Trairi", "São Vicente",
        "Sítio Novo", "Tangará", "Tenente Laurentino Cruz",
    ],
    "Goianinha": [
        "Goianinha", "Arês", "Baía Formosa", "Januário Cicco", "Brejinho",
        "Canguaretama", "Espírito Santo", "Jundiá", "Lagoa d'Anta",
        "Lagoa de Pedras", "Lagoa Salgada", "Monte Alegre", "Montanhas",
        "Monte das Gameleiras", "Nova Cruz", "Passa e Fica", "Passagem",
        "Pedro Velho", "Santo Antônio", "São José do Campestre",
        "Senador Georgino Avelino", "Serra de São Bento", "Serrinha",
        "Tibau do Sul", "Várzea", "Vila Flor",
    ],
    "Macau": [
        "Macau", "Afonso Bezerra", "Alto do Rodrigues", "Caiçara do Norte",
        "Galinhos", "Guamaré", "Jandaíra", "Pedro Avelino",
        "Pendências", "São Bento do Norte",
    ],
    "Mossoró": [
        "Mossoró", "Apodi", "Areia Branca", "Baraúna", "Caraúbas",
        "Felipe Guerra", "Governador Dix-Sept Rosado", "Grossos",
        "Serra do Mel", "Tibau",
    ],
    "Natal": [
        "Natal", "Barcelona", "Bom Jesus", "Caiçara do Rio do Vento",
        "Extremoz", "Ielmo Marinho", "Lagoa de Velhos", "Macaíba",
        "Nísia Floresta", "Parnamirim", "Riachuelo", "Ruy Barbosa",
        "Santa Maria", "São Gonçalo do Amarante", "São José de Mipibu",
        "São Paulo do Potengi", "São Pedro", "São Tomé",
        "Presidente Juscelino", "Senador Elói de Souza", "Vera Cruz",
    ],
    "Pau dos Ferros": [
        "Pau dos Ferros", "Água Nova", "Alexandria", "Almino Afonso",
        "Antônio Martins", "Coronel João Pessoa", "Doutor Severiano",
        "Encanto", "Francisco Dantas", "Frutuoso Gomes", "João Dias",
        "José da Penha", "Itaú", "Lucrecia", "Luís Gomes",
        "Marcelino Vieira", "Martins", "Messias Targino", "Paraná",
        "Pilões", "Portalegre", "Rafael Fernandes", "Rafael Godeiro",
        "Riacho da Cruz", "Riacho de Santana", "Rodolfo Fernandes",
        "Olho-d'Água do Borges", "São Francisco do Oeste", "São Miguel",
        "Severiano Melo", "Taboleiro Grande", "Tenente Ananias",
        "Viçosa", "Patu", "Major Sales", "Venha-Ver",
        "Serrinha dos Pintos", "Umarizal",
    ],
}

# Reverso: município → vara
_MUNICIPIO_PARA_VARA = {}
for vara, muns in _VARA_MUNICIPIOS.items():
    for m in muns:
        _MUNICIPIO_PARA_VARA[m] = vara

# Cores por vara (9 varas)
_CORES_VARA = {
    "Assu":           "#58A6FF",
    "Caicó":          "#BC8CFF",
    "Ceará-Mirim":    "#39D3F0",
    "Currais Novos":  "#FF7B54",
    "Goianinha":      "#3FB950",
    "Macau":          "#D29922",
    "Mossoró":        "#F85149",
    "Natal":          "#0969DA",
    "Pau dos Ferros": "#E879F9",
}


def _normalizar(texto):
    """Remove acentos e converte para upper."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    ).upper().strip()


def obter_vara_municipio(nome_municipio):
    """Retorna a vara de um município (match exato ou normalizado)."""
    if nome_municipio in _MUNICIPIO_PARA_VARA:
        return _MUNICIPIO_PARA_VARA[nome_municipio]
    # Normalizado
    norm = _normalizar(nome_municipio)
    for mun, vara in _MUNICIPIO_PARA_VARA.items():
        if _normalizar(mun) == norm:
            return vara
    return None


def obter_idhm(nome_municipio):
    """Retorna o IDHM de um município (match exato ou normalizado)."""
    if nome_municipio in _IDHM_RN:
        return _IDHM_RN[nome_municipio]
    norm = _normalizar(nome_municipio)
    for mun, val in _IDHM_RN.items():
        if _normalizar(mun) == norm:
            return val
    return None


# ═══════════════════════════════════════════════
#  API IBGE – População, PIB, Área
# ═══════════════════════════════════════════════
_IBGE_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"


def _fetch_ibge(url):
    """Fetch com tratamento de gzip."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (JurimetriaTRT21)',
        'Accept-Encoding': 'gzip, deflate',
    })
    resp = urllib.request.urlopen(req, timeout=30)
    raw = resp.read()
    try:
        raw = gzip.decompress(raw)
    except Exception:
        pass
    return json.loads(raw.decode('utf-8'))


@st.cache_data(ttl=86400, show_spinner="Carregando dados do IBGE...")
def carregar_dados_ibge():
    """
    Busca população, PIB e área dos 167 municípios do RN via API IBGE.
    Cache de 24h. Retorna dict {nome_municipio: {pop, pib_pc, area}}.
    """
    resultado = {}

    try:
        # ── 1. Municípios (para nome → id) ──
        muns_url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/24/municipios"
        muns_data = _fetch_ibge(muns_url)
        id_para_nome = {}
        for m in muns_data:
            id_para_nome[str(m['id'])] = m['nome']
            resultado[m['nome']] = {'populacao': 0, 'pib_pc': 0.0, 'area': 0.0}

        # ── 2. População (agregado 6579, var 9324) ──
        pop_url = f"{_IBGE_BASE}/6579/periodos/-1/variaveis/9324?localidades=N6[N3[24]]"
        pop_data = _fetch_ibge(pop_url)
        for serie in pop_data[0]['resultados'][0]['series']:
            nome = serie['localidade']['nome'].replace(' - RN', '')
            vals = serie['serie']
            ultimo = list(vals.values())[-1] if vals else '0'
            if nome in resultado:
                try:
                    resultado[nome]['populacao'] = int(ultimo)
                except (ValueError, TypeError):
                    pass

        # ── 3. PIB per capita (agregado 5938, var 37) ──
        pib_url = f"{_IBGE_BASE}/5938/periodos/-1/variaveis/37?localidades=N6[N3[24]]"
        pib_data = _fetch_ibge(pib_url)
        for serie in pib_data[0]['resultados'][0]['series']:
            nome = serie['localidade']['nome'].replace(' - RN', '')
            vals = serie['serie']
            ultimo = list(vals.values())[-1] if vals else '0'
            if nome in resultado:
                try:
                    # PIB total em mil reais / população = PIB per capita
                    pib_total_mil = float(ultimo)
                    pop = resultado[nome]['populacao']
                    if pop > 0:
                        resultado[nome]['pib_pc'] = round(pib_total_mil * 1000 / pop, 2)
                    else:
                        resultado[nome]['pib_pc'] = pib_total_mil  # fallback
                except (ValueError, TypeError):
                    pass

        # ── 4. Área territorial (agregado 1301, var 9601) ──
        try:
            area_url = f"{_IBGE_BASE}/1301/periodos/-1/variaveis/9601?localidades=N6[N3[24]]"
            area_data = _fetch_ibge(area_url)
            for serie in area_data[0]['resultados'][0]['series']:
                nome = serie['localidade']['nome'].replace(' - RN', '')
                vals = serie['serie']
                ultimo = list(vals.values())[-1] if vals else '0'
                if nome in resultado:
                    try:
                        resultado[nome]['area'] = round(float(ultimo), 1)
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass  # Área é informação complementar, não bloqueia

    except Exception as e:
        st.warning(f"Erro ao carregar dados do IBGE: {e}. Usando dados parciais.")

    # ── Aliases: municípios com nomes diferentes no GeoJSON vs API IBGE ──
    # Mapeamento completo auditado comparando geojs-24-mun.json com a API IBGE
    _ALIASES = {
        # GeoJSON/Outros nome    : API IBGE nome
        "Augusto Severo"        : "Campo Grande",          # renomeado; GeoJSON usa nome antigo
        "A\u00e7u"               : "Ass\u00fa",              # GeoJSON usa A\u00e7u; API usa Ass\u00fa
        "Assu"                  : "Ass\u00fa",              # Alguns códigos usam Assu; API usa Ass\u00fa
        "Ar\u00eas"              : "Arez",                   # GeoJSON usa acento; API usa sem acento
        "Olho-d'\u00c1gua do Borges": "Olho d'\u00c1gua do Borges",  # hífen vs espaço
        "Presidente Juscelino"  : "Serra Caiada",           # município renomeado
    }
    for nome_geo, nome_api in _ALIASES.items():
        if nome_geo not in resultado and nome_api in resultado:
            resultado[nome_geo] = resultado[nome_api].copy()

    return resultado
