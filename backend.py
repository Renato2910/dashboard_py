import sqlite3
import pandas as pd

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
    return float(df['valor_total'].mean())

def produto_mais_vendido(df: pd.DataFrame) -> str:
    return df.groupby('produto')['quantidade'].sum().idxmax()