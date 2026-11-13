import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import duckdb
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "byteword.duckdb"

def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

@contextmanager
def get_connection():
    """
    Retorna uma conexão pontual e fecha-a explicitamente no finally.
    Isso impede locks em disco e evita discrepâncias de configuração no DuckDB.
    """
    ensure_data_dir()
    conn = duckdb.connect(str(DB_PATH), read_only=False)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Cria as tabelas brutas (raw) se ainda não existirem."""
    ensure_data_dir()
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_players (
                id VARCHAR PRIMARY KEY,
                nickname VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_games (
                id VARCHAR PRIMARY KEY,
                player_id VARCHAR NOT NULL,
                target_word VARCHAR NOT NULL,
                is_won BOOLEAN NOT NULL,
                attempts_count INTEGER NOT NULL,
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP NOT NULL,
                duration_seconds INTEGER NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_guesses (
                id VARCHAR PRIMARY KEY,
                game_id VARCHAR NOT NULL,
                attempt_number INTEGER NOT NULL,
                guessed_word VARCHAR NOT NULL,
                guess_timestamp TIMESTAMP NOT NULL
            );
        """)

def get_or_create_player(nickname: str) -> str:
    """Busca jogador pelo nickname (case-insensitive) ou cria um novo."""
    init_db()
    nickname_clean = nickname.strip()
    if not nickname_clean:
        nickname_clean = "Player_Tech"

    with get_connection() as conn:
        res = conn.execute(
            "SELECT id FROM raw_players WHERE LOWER(nickname) = LOWER(?) LIMIT 1",
            [nickname_clean]
        ).fetchone()

        if res:
            return res[0]

        player_id = f"usr_{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT INTO raw_players (id, nickname, created_at) VALUES (?, ?, ?)",
            [player_id, nickname_clean, datetime.now()]
        )
        return player_id

def record_game(
    player_id: str,
    target_word: str,
    is_won: bool,
    attempts: List[str],
    started_at: datetime,
    ended_at: datetime
) -> str:
    """Registra uma partida completa e cada um dos seus palpites no DuckDB."""
    init_db()
    game_id = f"game_{uuid.uuid4().hex[:10]}"
    duration_seconds = max(1, int((ended_at - started_at).total_seconds()))
    attempts_count = len(attempts)

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO raw_games (
                id, player_id, target_word, is_won, attempts_count, started_at, ended_at, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            game_id, player_id, target_word.upper().strip(), is_won,
            attempts_count, started_at, ended_at, duration_seconds
        ])

        for idx, word in enumerate(attempts, start=1):
            guess_id = f"guess_{uuid.uuid4().hex[:10]}"
            conn.execute("""
                INSERT INTO raw_guesses (
                    id, game_id, attempt_number, guessed_word, guess_timestamp
                ) VALUES (?, ?, ?, ?, ?)
            """, [guess_id, game_id, idx, word.upper().strip(), ended_at])

    return game_id

def query_df(sql: str, params: Optional[list] = None) -> pd.DataFrame:
    """Executa consulta de leitura e retorna DataFrame."""
    init_db()
    with get_connection() as conn:
        if params:
            return conn.execute(sql, params).df()
        return conn.execute(sql).df()

def table_exists(table_name: str) -> bool:
    """Verifica se uma tabela ou visão existe no banco."""
    init_db()
    try:
        df = query_df(
            "SELECT 1 FROM information_schema.tables WHERE lower(table_name) = lower(?)",
            [table_name]
        )
        return not df.empty
    except Exception:
        return False
