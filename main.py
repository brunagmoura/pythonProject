import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# ------------------------------
# Configurações gerais (responsividade)
# ------------------------------
st.set_page_config(page_title="Emendas Parlamentares em grandes números", layout="wide")

# Opcional: limitar largura máxima do conteúdo no desktop
st.markdown("""
<style>
/* Centraliza e limita a largura do corpo para não ficar exagerado em telas muito largas */
.block-container { max-width: 1200px; padding-top: 1rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# Altair responsivo
alt.data_transformers.disable_max_rows()
alt.renderers.set_embed_options(actions=False)
AUTOSIZE = alt.AutoSizeParams(type="fit", contains="padding")

# Largura por categoria (ajuste fino se quiser)
STEP_CHART1 = 34     # ~px por "Ano" no gráfico 1
STEP_FACET2 = 26     # ~px por "Ano" em cada faceta do gráfico 2
STEP_FACET3 = 28     # ~px por "Modalidade" no gráfico 3

# Alturas (ajuste fino se quiser)
HEIGHT_CHART1 = 280
HEIGHT_FACET2 = 120
HEIGHT_FACET3 = 140

# ------------------------------
# Carregar dados
# ------------------------------
def carregar_dados_emendas():
    url = "http://191.252.193.11:5000/emendas"
    df = pd.read_json(url)
    return df

# ------------------------------
# Transformações de variáveis
# ------------------------------
def aplicar_transformacoes(df):
    # tipo_emenda
    df["tipo_emenda"] = df.apply(
        lambda row: (
            "Bancada" if row["ResultadoPrimario_cod"] == 7 else
            "Comissão" if row["ResultadoPrimario_cod"] == 8 else
            "Individual - transferência especial (Pix)" if row["ResultadoPrimario_cod"] == 6 and row["Acao_cod"] == "0EC2" else
            "Individual - finalidade definida" if row["ResultadoPrimario_cod"] == 6 else
            None
        ),
        axis=1
    )

    # Reclassificar ModalidadeAplicacao_desc
    modalidades_outras = [
        "Aplicação Direta Decorrente de Operação entre Órgãos, Fundos e Entidades Integrantes dos Orçamentos F/S",
        "Execução Orçamentária Delegada a Estados e ao Distrito Federal",
        "Execução Orçamentária Delegada a Municípios",
        "Transferências a Consórcios Públicos mediante contrato de rateio",
        "Transferências a Instituições Multigovernamentais Nacionais",
        "Transferências ao Exterior"
    ]

    mapa_modalidade = {
        "Transferências a Estados e ao Distrito Federal": "Transf. Estados e DF",
        "Transferências a Estados e ao Distrito Federal - Fundo a Fundo": "Transf. Estados e DF - F/F",
        "Transferências a Municípios": "Transf. a Municípios",
        "Transferências a Municípios - Fundo a Fundo": "Transf. a Municípios - F/F",
        "Transferências a Instituições Privadas sem Fins Lucrativos": "Transf. a Inst. Priv. s/ fins lucr",
        "A DEFINIR": "A definir"
    }

    df["ModalidadeAplicacao_desc"] = df["ModalidadeAplicacao_desc"].replace(mapa_modalidade)
    df["ModalidadeAplicacao_desc"] = df["ModalidadeAplicacao_desc"].apply(
        lambda x: "Outras" if x in modalidades_outras else x
    )
    return df

st.title("Emendas Parlamentares em grandes números (2022–2025)")

with st.spinner("Carregando dados..."):
    df = carregar_dados_emendas()

df = aplicar_transformacoes(df)
st.success("Dados carregados com sucesso!")

# Paletas
cores_tipo_emenda = {
    "Bancada": "#1B5DA3",
    "Comissão": "#77B5E5",
    "Individual - finalidade definida": "#E6332A",
    "Individual - transferência especial (Pix)": "#FCA3A0"
}
ordem_facetas = [
    "Bancada",
    "Comissão",
    "Individual - finalidade definida",
    "Individual - transferência especial (Pix)"
]

# ---------------------------
# 1) Evolução ResultadoPrimario_desc × Ano
# ---------------------------
st.header("1. Tipo de emenda parlamentar")

df1 = (
    df.groupby(["Ano", "tipo_emenda"], as_index=False)
      .agg({"loa_mais_credito": "sum"})
)

df1["dotacao"] = df1["loa_mais_credito"].apply(
    lambda x: f'{x / 1e9:,.1f} bi'.replace(",", "X").replace(".", ",").replace("X", ".")
)
df1["tipo_emenda"] = pd.Categorical(df1["tipo_emenda"], categories=ordem_facetas, ordered=True)

# Barras agrupadas por tipo (xOffset) — responsivo com Step
bar1 = (
    alt.Chart(df1)
    .mark_bar()
    .encode(
        x=alt.X("Ano:O", title="", sort=sorted(df1["Ano"].unique()), axis=alt.Axis(labelAngle=0, labelLimit=90)),
        y=alt.Y("sum(loa_mais_credito):Q", axis=alt.Axis(title=None, labels=False, ticks=False)),
        color=alt.Color(
            "tipo_emenda:N",
            title="Tipo de Emenda",
            scale=alt.Scale(
                domain=ordem_facetas,
                range=[cores_tipo_emenda[t] for t in ordem_facetas]
            ),
            legend=alt.Legend(
                orient="top",
                direction="vertical",
                columns=4,
                labelFontSize=9.5,
                titleFontSize=12
            )
        ),
        xOffset=alt.X("tipo_emenda:N", sort=ordem_facetas),
        tooltip=[
            alt.Tooltip("Ano:O", title="Ano"),
            alt.Tooltip("tipo_emenda:N", title="Tipo"),
            alt.Tooltip("dotacao:N", title="Dotação")
        ]
    )
)

# Texto (mesma agregação/posições)
text1 = (
    alt.Chart(df1)
    .mark_text(align="center", dy=-6, fontSize=12)
    .encode(
        x=alt.X("Ano:O", sort=sorted(df1["Ano"].unique())),
        y=alt.Y("sum(loa_mais_credito):Q"),
        xOffset=alt.X("tipo_emenda:N", sort=ordem_facetas),
        text=alt.Text("dotacao:N")
    )
)

chart1 = alt.layer(bar1, text1, data=df1).properties(
    title="Dotação atualizada (R$ bilhões) por tipo de emenda parlamentar",
    width=alt.Step(STEP_CHART1),
    height=HEIGHT_CHART1
).configure_view(stroke=None).properties(autosize=AUTOSIZE)

st.altair_chart(chart1, use_container_width=True)

# ---------------------------
# 2) Evolução Funcao_desc por ResultadoPrimario_desc × Ano
# ---------------------------
st.header("2. Função de governo")

df2 = (
    df.groupby(["Ano", "Funcao_desc", "tipo_emenda"], as_index=True)
      .agg({"loa_mais_credito": "sum"})
      .unstack("tipo_emenda")
      .fillna(0)
      .stack()
      .reset_index()
      .rename(columns={0: "loa_mais_credito"})
)

tipo_selecionado = st.selectbox("Selecione o tipo de emenda:", df2["tipo_emenda"].dropna().unique())

df_tipo = df2[df2["tipo_emenda"] == tipo_selecionado].copy()
df_tipo = df_tipo[df_tipo["loa_mais_credito"] > 0]
df_tipo["dotacao"] = df_tipo["loa_mais_credito"].apply(
    lambda x: f'{x / 1e6:,.1f} mi'.replace(",", "X").replace(".", ",").replace("X", ".")
)

cor_emenda = cores_tipo_emenda.get(tipo_selecionado, "#333333")

unit2 = (
    alt.Chart(df_tipo)
    .encode(
        x=alt.X("Ano:O", title="", axis=alt.Axis(labelAngle=0, labelLimit=90)),
        y=alt.Y("sum(loa_mais_credito):Q", axis=alt.Axis(title=None, labels=False, ticks=False))
    )
)

bar2 = unit2.mark_bar(color=cor_emenda)
text2 = unit2.mark_text(align="center", dy=-8, fontSize=9).encode(text=alt.Text("dotacao:N"))

titulo = f"Dotação atualizada (R$ milhões) por função de governo para as emendas {tipo_selecionado}"

chart_funcao = (
    (bar2 + text2)
    .properties(width=alt.Step(STEP_FACET2), height=HEIGHT_FACET2)  # largura/altura de cada faceta
    .facet(
        facet=alt.Facet("Funcao_desc:N", title=None, header=alt.Header(labelFontWeight="bold", labelLimit=140)),
        columns=7,
        title=titulo
    )
    .resolve_scale(y='shared')
    .properties(autosize=AUTOSIZE)
    .configure_view(stroke=None)
)

st.altair_chart(chart_funcao, use_container_width=True)

# ---------------------------
# 3) Evolução ModalidadeAplicacao_desc por ResultadoPrimario_desc × Ano
# ---------------------------
st.header("3. Modalidade de Aplicação")

df3 = (
    df.groupby(["Ano", "tipo_emenda", "ModalidadeAplicacao_desc"], as_index=True)
      .agg({"loa_mais_credito": "sum"})
      .unstack("ModalidadeAplicacao_desc")
      .fillna(0)
      .stack()
      .reset_index()
      .rename(columns={0: "loa_mais_credito"})
)

df3 = df3[df3["loa_mais_credito"] > 0].copy()
df3["dotacao"] = df3["loa_mais_credito"].apply(
    lambda x: f'{x / 1e6:,.1f} mi'.replace(",", "X").replace(".", ",").replace("X", ".")
)

cores_modalidades = {
    "Transf. Estados e DF": "#4578B5",
    "Transf. a Municípios": "#6BAAE1",
    "Transf. Estados e DF - F/F": "#BDBB45",
    "Transf. a Municípios - F/F": "#E8E379",
    "Transf. a Inst. Priv. s/ fins lucr": "#9355D3",
    "Aplicações Diretas": "#7EB37E",
    "Outras": "#A0B6C8",
    "A definir": "#999999"
}
modalidades_ordem = list(cores_modalidades.keys())

unit3 = (
    alt.Chart(df3)
    .encode(
        x=alt.X("ModalidadeAplicacao_desc:N",
                sort=modalidades_ordem,
                axis=alt.Axis(title=None, labels=False, ticks=False, labelLimit=110)),
        y=alt.Y("sum(loa_mais_credito):Q", axis=alt.Axis(title=None, labels=False, ticks=False)),
        color=alt.Color(
            "ModalidadeAplicacao_desc:N",
            title="Modalidade de Aplicação",
            scale=alt.Scale(domain=modalidades_ordem, range=[cores_modalidades[k] for k in modalidades_ordem]),
            legend=alt.Legend(orient="top", direction="horizontal", columns=4, labelFontSize=9, titleFontSize=12)
        ),
        tooltip=[
            alt.Tooltip("Ano:O", title="Ano"),
            alt.Tooltip("tipo_emenda:N", title="Tipo"),
            alt.Tooltip("ModalidadeAplicacao_desc:N", title="Modalidade"),
            alt.Tooltip("dotacao:N", title="Dotação")
        ]
    )
)

bar3 = unit3.mark_bar()
text3 = unit3.mark_text(align="center", dy=-8, fontSize=9).encode(text=alt.Text("dotacao:N"))

chart3 = (
    (bar3 + text3)
    .properties(width=alt.Step(STEP_FACET3), height=HEIGHT_FACET3)  # tamanho do unit-chart
    .facet(
        row=alt.Row("Ano:O", title=None, sort=sorted(df3["Ano"].unique()),
                    header=alt.Header(labelFontWeight="bold")),
        column=alt.Column("tipo_emenda:N", title=None,
                          header=alt.Header(labelFontWeight="bold")),
        title="Dotação atualizada (R$ milhões) por modalidade de aplicação"
    )
    .resolve_scale(y='shared')
    .properties(autosize=AUTOSIZE)
    .configure_view(stroke=None)
)

st.altair_chart(chart3, use_container_width=True)

# ---------------------------
# 4) Comparação de loa_mais_credito, empenhado e pago em 2025
# ---------------------------
st.header("4. Execução orçamentária (2025)")
st.info("Buscando algum programa específico? Tente filtrar pela lupa da tabela!")

def formatar_valor_br(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def barra_visual(pct):
    if pd.isna(pct):
        return ""
    blocos = int(pct // 10)
    return "▰" * blocos + "▱" * (10 - blocos)

df_2025 = df[df["Ano"] == 2025].copy()

tipos_disponiveis = df_2025["tipo_emenda"].dropna().unique()
tipo_selecionado = st.selectbox("Selecione o tipo de emenda:", tipos_disponiveis)

criterio = st.selectbox("Ordenar por:", options=["Dotação", "% Empenhado", "% Pago"])
coluna_ordenacao = {"Dotação": "Dotacao_mi", "% Empenhado": "% Empenhado (num)", "% Pago": "% Pago (num)"}[criterio]

df_emenda = df_2025[df_2025["tipo_emenda"] == tipo_selecionado].copy()
df_emenda["Ação Governamental"] = df_emenda["Acao_cod"] + " - " + df_emenda["Acao_desc"]

df4 = (
    df_emenda
    .groupby("Ação Governamental", as_index=False)
    .agg({"loa_mais_credito": "sum", "empenhado": "sum", "pago": "sum"})
)

df4["% Empenhado (num)"] = (df4["empenhado"] / df4["loa_mais_credito"]) * 100
df4["% Pago (num)"] = (df4["pago"] / df4["loa_mais_credito"]) * 100
df4["% Empenhado"] = df4["% Empenhado (num)"].apply(barra_visual)
df4["% Pago"] = df4["% Pago (num)"].apply(barra_visual)

df4["Dotacao_mi"] = df4["loa_mais_credito"] / 1e6
df4["Empenhado_mi"] = df4["empenhado"] / 1e6
df4["Pago_mi"] = df4["pago"] / 1e6

df4 = df4.sort_values(coluna_ordenacao, ascending=False).reset_index(drop=True)

df4["Dotação (mi)"] = df4["Dotacao_mi"].apply(formatar_valor_br)
df4["Empenhado (mi)"] = df4["Empenhado_mi"].apply(formatar_valor_br)
df4["Pago (mi)"] = df4["Pago_mi"].apply(formatar_valor_br)

df_final = df4[["Ação Governamental", "Dotação (mi)", "Empenhado (mi)", "Pago (mi)", "% Empenhado", "% Pago"]]

st.dataframe(df_final, use_container_width=True)

hoje = datetime.now().strftime("%d/%m/%Y")
st.warning(f"Última atualização em {hoje}")

st.markdown("---")
st.markdown("""
🔗 Este aplicativo utiliza os dados obtidos via pacote [**orcamentoBR**](https://cran.r-project.org/web/packages/orcamentoBR/index.html).

📆 Os dados se referem ao dia anterior à atualização.
""")
