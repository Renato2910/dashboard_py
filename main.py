import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt

from backend import (
    criar_banco,
    popular_banco_com_csv,
    calcular_total_vendas,
    calcular_quantidade_total,
    calcular_ticket_medio,
    produto_mais_vendido,
    get_connection
)

DB_PATH = "vendas_acai.db"
CSV_PATH = "dados_vendas_acai.csv"

st.set_page_config(
    page_title="Dashboard de Vendas - Açaíteria",
    layout="wide",
    initial_sidebar_state="expanded"
)

criar_banco(DB_PATH)

conn_check = get_connection(DB_PATH)
cursor = conn_check.cursor()
cursor.execute("SELECT COUNT(*) FROM vendas;")
count = cursor.fetchone()[0]
conn_check.close()

if count == 0:
    popular_banco_com_csv(DB_PATH, CSV_PATH)

@st.cache_data(ttl=300)
def carregar_dados(db_path: str) -> pd.DataFrame:
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM vendas;",
        conn,
        parse_dates=['data_venda']
    )
    conn.close()
    df = df.sort_values('data_venda').reset_index(drop=True)
    return df

df_vendas = carregar_dados(DB_PATH)

st.sidebar.header("Filtros")
st.sidebar.divider()

data_min = df_vendas['data_venda'].min().date()
data_max = df_vendas['data_venda'].max().date()

datas_selecionadas = st.sidebar.slider(
    "Período de Venda:",
    min_value=data_min,
    max_value=data_max,
    value=(data_min, data_max),
    format="YYYY-MM-DD"
)
inicio_date, fim_date = datas_selecionadas
dt_inicio = datetime.combine(inicio_date, datetime.min.time())
dt_fim    = datetime.combine(fim_date,   datetime.max.time())

formas_unicas = df_vendas['forma_pagamento'].dropna().unique().tolist()
formas_disponiveis = ["Todos"] + sorted(formas_unicas)
forma_pag_sel = st.sidebar.selectbox("Forma de Pagamento:", formas_disponiveis)

st.sidebar.divider()

categorias_unicas = df_vendas['categoria'].dropna().unique().tolist()
categorias_unicas = sorted(categorias_unicas)
categorias_selecionadas = st.sidebar.multiselect(
    "Categorias:",
    options=categorias_unicas,
    default=categorias_unicas
)

# 4) Produto
produtos_unicos = df_vendas['produto'].dropna().unique().tolist()
produtos_unicos = sorted(produtos_unicos)
produtos_selecionados = st.sidebar.multiselect(
    "Produtos:",
    options=produtos_unicos,
    default=produtos_unicos
)

st.sidebar.divider()

df_filtrado = df_vendas[
    (df_vendas['data_venda'] >= dt_inicio) &
    (df_vendas['data_venda'] <= dt_fim)
].copy()

if forma_pag_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['forma_pagamento'] == forma_pag_sel]

df_filtrado = df_filtrado[df_filtrado['categoria'].isin(categorias_selecionadas)]
df_filtrado = df_filtrado[df_filtrado['produto'].isin(produtos_selecionados)]

st.title("📊 Dashboard de Vendas - Açaíteria")

tab1, tab2 = st.tabs([
    "🏠 Dashboard",
    "📈 Análises Detalhadas",
])

# ---------------------------- Aba 1: Dashboard ----------------------------
with tab1:
    st.header("Visão Geral")

    total_vendas = calcular_total_vendas(df_filtrado)
    quantidade_total = calcular_quantidade_total(df_filtrado)
    ticket_medio = calcular_ticket_medio(df_filtrado)
    produto_mais_vendido_total = produto_mais_vendido(df_filtrado)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="💰 Total de Vendas",     value=f"R$ {total_vendas:,.2f}")
    c2.metric(label="📦 Quantidade Vendida",   value=f"{quantidade_total:,}")
    c3.metric(label="🎯 Ticket Médio",         value=f"R$ {ticket_medio:,.2f}")
    c4.metric(label="🥇 Produto Mais Vendido", value=f"{produto_mais_vendido_total}")

    st.divider()

    st.subheader("Evolução de Vendas ao Longo do Tempo")
    df_evol = df_filtrado.copy()
    df_evol['dia'] = df_evol['data_venda'].dt.date
    vendas_por_dia = (
        df_evol
        .groupby('dia')['valor_total']
        .sum()
        .reset_index()
        .rename(columns={'dia': 'Data', 'valor_total': 'Receita'})
    )
    st.line_chart(
        data=vendas_por_dia.set_index('Data'),
        use_container_width=True,
        color="#110B47"
    )

    st.divider()

    st.subheader("Receita por Categoria")
    vendas_categoria = (
        df_filtrado
        .groupby('categoria')['valor_total']
        .sum()
        .reset_index()
        .sort_values('valor_total', ascending=False)
    )
    vendas_categoria = vendas_categoria.rename(columns={'categoria': 'Categoria', 'valor_total': 'Receita'})
    vendas_categoria = vendas_categoria.set_index('Categoria')
    st.bar_chart(
        data=vendas_categoria,
        use_container_width=True,
        color="#110B47"
    )
    
    st.divider()

