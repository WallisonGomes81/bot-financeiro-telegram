import sqlite3

DB_PATH = "financeiro.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    # Saldo inicial
    db.execute("""
        CREATE TABLE IF NOT EXISTS saldo (
            id INTEGER PRIMARY KEY,
            valor REAL
        )
    """)
    db.execute("INSERT OR IGNORE INTO saldo (id, valor) VALUES (1, 0)")
    
    # Movimentações
    db.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT CHECK(tipo IN ('entrada','saida')),
            valor REAL,
            descricao TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    db.close()

if __name__ == "__main__":
    init_db()
    print("Banco de dados criado com sucesso!")
