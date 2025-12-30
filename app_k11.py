import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from datetime import date
from models import engine

# ==============================================================================
# CONFIGURAÇÃO E CSS
# ==============================================================================
st.set_page_config(page_title="Sentinela AL 5.0", layout="wide", page_icon="🌵")

st.markdown(
    """
<style>
    .metric-card {background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px; padding: 20px; text-align: center;}
    .badge-veterano {background-color: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;}
    .badge-novato {background-color: #17a2b8; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;}
    .badge-intermitente {background-color: #ffc107; color: black; padding: 4px 8px; border-radius: 4px; font-weight: bold;}
    .alert-red {color: #dc3545; font-weight: bold;}
</style>
""",
    unsafe_allow_html=True,
)

def exibir_disclaimer():
    st.sidebar.markdown("---")
    with st.sidebar.expander("ℹ️ Sobre e Aviso Legal", expanded=False):
        st.markdown("""
        <div class='disclaimer-box'>
        <b>Autoria:</b><br>
        Projeto desenvolvido por <b>Ludson Almeida</b>, estudante de Ciência da Computação na UFAL (Universidade Federal de Alagoas).<br><br>
        <b>Objetivo:</b><br>
        Este programa trata-se de um projeto de portfólio para experimentação em Visualização e Engenharia de Dados. <b>Não possui vínculo oficial</b> com a Assembleia Legislativa ou órgãos de controle.<br><br>
        <b>Fonte dos Dados:</b><br>
        Dados extraídos automaticamente do portal público: <a href='https://transparencia.al.al.leg.br/' target='_blank'>Transparência ALE-AL</a>. A coleta é feita de forma automatizada.<br><br>
        <b>Isenção de Responsabilidade:</b><br>
        1. Podem ocorrer erros no processo de extração (OCR/HTML parsing) ou no tratamento dos dados.<br>
        2. Nenhuma conclusão deve ser tomada exclusivamente com base nesta ferramenta sem conferência na fonte oficial.<br>
        3. O autor não se responsabiliza pelo uso indevido das informações aqui apresentadas.
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# ETL: CARREGAMENTO
# ==============================================================================
@st.cache_data
def carregar_dados():
    # engine = create_engine("sqlite:///sentinela_alagoas.db")
    
    try:
        query = "SELECT * FROM historico_folha"
        df = pd.read_sql(query, engine)
    except Exception:
        return pd.DataFrame()

    # 1. Cria Data Base
    df["data_base"] = pd.to_datetime(
        df["ano_referencia"].astype(str)
        + "-"
        + df["mes_referencia"].astype(str)
        + "-01"
    )

    # 2. Extrai Sobrenome
    def extrair_sobrenome(nome):
        partes = str(nome).strip().upper().split()
        if not partes:
            return "DESCONHECIDO"
        ignorar = ["JUNIOR", "NETO", "FILHO", "SOBRINHO"]
        if len(partes) > 1 and partes[-1] in ignorar:
            return partes[-2]
        return partes[-1]

    df["sobrenome"] = df["nome"].apply(extrair_sobrenome)
    return df


@st.cache_data
def calcular_rotatividade(df):
    datas = sorted(df["data_base"].unique())
    resultados = []
    for i in range(1, len(datas)):
        mes_atual = datas[i]
        mes_anterior = datas[i - 1]
        nomes_atual = set(df[df["data_base"] == mes_atual]["nome"])
        nomes_anterior = set(df[df["data_base"] == mes_anterior]["nome"])
        entraram = len(nomes_atual - nomes_anterior)
        sairam = len(nomes_anterior - nomes_atual)
        resultados.append(
            {"data_base": mes_atual, "Admissões": entraram, "Desligamentos": -sairam}
        )
    return pd.DataFrame(resultados)


@st.cache_data
def converter_para_csv(df):
    return df.to_csv(index=False).encode("utf-8")


# Carrega Dataframe
df_raw = carregar_dados()

if df_raw.empty:
    st.error("🚨 Banco de dados vazio! Rode o 'ingestor_turbo.py' primeiro.")
    st.stop()

# ==============================================================================
# SIDEBAR: FILTROS OTIMIZADOS (com botão de aplicar) - REPLACED
# ==============================================================================
st.sidebar.title("🎛️ Centro de Comando")

# Prepara valores padrão / limites usados pelo form
min_date = df_raw["data_base"].min().date()
max_date = df_raw["data_base"].max().date()
# lista ordenada de competências (datas) para usar no select_slider
competencias = sorted(df_raw["data_base"].dt.date.unique())

anos_disponiveis = sorted(df_raw["data_base"].dt.year.unique(), reverse=True)
default_anos = anos_disponiveis[:1] if anos_disponiveis else []

# Inicializa filtro aplicado na sessão (persistência entre reruns)
if "filtro_aplicado" not in st.session_state:
    st.session_state.filtro_aplicado = {
        "modo": "Seleção Rápida (Por Ano)",
        "anos": default_anos,
        "range": (min_date, max_date),
    }

# --- FORMULÁRIO: controles só são efetivados quando o usuário clica em "Aplicar" ---
with st.sidebar.form("filtro_temporal_form"):
    st.subheader("📅 Filtro Temporal")
    modo_filtro = st.radio(
        "Método de Seleção:",
        ["Seleção Rápida (Por Ano)", "Intervalo Preciso (Slider)"],
        index=(
            0 if st.session_state.filtro_aplicado["modo"].startswith("Seleção") else 1
        ),
    )

    if modo_filtro == "Seleção Rápida (Por Ano)":
        anos_sel = st.multiselect(
            "Selecione os Anos:",
            options=anos_disponiveis,
            default=st.session_state.filtro_aplicado.get("anos", default_anos),
        )
    else:  # Intervalo Preciso (agora com select_slider por competências)
        # valor padrão do range aplicado (se houver)
        default_range = st.session_state.filtro_aplicado.get(
            "range", (min_date, max_date)
        )
        # garante que os valores default existem dentro de 'competencias'
        # se não existirem, usa os extremos
        start_default = (
            default_range[0] if default_range[0] in competencias else competencias[0]
        )
        end_default = (
            default_range[1] if default_range[1] in competencias else competencias[-1]
        )

        # select_slider com formato amigável de mês/ano
        start_date, end_date = st.select_slider(
            "Arraste para definir início e fim:",
            options=competencias,
            value=(start_default, end_default),
            format_func=lambda d: d.strftime("%m/%Y"),
        )

    # Botão que efetiva o filtro — visual mais simples
    aplicar = st.form_submit_button("Aplicar")

    # Quando o usuário submete o form, atualizamos session_state.filtro_aplicado
    if aplicar:
        if modo_filtro == "Seleção Rápida (Por Ano)":
            if not anos_sel:
                st.sidebar.warning("Selecione pelo menos um ano.")
                # não atualiza o filtro aplicado quando inválido; mantém o anterior
            else:
                st.session_state.filtro_aplicado = {
                    "modo": modo_filtro,
                    "anos": anos_sel,
                    "range": (min_date, max_date),
                }
                st.sidebar.success(f"Filtro aplicado: {len(anos_sel)} ano(s).")
        else:
            st.session_state.filtro_aplicado = {
                "modo": modo_filtro,
                "anos": None,
                "range": (start_date, end_date),
            }
            st.sidebar.success(
                f"Filtro aplicado: {start_date.strftime('%m/%Y')} — {end_date.strftime('%m/%Y')}"
            )

# --- A análise usa o último filtro armazenado em session_state.filtro_aplicado ---
f = st.session_state.filtro_aplicado
if f["modo"] == "Seleção Rápida (Por Ano)":
    if f.get("anos"):
        df_filtered = df_raw[df_raw["data_base"].dt.year.isin(f["anos"])]
    else:
        df_filtered = df_raw.copy()
else:
    start_date, end_date = f.get("range", (min_date, max_date))
    mask = (df_raw["data_base"].dt.date >= start_date) & (
        df_raw["data_base"].dt.date <= end_date
    )
    df_filtered = df_raw.loc[mask]


# Resumo do Filtro
st.sidebar.info(
    f"Analisando **{len(df_filtered):,}** registros em **{df_filtered['data_base'].nunique()}** competências."
)

# Botão de Exportação Global
st.sidebar.markdown("---")
csv_filtrado = converter_para_csv(df_filtered)
st.sidebar.download_button(
    label="📥 Baixar Seleção Atual (.csv)",
    data=csv_filtrado,
    file_name="sentinela_dados_selecao.csv",
    mime="text/csv",
)

exibir_disclaimer()

# ==============================================================================
# DASHBOARD
# ==============================================================================
st.title("🌵 Sentinela Alagoas 5.0")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📈 Macro & Radar",
        "🔄 Dinâmica de RH",
        "🧬 Grupos & Ganhos",
        "🕵️ Detetive Individual",
        "🎯 Radar de Anomalias",
    ]
)

# ------------------------------------------------------------------------------
# TAB 1: MACRO E RADAR DE ANOMALIAS (Recuperado!)
# ------------------------------------------------------------------------------
with tab1:
    col1, col2, col3 = st.columns(3)
    custo_total = df_filtered["rendimento_liquido"].sum()
    media_mensal = df_filtered.groupby("data_base")["rendimento_liquido"].sum().mean()

    col1.metric("Custo Total (Seleção)", f"R$ {custo_total/1e6:,.1f} Mi")
    col2.metric("Média Mensal da Folha", f"R$ {media_mensal/1e6:,.1f} Mi")
    col3.metric("Total de CPFs Distintos", f"{df_filtered['nome'].nunique()}")

    st.markdown("---")

    # 1. Gráfico de Evolução (Eixo Duplo)
    st.subheader("📊 Evolução: Dinheiro vs. Pessoas")
    df_agrupado = (
        df_filtered.groupby("data_base")
        .agg({"rendimento_liquido": "sum", "nome": "nunique"})
        .reset_index()
    )

    fig_dual = go.Figure()
    fig_dual.add_trace(
        go.Bar(
            x=df_agrupado["data_base"],
            y=df_agrupado["rendimento_liquido"],
            name="Custo Líquido (R$)",
            marker_color="#0052cc",
            yaxis="y",
        )
    )
    fig_dual.add_trace(
        go.Scatter(
            x=df_agrupado["data_base"],
            y=df_agrupado["nome"],
            name="Funcionários",
            mode="lines+markers",
            line=dict(color="#ff2b2b", width=3),
            yaxis="y2",
        )
    )
    fig_dual.update_layout(
        yaxis=dict(title="Custo (R$)", side="left", showgrid=False),
        yaxis2=dict(title="Qtd. Pessoas", side="right", overlaying="y", showgrid=False),
        legend=dict(x=0.01, y=0.99),
        hovermode="x unified",
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_dual, use_container_width=True)

    # Botão de exportação dos dados macro
    csv_macro = converter_para_csv(df_agrupado)
    st.download_button(
        label="📥 Exportar dados macro (CSV)",
        data=csv_macro,
        file_name="macro_evolucao.csv",
        mime="text/csv",
    )


# ------------------------------------------------------------------------------
# TAB 2: DINÂMICA DE RH
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("🔄 Rotatividade (Turnover)")
    df_turnover = calcular_rotatividade(df_filtered)

    if not df_turnover.empty:
        fig_turn = go.Figure()
        fig_turn.add_trace(
            go.Bar(
                x=df_turnover["data_base"],
                y=df_turnover["Admissões"],
                name="Entradas",
                marker_color="green",
            )
        )
        fig_turn.add_trace(
            go.Bar(
                x=df_turnover["data_base"],
                y=df_turnover["Desligamentos"],
                name="Saídas",
                marker_color="red",
            )
        )
        fig_turn.update_layout(
            barmode="relative", title="Fluxo de Contratações e Exonerações"
        )
        st.plotly_chart(fig_turn, use_container_width=True)
        # Botão de exportação dos dados de turnover logo abaixo do gráfico
        csv_turnover = converter_para_csv(df_turnover)
        st.download_button(
            label="📥 Exportar dados de rotatividade (CSV)",
            data=csv_turnover,
            file_name="rotatividade.csv",
            mime="text/csv",
        )
    else:
        st.info("Selecione um período maior que 1 mês para ver a rotatividade.")

    st.markdown("---")
    c_alert, c_export = st.columns([3, 1])
    c_alert.subheader("🚨 Progressões de Carreira (> 20%)")

    df_sorted = df_filtered.sort_values(["nome", "data_base"])
    df_sorted["salario_anterior"] = df_sorted.groupby("nome")[
        "rendimento_liquido"
    ].shift(1)
    df_sorted["delta_perc"] = (
        (df_sorted["rendimento_liquido"] - df_sorted["salario_anterior"])
        / df_sorted["salario_anterior"]
    ) * 100

    progredidos = df_sorted[
        (df_sorted["delta_perc"] > 20) & (df_sorted["rendimento_liquido"] > 5000)
    ].sort_values("delta_perc", ascending=False)

    if not progredidos.empty:
        csv_progredidos = converter_para_csv(
            progredidos[
                [
                    "data_base",
                    "nome",
                    "cargo",
                    "salario_anterior",
                    "rendimento_liquido",
                    "delta_perc",
                ]
            ]
        )
        c_export.download_button(
            label="⚠️ Baixar Relatório",
            data=csv_progredidos,
            file_name="progressoes_carreira.csv",
            mime="text/csv",
        )
        st.dataframe(
            progredidos[
                [
                    "data_base",
                    "nome",
                    "cargo",
                    "salario_anterior",
                    "rendimento_liquido",
                    "delta_perc",
                ]
            ].style.format(
                {
                    "salario_anterior": "R$ {:.2f}",
                    "rendimento_liquido": "R$ {:.2f}",
                    "delta_perc": "{:.1f}%",
                }
            )
        )
    else:
        st.success("Nenhuma anomalia de aumento detectada.")

# ------------------------------------------------------------------------------
# TAB 3: CLÃS
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("🏰 Sobrenomes Comuns")
    ignorar = [
        "SILVA",
        "SANTOS",
        "OLIVEIRA",
        "SOUZA",
        "LIMA",
        "COSTA",
        "PEREIRA",
        "ALVES",
        "FERREIRA",
        "RODRIGUES",
    ]
    df_clans = df_filtered[~df_filtered["sobrenome"].isin(ignorar)]
    top_clans = (
        df_clans.groupby("sobrenome")["nome"]
        .nunique()
        .sort_values(ascending=False)
        .head(15)
    )
    fig_clan = px.bar(top_clans, orientation="h", color_discrete_sequence=["#6610f2"])
    fig_clan.update_layout(yaxis={"categoryorder": "total ascending"})

    st.plotly_chart(fig_clan, use_container_width=True)
    # Botão de exportação dos dados de clãs
    csv_clans = converter_para_csv(top_clans.reset_index())
    st.download_button(
        label="📥 Exportar dados de sobrenomes (CSV)",
        data=csv_clans,
        file_name="sobrenomes_comuns.csv",
        mime="text/csv",
    )

    st.subheader("💰 Ranking Acumulado")
    ocultar = st.checkbox("Ocultar Deputados", value=True)
    n_top = st.number_input(
        "Nomes no ranking:", min_value=1, max_value=100, value=15, step=1
    )
    df_rank = df_filtered.copy()
    if ocultar:
        df_rank = df_rank[~df_rank["cargo"].str.contains("DEPUTADO", case=False)]
    soma = df_rank.groupby(["nome", "cargo"])["rendimento_liquido"].sum().reset_index()
    fig_rank = px.bar(
        soma.nlargest(int(n_top), "rendimento_liquido"),
        x="rendimento_liquido",
        y="nome",
        orientation="h",
        text_auto=".2s",
        color="cargo",
    )
    fig_rank.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_rank, use_container_width=True)
    # Botão de exportação dos dados de ranking acumulado
    csv_ranking = converter_para_csv(soma.nlargest(int(n_top), "rendimento_liquido"))
    st.download_button(
        label="📥 Exportar ranking acumulado (CSV)",
        data=csv_ranking,
        file_name="ranking_acumulado.csv",
        mime="text/csv",
    )

# ------------------------------------------------------------------------------
# TAB 4: DETETIVE
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("🔍 Investigação Individual")
    nome_sel = st.selectbox("Buscar Servidor:", [""] + sorted(df_raw["nome"].unique()))

    if nome_sel:
        df_pessoa = df_raw[df_raw["nome"] == nome_sel].sort_values("data_base")
        total_meses = df_raw["data_base"].nunique()
        meses_pessoa = df_pessoa["data_base"].nunique()

        badge = (
            "🔰 VETERANO"
            if meses_pessoa >= (total_meses * 0.8)
            else "🆕 NOVATO" if meses_pessoa <= 3 else "🔄 REGULAR"
        )
        st.markdown(f"### {nome_sel} ({badge})")

        # Comparativo
        cargo_atual = df_pessoa.iloc[-1]["cargo"]
        df_media = (
            df_raw[df_raw["cargo"] == cargo_atual]
            .groupby("data_base")["rendimento_liquido"]
            .mean()
            .reset_index()
        )
        df_merged = pd.merge(
            df_pessoa, df_media, on="data_base", how="left", suffixes=("", "_media")
        )

        fig_comp = go.Figure()
        fig_comp.add_trace(
            go.Scatter(
                x=df_merged["data_base"],
                y=df_merged["rendimento_liquido_media"],
                name=f"Média ({cargo_atual})",
                line=dict(color="gray", dash="dash"),
            )
        )
        fig_comp.add_trace(
            go.Scatter(
                x=df_merged["data_base"],
                y=df_merged["rendimento_liquido"],
                name="Servidor",
                mode="lines+markers",
                line=dict(color="blue", width=3),
            )
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        st.dataframe(
            df_pessoa[
                [
                    "data_base",
                    "cargo",
                    "rendimento_liquido",
                    "total_creditos",
                    "total_debitos",
                ]
            ].style.format({"rendimento_liquido": "R$ {:.2f}"})
        )
        # Botão de exportação dos dados individuais
        csv_pessoa = converter_para_csv(
            df_pessoa[
                [
                    "data_base",
                    "cargo",
                    "rendimento_liquido",
                    "total_creditos",
                    "total_debitos",
                ]
            ]
        )
        st.download_button(
            label="📥 Exportar dados do servidor (CSV)",
            data=csv_pessoa,
            file_name=f"dados_{nome_sel.replace(' ', '_')}.csv",
            mime="text/csv",
        )

with tab5:
    st.subheader("🎯 Radar de Anomalias")
    st.info(
        "Este gráfico mostra a distribuição. Pontos muito à direita são salários altos."
    )

    if modo_filtro == "Seleção Rápida (Por Ano)":
        if not df_filtered.empty:
            # Adiciona seletor de mês
            meses_disponiveis = (
                df_filtered["data_base"]
                .dt.to_period("M")
                .drop_duplicates()
                .sort_values()
            )
            meses_str = [str(m) for m in meses_disponiveis]
            mes_sel_str = st.selectbox(
                "Selecione o mês:", options=meses_str, index=len(meses_str) - 1
            )
            mes_sel = pd.Period(mes_sel_str)
            # Filtra para o mês selecionado
            mask_mes = df_filtered["data_base"].dt.to_period("M") == mes_sel
            df_mes = df_filtered[mask_mes]

            if not df_mes.empty:
                fig_scatter = px.scatter(
                    df_mes,
                    x="rendimento_liquido",
                    y="cargo",
                    hover_data=["nome"],
                    color="rendimento_liquido",
                    color_continuous_scale="Bluered",
                )
                fig_scatter.update_yaxes(
                    showticklabels=False
                )  # Esconde nomes dos cargos pra não poluir
                st.plotly_chart(fig_scatter, use_container_width=True)
                # Botão de exportação dos dados de anomalias
                csv_anomalias = converter_para_csv(df_mes)
                st.download_button(
                    label="📥 Exportar dados do mês selecionado (CSV)",
                    data=csv_anomalias,
                    file_name=f"anomalias_{mes_sel_str}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("Não há dados para o mês selecionado.")
        else:
            st.warning("Não há dados para o mês selecionado.")
