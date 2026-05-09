# ─────────────────────────────────────────────
# SEÇÃO: VISÃO GERAL COMPARATIVA
# ─────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config import *


def render_overview(dados: dict):
    """Renderiza a visão geral comparativa dos 3 tribunais."""

    st.caption("⚖️ Observatório dos Direitos Sociais do Semiárido · UFERSA")
    st.title("Judicialização dos Direitos Sociais no RN")
    st.markdown("Visão comparativa entre os três tribunais analisados — **TRT21** (Trabalho), **TJRN** (Estadual) e **JFRN/TRF5** (Federal)")

    # ── KPI Cards ──
    cols = st.columns(3)
    for i, (trib, df) in enumerate(dados.items()):
        if df.empty:
            continue
        cor = CORES_TRIBUNAL[trib]
        icon = cor["icon"]
        nome = cor["nome"]
        total = len(df)
        n_ano = df.groupby('ano').size()
        delta = ((n_ano.iloc[-1] - n_ano.iloc[-2]) / n_ano.iloc[-2] * 100) if len(n_ano) >= 2 else 0

        with cols[i]:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, rgba({_hex_to_rgb(cor["primaria"])},0.12), rgba({_hex_to_rgb(cor["primaria"])},0.04));
                        border: 1px solid rgba({_hex_to_rgb(cor["primaria"])},0.25); border-radius: 12px; padding: 1.2rem; text-align:center;'>
                <div style='font-size: 1.8rem;'>{icon}</div>
                <div style='font-size: 0.75rem; color: {cor["primaria"]}; font-weight: 700; letter-spacing: 0.08em; margin: 0.3rem 0;'>{trib}</div>
                <div style='font-size: 0.65rem; color: #8B949E;'>{nome}</div>
                <div style='font-size: 2rem; font-weight: 800; color: #E6EDF3; margin: 0.5rem 0 0.2rem;'>{fmt_num(total)}</div>
                <div style='font-size: 0.7rem; color: #8B949E;'>processos (2020–2024)</div>
                <div style='font-size: 0.8rem; color: {"#3FB950" if delta >= 0 else "#F85149"}; margin-top: 0.3rem;'>
                    {"▲" if delta >= 0 else "▼"} {abs(delta):.1f}% último ano
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Evolução temporal comparativa ──
    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()
        for trib, df in dados.items():
            if df.empty:
                continue
            cor = CORES_TRIBUNAL[trib]["primaria"]
            df_a = df.groupby('ano').size().reset_index(name='qtd')
            fig.add_trace(go.Scatter(
                x=df_a['ano'], y=df_a['qtd'],
                mode='lines+markers+text',
                name=trib,
                text=df_a['qtd'].apply(fmt_num),
                textposition='top center',
                textfont=dict(size=9, color=cor),
                line=dict(color=cor, width=2.5),
                marker=dict(size=7, color=cor, line=dict(color="#0D1117", width=2)),
                hovertemplate=f"<b>{trib}</b><br>%{{x}}: %{{y:,}} processos<extra></extra>",
            ))
        fig.update_layout(**layout_plotly("Evolução Anual por Tribunal"))
        fig.update_xaxes(tickmode='linear', dtick=1)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Total por tribunal (barras)
        tribs, totais, cores = [], [], []
        for trib, df in dados.items():
            if df.empty:
                continue
            tribs.append(trib)
            totais.append(len(df))
            cores.append(CORES_TRIBUNAL[trib]["primaria"])
        fig_bar = go.Figure(go.Bar(
            x=tribs, y=totais,
            marker_color=cores,
            text=[fmt_num(t) for t in totais],
            textposition='outside',
            textfont=dict(size=12, color="#C9D1D9"),
            hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
        ))
        fig_bar.update_layout(**layout_plotly("Volume Total por Tribunal"))
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ── Composição por assunto e classe ──
    col3, col4 = st.columns(2)

    with col3:
        # Top assuntos por tribunal (grouped bar)
        rows = []
        for trib, df in dados.items():
            if df.empty or 'assunto_primario_nome' not in df.columns:
                continue
            top5 = df['assunto_primario_nome'].value_counts().head(5)
            for ass, qtd in top5.items():
                rows.append({'tribunal': trib, 'assunto': str(ass)[:40], 'qtd': qtd})
        if rows:
            df_ass = pd.DataFrame(rows)
            fig_ass = px.bar(
                df_ass, x='qtd', y='assunto', color='tribunal',
                orientation='h', barmode='group',
                color_discrete_map={t: CORES_TRIBUNAL[t]["primaria"] for t in dados.keys()},
            )
            fig_ass.update_layout(**layout_plotly("Top 5 Assuntos por Tribunal"))
            fig_ass.update_layout(height=450)
            fig_ass.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(fig_ass, use_container_width=True)

    with col4:
        # Classes processuais por tribunal (stacked)
        rows = []
        for trib, df in dados.items():
            if df.empty or 'classe_nome' not in df.columns:
                continue
            top5 = df['classe_nome'].value_counts().head(5)
            for cls, qtd in top5.items():
                rows.append({'tribunal': trib, 'classe': str(cls)[:45], 'qtd': qtd})
        if rows:
            df_cls = pd.DataFrame(rows)
            fig_cls = px.bar(
                df_cls, x='qtd', y='classe', color='tribunal',
                orientation='h', barmode='group',
                color_discrete_map={t: CORES_TRIBUNAL[t]["primaria"] for t in dados.keys()},
            )
            fig_cls.update_layout(**layout_plotly("Top 5 Classes Processuais por Tribunal"))
            fig_cls.update_layout(height=450)
            fig_cls.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(fig_cls, use_container_width=True)

    st.markdown("---")

    # ── Tabela resumo ──
    st.markdown("### 📊 Resumo Comparativo")
    resumo = []
    for trib, df in dados.items():
        if df.empty:
            continue
        n_anos = df['ano'].nunique()
        n_orgaos = df['orgaoJulgador_nome'].nunique() if 'orgaoJulgador_nome' in df.columns else 0
        n_classes = df['classe_nome'].nunique() if 'classe_nome' in df.columns else 0
        n_assuntos = df['assunto_primario_nome'].nunique() if 'assunto_primario_nome' in df.columns else 0
        resumo.append({
            'Tribunal': trib,
            'Justiça': CORES_TRIBUNAL[trib]["nome"],
            'Total': fmt_num(len(df)),
            'Anos': n_anos,
            'Órgãos Julgadores': n_orgaos,
            'Classes': n_classes,
            'Assuntos': n_assuntos,
        })
    if resumo:
        st.dataframe(pd.DataFrame(resumo), use_container_width=True, hide_index=True)


def _hex_to_rgb(hex_color: str) -> str:
    """Converte #RRGGBB para 'R,G,B'."""
    h = hex_color.lstrip('#')
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"
