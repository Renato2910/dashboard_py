import streamlit as st
import pandas as pd
from datetime import datetime
import io
import matplotlib.pyplot as plt

from backend import (
    criar_banco,
    popular_banco_com_csv,
    calcular_total_vendas,
    calcular_quantidade_total,
    calcular_ticket_medio,
    produto_mais_vendido,
    get_connection,
    filtrar_vendas,
    resumo_indicadores,
    pivot_receita_cliente_categoria
)

DB_PATH = "vendas_acai.db"
CSV_PATH = "dados_vendas_acai.csv"

st.set_page_config(page_title="Dashboard de Vendas - Açaíteria", layout="wide", initial_sidebar_state="expanded")

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
    df = pd.read_sql_query("SELECT * FROM vendas;", conn, parse_dates=['data_venda'])
    conn.close()
    return df.sort_values('data_venda').reset_index(drop=True)

df_vendas = carregar_dados(DB_PATH)

st.sidebar.header("Filtros")
st.sidebar.divider()

data_min = df_vendas['data_venda'].min().date()
data_max = df_vendas['data_venda'].max().date()

formas_unicas = df_vendas['forma_pagamento'].dropna().unique().tolist()
formas_disponiveis = ["Todos"] + sorted(formas_unicas)

categorias_unicas = sorted(df_vendas['categoria'].dropna().unique().tolist())
produtos_unicos   = sorted(df_vendas['produto'].dropna().unique().tolist())

if st.sidebar.button("🔄 Resetar Filtros"):
    st.session_state['intervalo_selecionado']   = (data_min, data_max)
    st.session_state['dia_selecionado']        = data_min
    st.session_state['forma_pag_sel']          = "Todos"
    st.session_state['categorias_selecionadas']= categorias_unicas
    st.session_state['produtos_selecionados']  = produtos_unicos

st.sidebar.divider()

modo_data = st.sidebar.radio(
    "Seleção de Data:",
    options=["Período de Dias", "Dia Único"],
    index=0
)

if modo_data == "Período de Dias":
    default_intervalo = st.session_state.get("intervalo_selecionado", (data_min, data_max))
    datas_selecionadas = st.sidebar.date_input(
        "Período de Venda:",
        value=default_intervalo,
        min_value=data_min,
        max_value=data_max,
        format="DD/MM/YYYY",
        key="intervalo_selecionado"
    )

    # Tenta desempacotar dois dias; se vier apenas um, exibe aviso e usa como único dia
    if isinstance(datas_selecionadas, (list, tuple)) and len(datas_selecionadas) == 2:
        inicio_date, fim_date = datas_selecionadas
    else:
        st.warning(
            "Você escolheu apenas um dia, selecione outro para verificar os dados."
        )
        inicio_date = fim_date = datas_selecionadas

else:  # modo_data == "Dia Único"
    default_dia = st.session_state.get("dia_selecionado", data_min)
    dia_selecionado = st.sidebar.date_input(
        "Selecione o Dia:",
        value=default_dia,
        min_value=data_min,
        max_value=data_max,
        format="DD/MM/YYYY",
        key="dia_selecionado"
    )
    inicio_date = fim_date = dia_selecionado

dt_inicio = datetime.combine(inicio_date, datetime.min.time())
dt_fim    = datetime.combine(fim_date,   datetime.max.time())

forma_pag_sel = st.sidebar.selectbox(
    "Forma de Pagamento:",
    options=formas_disponiveis,
    index=formas_disponiveis.index(st.session_state.get("forma_pag_sel", "Todos")),
    key="forma_pag_sel"
)

st.sidebar.divider()

categorias_selecionadas = st.sidebar.multiselect(
    "Categorias:",
    options=categorias_unicas,
    default=st.session_state.get("categorias_selecionadas", categorias_unicas),
    key="categorias_selecionadas"
)

produtos_selecionados = st.sidebar.multiselect(
    "Produtos:",
    options=produtos_unicos,
    default=st.session_state.get("produtos_selecionados", produtos_unicos),
    key="produtos_selecionados"
)

st.sidebar.divider()


df_filtrado = filtrar_vendas(
    df_vendas,
    dt_inicio,
    dt_fim,
    forma_pag_sel,
    categorias_selecionadas,
    produtos_selecionados
)

st.title("📊 Dashboard de Vendas - Açaíteria")

tab1, tab2 = st.tabs(["🏠 Dashboard", "📈 Análises Detalhadas"])

