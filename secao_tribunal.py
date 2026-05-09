# ─────────────────────────────────────────────
# SEÇÃO GENÉRICA PARA TRIBUNAL (TJRN / JFRN)
# ─────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from config import *


def render_tribunal_generico(df_raw: pd.DataFrame, tribunal: str, filtros_sidebar=True):
    """Renderiza seção completa para TJRN ou JFRN."""
    cor_info = CORES_TRIBUNAL[tribunal]
    cor = cor_info["primaria"]

    st.caption(f"{cor_info['icon']} {cor_info['nome']} · {cor_info['subtitulo']}")
    st.title(f"Judicialização dos Direitos Sociais — {tribunal}")
    st.markdown(f"Análise dos processos de saúde · {cor_info['subtitulo']} · 2020–2024")

    if df_raw.empty:
        st.warning(f"Nenhum dado disponível para {tribunal}.")
        return

    # ── Filtros na sidebar ──
    with st.sidebar:
        st.markdown(f"**📅 PERÍODO — {tribunal}**")
        anos_disp = sorted(df_raw['ano'].dropna().unique().tolist())
        anos_sel = st.multiselect(f"Anos ({tribunal})", options=anos_disp, default=anos_disp, label_visibility="collapsed", key=f"anos_{tribunal}")

        if 'grau' in df_raw.columns:
            st.markdown(f"**🏛️ GRAU — {tribunal}**")
            graus_disp = sorted(df_raw['grau'].dropna().unique().tolist())
            graus_sel = st.multiselect(f"Grau ({tribunal})", options=graus_disp, default=graus_disp, label_visibility="collapsed", key=f"grau_{tribunal}")
        else:
            graus_sel = []

    # Aplicar filtros
    mask = df_raw['ano'].isin(anos_sel)
    if graus_sel and 'grau' in df_raw.columns:
        mask &= df_raw['grau'].isin(graus_sel)
    df_f = df_raw[mask].copy()

    if df_f.empty:
        st.warning("Nenhum processo com os filtros selecionados.")
        return

    # ── KPIs ──
    total = len(df_f)
    n_ano = df_f.groupby('ano').size()
    delta = ((n_ano.iloc[-1] - n_ano.iloc[-2]) / n_ano.iloc[-2] * 100) if len(n_ano) >= 2 else 0
    media_ano = int(n_ano.mean()) if not n_ano.empty else 0
    n_orgaos = df_f['orgaoJulgador_nome'].nunique() if 'orgaoJulgador_nome' in df_f.columns else 0
    n_classes = df_f['classe_nome'].nunique() if 'classe_nome' in df_f.columns else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total de Processos", fmt_num(total))
    k2.metric("Variação (último ano)", f"{delta:+.1f}%", delta=f"{delta:+.1f}%")
    k3.metric("Média Anual", fmt_num(media_ano))
    k4.metric("Órgãos Julgadores", f"{n_orgaos}")
    k5.metric("Classes Processuais", f"{n_classes}")

    st.markdown("---")

    # ── Abas ──
    aba1, aba2, aba3, aba4 = st.tabs([
        "📈  Evolução Temporal",
        "📂  Perfil das Demandas",
        "🏛️  Estrutura Judicial",
        "🔍  Explorar Dados",
    ])

    # ═══════════ ABA 1: EVOLUÇÃO TEMPORAL ═══════════
    with aba1:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            df_anual = df_f.groupby('ano').size().reset_index(name='qtd')
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_anual['ano'], y=df_anual['qtd'],
                mode='lines+markers+text',
                text=df_anual['qtd'].apply(fmt_num),
                textposition='top center', textfont=dict(size=10, color=cor),
                line=dict(color=cor, width=2.5),
                marker=dict(size=8, color=cor, line=dict(color="#0D1117", width=2)),
                fill='tozeroy', fillcolor=f'rgba({_hex_to_rgb(cor)},0.06)',
                hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
            ))
            fig.update_layout(**layout_plotly("Evolução Anual de Processos"))
            fig.update_xaxes(tickmode='linear', dtick=1)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            df_anual['delta'] = df_anual['qtd'].pct_change() * 100
            df_d = df_anual.dropna(subset=['delta'])
            cores_d = [COR_SECUNDARIA if v >= 0 else COR_PERIGO for v in df_d['delta']]
            fig_d = go.Figure(go.Bar(
                x=df_d['ano'], y=df_d['delta'].round(1),
                marker_color=cores_d,
                text=df_d['delta'].apply(lambda v: f"{v:+.1f}%"),
                textposition='outside', textfont=dict(size=10, color="#C9D1D9"),
                hovertemplate="<b>%{x}</b><br>Variação: %{y:.1f}%<extra></extra>",
            ))
            fig_d.update_layout(**layout_plotly("Variação Anual (%)"))
            fig_d.update_xaxes(tickmode='linear', dtick=1)
            fig_d.add_hline(y=0, line_dash="dash", line_color="#21262D")
            st.plotly_chart(fig_d, use_container_width=True)

        st.markdown("---")
        col_c, col_d = st.columns(2)
        with col_c:
            df_heat = df_f.groupby(['ano', 'mes']).size().reset_index(name='qtd')
            df_pivot = df_heat.pivot(index='mes', columns='ano', values='qtd').fillna(0)
            meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
            df_pivot.index = [meses[i-1] for i in df_pivot.index]
            escala = cor_info["escala"]
            fig_h = go.Figure(go.Heatmap(
                z=df_pivot.values, x=[str(c) for c in df_pivot.columns], y=df_pivot.index,
                colorscale=[[0, escala[0]], [0.3, escala[2]], [0.7, escala[4]], [1, escala[7]]],
                hovertemplate="<b>%{y} %{x}</b><br>%{z:.0f} processos<extra></extra>",
                showscale=True,
                colorbar=dict(tickfont=dict(color="#8B949E", size=10), outlinewidth=0, bgcolor="rgba(0,0,0,0)"),
            ))
            fig_h.update_layout(**layout_plotly("Distribuição Mensal (Heatmap)"))
            st.plotly_chart(fig_h, use_container_width=True)

        with col_d:
            df_trim = df_f.groupby('trimestre').size().reset_index(name='qtd').sort_values('trimestre').tail(20)
            fig_t = go.Figure(go.Bar(
                x=df_trim['trimestre'], y=df_trim['qtd'],
                marker=dict(color=df_trim['qtd'], colorscale=[[0, escala[2]], [1, cor]], showscale=False),
                hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
            ))
            fig_t.update_layout(**layout_plotly("Evolução Trimestral"))
            fig_t.update_xaxes(tickangle=45)
            st.plotly_chart(fig_t, use_container_width=True)

    # ═══════════ ABA 2: PERFIL DAS DEMANDAS ═══════════
    with aba2:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba({_hex_to_rgb(cor)},0.15), rgba({_hex_to_rgb(cor)},0.04));
                    border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid {cor};'>
            <span style='font-size: 0.78rem; color: #8B949E;'>
                📋 Perfil das ações judiciais de saúde — assuntos primários e classes processuais — {tribunal}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Assuntos
        st.markdown("### 📂 Assuntos Primários")
        col_a, col_b = st.columns(2)
        with col_a:
            if 'assunto_primario_nome' in df_f.columns:
                df_ass = df_f['assunto_primario_nome'].value_counts().head(15).reset_index()
                df_ass.columns = ['assunto', 'qtd']
                df_ass['label'] = df_ass['assunto'].str[:45]
                fig_a = go.Figure(go.Bar(
                    x=df_ass['qtd'], y=df_ass['label'], orientation='h',
                    marker=dict(color=cor, opacity=0.85),
                    text=df_ass['qtd'].apply(fmt_num), textposition='outside',
                    textfont=dict(size=10, color="#C9D1D9"),
                    hovertemplate="<b>%{y}</b><br>%{x:,} processos<extra></extra>",
                ))
                fig_a.update_layout(**layout_plotly("Top 15 Assuntos Primários"))
                fig_a.update_layout(height=520)
                fig_a.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_a, use_container_width=True)

        with col_b:
            if 'assunto_primario_nome' in df_f.columns:
                df_dn = df_f['assunto_primario_nome'].value_counts().head(8).reset_index()
                df_dn.columns = ['assunto', 'qtd']
                outros = df_f['assunto_primario_nome'].value_counts().iloc[8:].sum()
                if outros > 0:
                    df_dn = pd.concat([df_dn, pd.DataFrame({'assunto': ['Outros'], 'qtd': [outros]})], ignore_index=True)
                fig_dn = go.Figure(go.Pie(
                    labels=df_dn['assunto'].str[:30], values=df_dn['qtd'], hole=0.55,
                    marker=dict(colors=CORES_MULTI[:len(df_dn)], line=dict(color='#0D1117', width=2)),
                    hovertemplate="<b>%{label}</b><br>%{value:,}<br>%{percent}<extra></extra>",
                    textinfo='percent', textfont=dict(size=11),
                ))
                fig_dn.update_layout(**layout_plotly("Participação por Assunto"))
                fig_dn.update_layout(height=520, annotations=[dict(
                    text=f"<b>{fmt_num(len(df_f))}</b><br>total",
                    x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#C9D1D9", family="Sora"),
                )])
                st.plotly_chart(fig_dn, use_container_width=True)

        st.markdown("---")

        # Classes
        if 'classe_nome' in df_f.columns:
            st.markdown("### ⚖️ Classes Processuais")
            col_c, col_d = st.columns(2)
            with col_c:
                df_cls = df_f['classe_nome'].value_counts().reset_index()
                df_cls.columns = ['classe', 'qtd']
                df_cls['pct'] = (df_cls['qtd'] / df_cls['qtd'].sum() * 100).round(1)
                fig_cls = go.Figure(go.Bar(
                    x=df_cls['classe'].str[:40], y=df_cls['qtd'],
                    marker=dict(color=CORES_MULTI[:len(df_cls)]),
                    text=df_cls.apply(lambda r: f"{fmt_num(r['qtd'])} ({r['pct']}%)", axis=1),
                    textposition='outside', textfont=dict(size=10, color="#C9D1D9"),
                    hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
                ))
                fig_cls.update_layout(**layout_plotly("Volume por Classe Processual"))
                fig_cls.update_layout(height=400)
                st.plotly_chart(fig_cls, use_container_width=True)

            with col_d:
                fig_cp = go.Figure(go.Pie(
                    labels=df_cls['classe'].str[:35], values=df_cls['qtd'], hole=0.55,
                    marker=dict(colors=CORES_MULTI[:len(df_cls)], line=dict(color='#0D1117', width=2)),
                    hovertemplate="<b>%{label}</b><br>%{value:,}<br>%{percent}<extra></extra>",
                    textinfo='label+percent', textfont=dict(size=10),
                ))
                fig_cp.update_layout(**layout_plotly("Composição por Classe"))
                fig_cp.update_layout(height=400)
                st.plotly_chart(fig_cp, use_container_width=True)

    # ═══════════ ABA 3: ESTRUTURA JUDICIAL ═══════════
    with aba3:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba({_hex_to_rgb(cor)},0.15), rgba({_hex_to_rgb(cor)},0.04));
                    border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem; border-left: 3px solid {cor};'>
            <span style='font-size: 0.78rem; color: #8B949E;'>
                🏛️ Estrutura dos órgãos julgadores — distribuição por vara, grau de jurisdição e volume — {tribunal}
            </span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🏛️ Órgãos Julgadores")
        if 'orgaoJulgador_nome' in df_f.columns:
            col_a, col_b = st.columns([3, 2])
            with col_a:
                df_v = df_f['orgaoJulgador_nome'].value_counts().reset_index()
                df_v.columns = ['orgao', 'qtd']
                df_v['pct'] = (df_v['qtd'] / df_v['qtd'].sum() * 100).round(1)
                df_vt = df_v.head(20)
                fig_v = go.Figure(go.Bar(
                    x=df_vt['qtd'], y=df_vt['orgao'].str[:50], orientation='h',
                    marker=dict(color=df_vt['qtd'], colorscale=[[0, cor_info["escala"][2]], [1, cor]], showscale=False),
                    text=df_vt.apply(lambda r: f"{fmt_num(r['qtd'])} ({r['pct']}%)", axis=1),
                    textposition='outside', textfont=dict(size=10, color="#C9D1D9"),
                    hovertemplate="<b>%{y}</b><br>%{x:,} processos<extra></extra>",
                ))
                fig_v.update_layout(**layout_plotly("Top 20 Órgãos Julgadores"))
                fig_v.update_layout(height=550)
                fig_v.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_v, use_container_width=True)

            with col_b:
                df_vd = df_v.head(10).copy()
                outros_v = df_v.iloc[10:]['qtd'].sum() if len(df_v) > 10 else 0
                if outros_v > 0:
                    df_vd = pd.concat([df_vd, pd.DataFrame({'orgao': ['Demais'], 'qtd': [outros_v], 'pct': [0]})], ignore_index=True)
                fig_vp = go.Figure(go.Pie(
                    labels=df_vd['orgao'].str[:30], values=df_vd['qtd'], hole=0.5,
                    marker=dict(colors=CORES_MULTI[:len(df_vd)], line=dict(color='#0D1117', width=2)),
                    hovertemplate="<b>%{label}</b><br>%{value:,}<br>%{percent}<extra></extra>",
                    textinfo='percent', textfont=dict(size=10),
                ))
                fig_vp.update_layout(**layout_plotly("Distribuição por Órgão"))
                fig_vp.update_layout(height=550, annotations=[dict(
                    text=f"<b>{df_f['orgaoJulgador_nome'].nunique()}</b><br>órgãos",
                    x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#C9D1D9", family="Sora"),
                )])
                st.plotly_chart(fig_vp, use_container_width=True)

        st.markdown("---")

        # Grau de jurisdição
        if 'grau' in df_f.columns:
            st.markdown("### 📊 Grau de Jurisdição")
            grau_map = {'G1': '1º Grau', 'G2': '2º Grau', 'JE': 'Juizado Especial', 'TR': 'Turma Recursal'}
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                df_g = df_f['grau'].map(lambda x: grau_map.get(x, x)).value_counts().reset_index()
                df_g.columns = ['grau', 'qtd']
                fig_g = go.Figure(go.Bar(
                    x=df_g['grau'], y=df_g['qtd'],
                    marker=dict(color=CORES_MULTI[:len(df_g)]),
                    text=df_g['qtd'].apply(fmt_num), textposition='outside',
                    textfont=dict(size=11, color="#C9D1D9"),
                    hovertemplate="<b>%{x}</b><br>%{y:,} processos<extra></extra>",
                ))
                fig_g.update_layout(**layout_plotly("Volume por Grau"))
                st.plotly_chart(fig_g, use_container_width=True)

            with col_g2:
                df_g_t = df_f.copy()
                df_g_t['grau_label'] = df_g_t['grau'].map(lambda x: grau_map.get(x, x))
                df_g_ano = df_g_t.groupby(['ano', 'grau_label']).size().reset_index(name='qtd')
                fig_ga = px.bar(
                    df_g_ano, x='ano', y='qtd', color='grau_label', barmode='stack',
                    color_discrete_sequence=CORES_MULTI,
                    labels={'grau_label': 'Grau', 'ano': 'Ano', 'qtd': 'Processos'},
                )
                fig_ga.update_layout(**layout_plotly("Evolução por Grau"))
                fig_ga.update_xaxes(tickmode='linear', dtick=1)
                st.plotly_chart(fig_ga, use_container_width=True)

    # ═══════════ ABA 4: EXPLORAR DADOS ═══════════
    with aba4:
        st.markdown("**🔎 Pesquisa e Exportação**")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            filtro_ano = st.selectbox("Ano", ["Todos"] + [str(a) for a in sorted(df_f['ano'].dropna().unique())], key=f"exp_ano_{tribunal}")
        with col_s2:
            if 'grau' in df_f.columns:
                filtro_grau = st.selectbox("Grau", ["Todos"] + sorted(df_f['grau'].dropna().unique().tolist()), key=f"exp_grau_{tribunal}")
            else:
                filtro_grau = "Todos"

        df_exp = df_f.copy()
        if filtro_ano != "Todos":
            df_exp = df_exp[df_exp['ano'] == int(filtro_ano)]
        if filtro_grau != "Todos":
            df_exp = df_exp[df_exp['grau'] == filtro_grau]

        st.markdown(f"**{fmt_num(len(df_exp))} registros encontrados**")

        # Colunas para exibir
        cols_exibir = [c for c in ['Numero processo', 'dataajuizamento_dt', 'classe_nome', 'assunto_primario_nome',
                                    'orgaoJulgador_nome', 'grau', 'municipio_comarca', 'valor_causa'] if c in df_exp.columns]
        st.dataframe(df_exp[cols_exibir].head(1000), use_container_width=True, height=450)

        csv = df_exp.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="⬇️  Baixar CSV (filtrado)",
            data=csv,
            file_name=f"processos_{tribunal.lower()}_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime='text/csv',
            use_container_width=True,
            key=f"download_{tribunal}",
        )


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip('#')
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"