# ---------------------------- Aba 2: Análises Detalhadas ----------------------------
with tab2:
    st.header("📈 Análises Detalhadas")

    col1, col2, col3 = st.columns(3)
    with col1:
        num_clientes = df_filtrado['cliente'].nunique()
        st.metric("👥 Clientes Únicos", value=f"{num_clientes}")
    with col2:
        if "Pix" in df_filtrado['forma_pagamento'].unique():
            ticket_pix = df_filtrado[df_filtrado['forma_pagamento'] == "Pix"]['valor_total'].mean()
        else:
            ticket_pix = 0.0
        st.metric("🎫 Ticket Médio (Pix)", value=f"R$ {ticket_pix:,.2f}")
    with col3:
        df_cartoes = df_filtrado[df_filtrado['forma_pagamento'].str.contains("Cartão", na=False)]
        if not df_cartoes.empty:
            ticket_cartao = df_cartoes['valor_total'].mean()
        else:
            ticket_cartao = 0.0
        st.metric("🎫 Ticket Médio (Cartão)", value=f"R$ {ticket_cartao:,.2f}")

    st.divider()

    st.subheader("Vendas por Hora do Dia")
    df_hora = df_filtrado.copy()
    df_hora['Hora'] = df_hora['data_venda'].dt.hour
    vendas_hora = (
        df_hora
        .groupby('Hora')['valor_total']
        .sum()
        .reset_index()
        .rename(columns={'valor_total': 'Receita'})
    )
    vendas_hora['Horas'] = vendas_hora['Hora'].apply(lambda x: f"{x:02d}:00")
    vendas_hora = vendas_hora.set_index('Horas')

    st.line_chart(
        data=vendas_hora[['Receita']],
        use_container_width=True,
        height=300,
        color="#110B47"
    )
    
    st.divider()

    st.subheader("Receita por Produto Dentro de Categoria Selecionada")
    categoria_para_produto = st.selectbox("Escolha uma Categoria:", options=categorias_unicas)
    produtos_disponiveis_na_categoria = (
        df_vendas[df_vendas['categoria'] == categoria_para_produto]['produto']
        .dropna()
        .unique()
        .tolist()
    )
    produtos_disponiveis_na_categoria.sort()
    produtos_sel_dinamico = st.multiselect(
        "Escolha Produto(s) (dentro da categoria):",
        options=produtos_disponiveis_na_categoria,
        default=produtos_disponiveis_na_categoria
    )
    df_cat_prod = df_filtrado[df_filtrado['categoria'] == categoria_para_produto].copy()
    df_cat_prod = df_cat_prod[df_cat_prod['produto'].isin(produtos_sel_dinamico)]

    if not df_cat_prod.empty:
        receita_por_prod = (
            df_cat_prod
            .groupby('produto')['valor_total']
            .sum()
            .reset_index()
            .sort_values('valor_total', ascending=False)
            .rename(columns={'produto': 'Produto', 'valor_total': 'Receita'})
        )
        receita_por_prod = receita_por_prod.set_index('Produto')
        st.bar_chart(
            data=receita_por_prod,
            use_container_width=True,
            height=350,
            color="#110B47"
        )
    else:
        st.info("Não há vendas para esta combinação de categoria e produto no período selecionado.")

    st.divider()

    st.subheader("Tabela Dinâmica: Receita por Cliente x Categoria")
    pivot = (
        df_filtrado
        .pivot_table(
            index='cliente',
            columns='categoria',
            values='valor_total',
            aggfunc='sum',
            fill_value=0
        )
    )
    st.dataframe(pivot)
    csv = pivot.to_csv().encode('utf-8')
    st.download_button(
        label="⬇️ Baixar Tabela como CSV",
        data=csv,
        file_name='tabela_dinamica_cliente_categoria.csv',
        mime='text/csv'
    )