with tab1:
    st.header("Visão Geral")

    total_vendas = calcular_total_vendas(df_filtrado)
    quantidade_total = calcular_quantidade_total(df_filtrado)
    ticket_medio = calcular_ticket_medio(df_filtrado)
    produto_mais_vendido_total = produto_mais_vendido(df_filtrado)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="💰 Total de Vendas", value=f"R$ {total_vendas:,.2f}")
    c2.metric(label="📦 Quantidade Vendida", value=f"{quantidade_total:,}")
    c3.metric(label="🎯 Ticket Médio", value=f"R$ {ticket_medio:,.2f}")
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
    st.line_chart(data=vendas_por_dia.set_index('Data'), use_container_width=True, color="#110B47")

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
    st.bar_chart(data=vendas_categoria, use_container_width=True, color="#110B47")

    st.subheader("📋 Resumo de Indicadores Gerais (com filtro de mês)")

    df_mes_ano = df_filtrado.copy()
    df_mes_ano['mes_ano'] = df_mes_ano['data_venda'].dt.to_period('M')

    meses_unicos = sorted(df_mes_ano['mes_ano'].dropna().unique().tolist())
    meses_str = [str(m) for m in meses_unicos]
    opcoes_meses = ["Todos"] + meses_str

    mes_selecionado = st.selectbox("Selecione o mês para gerar o resumo:", options=opcoes_meses, index=0)

    if mes_selecionado != "Todos":
        periodo = pd.Period(mes_selecionado, freq="M")
        df_summary = df_mes_ano[df_mes_ano['mes_ano'] == periodo].copy()
    else:
        df_summary = df_filtrado.copy()

    indicadores = resumo_indicadores(df_summary)

    dia_maior = indicadores['dia_maior_faturamento']
    dia_str = str(dia_maior) if dia_maior else ""

    resumo_dict = {
        "Métrica": [
            "Total de Vendas (R$)",
            "Quantidade Total Vendida",
            "Ticket Médio (R$)",
            "Clientes Únicos",
            "Produto Mais Vendido",
            "Categoria que Mais Faturou",
            "Forma de Pagamento Mais Utilizada",
            "Venda Média Diária (R$)",
            "Dia de Maior Faturamento"
        ],
        "Valor": [
            f"R$ {indicadores['total_vendas']:,.2f}",
            f"{indicadores['quantidade_total']:,}",
            f"R$ {indicadores['ticket_medio']:,.2f}",
            f"{indicadores['num_clientes']:,}",
            indicadores['produto_mais_vendido'],
            indicadores['categoria_mais_faturou'],
            indicadores['forma_mais_usada'],
            f"R$ {indicadores['venda_media_diaria']:,.2f}",
            dia_str
        ]
    }
    df_resumo = pd.DataFrame(resumo_dict)

    st.table(df_resumo)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_resumo.to_excel(writer, index=False, sheet_name="Resumo")
    buffer.seek(0)

    st.download_button(
        label="⬇️ Exportar Resumo como Excel",
        data=buffer,
        file_name=f'resumo_indicadores_{mes_selecionado}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

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
    st.line_chart(data=vendas_hora[['Receita']], use_container_width=True, height=300, color="#110B47")

    st.divider()

    st.subheader("Receita por Produto Dentro de Categoria Selecionada")
    categoria_para_produto = st.selectbox("Escolha uma Categoria:", options=categorias_unicas)
    produtos_disponiveis_na_categoria = sorted(df_vendas[df_vendas['categoria'] == categoria_para_produto]['produto'].dropna().unique().tolist())
    produtos_sel_dinamico = st.multiselect("Escolha Produto(s) (dentro da categoria):", options=produtos_disponiveis_na_categoria, default=produtos_disponiveis_na_categoria)
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
        st.bar_chart(data=receita_por_prod, use_container_width=True, height=350, color="#110B47")
    else:
        st.info("Não há vendas para esta combinação de categoria e produto no período selecionado.")

    st.divider()

    st.subheader("Top 5 Produtos Mais Vendidos")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Por Quantidade (Top 5)**")
        top_qtd = (
            df_filtrado
            .groupby('produto')['quantidade']
            .sum()
            .reset_index()
            .sort_values('quantidade', ascending=False)
            .head(5)
            .rename(columns={'quantidade': 'Quantidade Vendida'})
        )
        top_qtd = top_qtd.set_index('produto')
        st.bar_chart(data=top_qtd['Quantidade Vendida'], use_container_width=True, color="#110B47")

    with col2:
        st.markdown("**Por Receita (Top 5) – Gráfico de Pizza**")

        top_rev = (
            df_filtrado
            .groupby('produto')['valor_total']
            .sum()
            .reset_index()
            .sort_values('valor_total', ascending=False)
            .head(5)
            .rename(columns={'valor_total': 'Receita Total (R$)'})
        )

        fig, ax = plt.subplots(figsize=(3, 3), facecolor='none')
        ax.set_facecolor('none')

        produtos = top_rev['produto']
        receitas = top_rev['Receita Total (R$)']

        cores = ['#BBA5CD', '#BF30B6', '#73346F', '#2F1740', '#744397']

        wedges, textos, autotextos = ax.pie(
            receitas,
            labels=None,  
            autopct='%1.1f%%',
            textprops={'fontsize': 6, 'color': '#FFFFFF'},
            startangle=90,
            counterclock=False,
            colors=cores
        )
        ax.axis('equal')

        ax.legend(
            wedges,                
            produtos,             
            title="Produto",       
            loc="center left",    
            bbox_to_anchor=(1, 0, 0.5, 1),
            frameon=False,        
            labelcolor='black',    
            fontsize=8
        )
        st.pyplot(fig)

    st.divider()

    st.subheader("Receita por Cliente x Categoria")
    pivot = pivot_receita_cliente_categoria(df_filtrado)
    st.dataframe(pivot)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pivot.to_excel(writer, sheet_name="Receita_Cliente_Categoria")
    buffer.seek(0)

    st.download_button(
        label="⬇️ Baixar Tabela como Excel",
        data=buffer,
        file_name='tabela_dinamica_cliente_categoria.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )