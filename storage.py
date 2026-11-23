import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / 'monitor.db'

# Endereços de exemplo carregados automaticamente apenas na primeira inicialização.
EXAMPLE_TARGETS = (
    ('187.45.181.182', 'IP Exemplo 01'),
    ('189.73.48.167', 'IP Exemplo 02'),
    ('187.49.84.183', 'IP Exemplo 03'),
)


def connect():
    conn = sqlite3.connect(DB, timeout=15)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=15000')
    return conn


def setup():
    with connect() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                online INTEGER NOT NULL,
                latency_ms REAL,
                FOREIGN KEY (target_id) REFERENCES targets(id)
            );
            CREATE INDEX IF NOT EXISTS idx_checks_date ON checks(checked_at);
            CREATE INDEX IF NOT EXISTS idx_checks_target_date ON checks(target_id, checked_at);
        ''')

    # Insere exemplos somente se o banco estiver sem dispositivos cadastrados.
    # Não sobrescreve os IPs administrados pelo usuário em reinicializações futuras.
    with connect() as conn:
        count = conn.execute('SELECT COUNT(*) FROM targets').fetchone()[0]
        if count == 0:
            conn.executemany(
                'INSERT OR IGNORE INTO targets (address, label) VALUES (?, ?)',
                EXAMPLE_TARGETS
            )
