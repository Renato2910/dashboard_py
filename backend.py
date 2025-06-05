import sqlite3
import pandas as pd
from datetime import datetime

def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    return conn

def criar_banco(db_path: str) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_venda TIMESTAMP NOT NULL,
            cliente TEXT NOT NULL,
            produto TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            forma_pagamento TEXT NOT NULL,
            preco_unitario REAL NOT NULL,
            valor_total REAL NOT NULL,
            categoria TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

def popular_banco_com_csv(db_path: str, csv_path: str) -> None:
    df = pd.read_csv(csv_path, parse_dates=['data_venda'])
    df['quantidade'] = df['quantidade'].astype(int)
    df['preco_unitario'] = df['preco_unitario'].astype(float)
    df['valor_total'] = df['valor_total'].astype(float)
    df['forma_pagamento'] = df['forma_pagamento'].astype(str)
    df['cliente'] = df['cliente'].astype(str)
    df['produto'] = df['produto'].astype(str)
    df['categoria'] = df['categoria'].astype(str)
    conn = get_connection(db_path)
    df.to_sql('vendas', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()

def calcular_total_vendas(df: pd.DataFrame) -> float:
    return float(df['valor_total'].sum())

def calcular_quantidade_total(df: pd.DataFrame) -> int:
    return int(df['quantidade'].sum())

def calcular_ticket_medio(df: pd.DataFrame) -> float:
    return float(df['valor_total'].mean()) if not df.empty else 0.0

def produto_mais_vendido(df: pd.DataFrame) -> str:
    return df.groupby('produto')['quantidade'].sum().idxmax() if not df.empty else ""

def filtrar_vendas(
    df: pd.DataFrame,
    inicio: datetime,
    fim: datetime,
    forma_pagamento: str,
    categorias: list,
    produtos: list
) -> pd.DataFrame:
    df_f = df[(df['data_venda'] >= inicio) & (df['data_venda'] <= fim)].copy()
    if forma_pagamento != "Todos":
        df_f = df_f[df_f['forma_pagamento'] == forma_pagamento]
    df_f = df_f[df_f['categoria'].isin(categorias)]
    df_f = df_f[df_f['produto'].isin(produtos)]
    return df_f

def resumo_indicadores(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            'total_vendas': 0.0,
            'quantidade_total': 0,
            'ticket_medio': 0.0,
            'num_clientes': 0,
            'produto_mais_vendido': "",
            'categoria_mais_faturou': "",
            'forma_mais_usada': "",
            'venda_media_diaria': 0.0,
            'dia_maior_faturamento': ""
        }
    total_v = calcular_total_vendas(df)
    qtd_total = calcular_quantidade_total(df)
    ticket = calcular_ticket_medio(df)
    num_cli = df['cliente'].nunique()
    prod_mais = df.groupby('produto')['quantidade'].sum().idxmax()
    cat_mais = df.groupby('categoria')['valor_total'].sum().idxmax()
    forma_mais = df['forma_pagamento'].value_counts().idxmax()
    temp = df.copy()
    temp['dia'] = temp['data_venda'].dt.date
    vendas_por_dia = temp.groupby('dia')['valor_total'].sum().reset_index(name='Receita')
    dias_com_venda = vendas_por_dia['dia'].nunique()
    med_diaria = float(vendas_por_dia['Receita'].sum() / dias_com_venda) if dias_com_venda > 0 else 0.0
    maior_idx = vendas_por_dia['Receita'].idxmax()
    dia_maior = vendas_por_dia.loc[maior_idx, 'dia']
    return {
        'total_vendas': total_v,
        'quantidade_total': qtd_total,
        'ticket_medio': ticket,
        'num_clientes': num_cli,
        'produto_mais_vendido': prod_mais,
        'categoria_mais_faturou': cat_mais,
        'forma_mais_usada': forma_mais,
        'venda_media_diaria': med_diaria,
        'dia_maior_faturamento': dia_maior
    }

def pivot_receita_cliente_categoria(df: pd.DataFrame) -> pd.DataFrame:
    return df.pivot_table(
        index='cliente',
        columns='categoria',
        values='valor_total',
        aggfunc='sum',
        fill_value=0
    )