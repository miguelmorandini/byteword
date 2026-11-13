"""
Script gerador de partidas sintéticas para ByteWord.
Popula data/byteword.duckdb com o histórico do único rival fictício 'anti-shavraul',
garantindo que o ranking contenha exclusivamente jogadores reais e o 'anti-shavraul'.
"""

import random
from datetime import datetime, timedelta
from db import init_db, get_or_create_player, record_game, get_connection

TECH_WORDS = [
    "QUERY", "TABLE", "INDEX", "SPARK", "CLOUD",
    "KAFKA", "REDIS", "PROXY", "FLASK", "BUILD",
    "MODEL", "DRAIN", "MERGE", "STACK", "PIVOT",
    "FETCH", "PARSE", "GRAPH", "CACHE", "SHARD"
]

RIVAL_NICKNAME = "anti-shavraul"

def clean_old_dummy_players():
    """Remove jogadores fictícios antigos gerados anteriormente, preservando jogadores reais."""
    old_dummies = [
        "carla_dba", "ana_dataeng", "diego_devops", 
        "elena_datascientist", "bruno_analytics", "hacker_invalido",
        "player_tech"
    ]
    with get_connection() as conn:
        placeholders = ",".join(["?"] * len(old_dummies))
        rows = conn.execute(
            f"SELECT id FROM raw_players WHERE lower(nickname) IN ({placeholders})", 
            old_dummies
        ).fetchall()
        pids = [r[0] for r in rows]

        if pids:
            p_placeholders = ",".join(["?"] * len(pids))
            g_rows = conn.execute(
                f"SELECT id FROM raw_games WHERE player_id IN ({p_placeholders})",
                pids
            ).fetchall()
            gids = [r[0] for r in g_rows]

            if gids:
                g_placeholders = ",".join(["?"] * len(gids))
                conn.execute(f"DELETE FROM raw_guesses WHERE game_id IN ({g_placeholders})", gids)
                conn.execute(f"DELETE FROM raw_games WHERE player_id IN ({p_placeholders})", pids)
            conn.execute(f"DELETE FROM raw_players WHERE id IN ({p_placeholders})", pids)

def generate_guesses_for_game(target: str, is_won: bool, attempts_count: int):
    guesses = []
    pool = [w for w in TECH_WORDS if w != target]
    random.shuffle(pool)

    for i in range(attempts_count):
        if i == attempts_count - 1 and is_won:
            guesses.append(target)
        else:
            guesses.append(pool[i % len(pool)])
    return guesses

def seed_anti_shavraul(num_games: int = 5):
    """
    Gera o histórico do rival fictício anti-shavraul e remove quaisquer bots legados.
    """
    init_db()
    clean_old_dummy_players()

    with get_connection() as conn:
        res = conn.execute(
            "SELECT count(*) FROM raw_games g JOIN raw_players p ON g.player_id = p.id WHERE lower(p.nickname) = ?",
            [RIVAL_NICKNAME.lower()]
        ).fetchone()
        if res and res[0] >= num_games:
            print(f"Rival {RIVAL_NICKNAME} já possui {res[0]} partidas registradas.")
            return

    player_id = get_or_create_player(RIVAL_NICKNAME)
    start_base = datetime.now() - timedelta(days=3)

    scenarios = [
        {"target": "QUERY", "won": True, "attempts": 3, "duration": 34},
        {"target": "SPARK", "won": True, "attempts": 4, "duration": 48},
        {"target": "CLOUD", "won": True, "attempts": 3, "duration": 29},
        {"target": "KAFKA", "won": False, "attempts": 6, "duration": 65},
        {"target": "INDEX", "won": True, "attempts": 4, "duration": 42},
    ]

    for idx, s in enumerate(scenarios[:num_games]):
        game_start = start_base + timedelta(hours=idx * 12)
        game_end = game_start + timedelta(seconds=s["duration"])
        guesses = generate_guesses_for_game(s["target"], s["won"], s["attempts"])
        record_game(
            player_id=player_id,
            target_word=s["target"],
            is_won=s["won"],
            attempts=guesses,
            started_at=game_start,
            ended_at=game_end
        )

    print(f"Sucesso! Partidas do rival fictício '{RIVAL_NICKNAME}' configuradas em data/byteword.duckdb.")

def seed_database(num_games_per_player: int = 5):
    """Função padrão chamada na inicialização."""
    seed_anti_shavraul(num_games=num_games_per_player)

if __name__ == "__main__":
    seed_database()
