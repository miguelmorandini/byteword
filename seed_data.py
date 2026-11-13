"""
Script gerador de partidas sintéticas para ByteWord.
Popula data/byteword.duckdb com histórico realista de jogadores e partidas
para que o painel e o Leaderboard já iniciem com dados prontos para apresentação.
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

PLAYERS = [
    {"nickname": "Carla_DBA", "skill": 0.90, "speed": 40},
    {"nickname": "Ana_DataEng", "skill": 0.85, "speed": 55},
    {"nickname": "Diego_DevOps", "skill": 0.70, "speed": 35},
    {"nickname": "Elena_DataScientist", "skill": 0.75, "speed": 70},
    {"nickname": "Bruno_Analytics", "skill": 0.60, "speed": 90},
]

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

def seed_database(num_games_per_player: int = 6):
    print("Iniciando geração de dados sintéticos para DuckDB...")
    init_db()

    # Base time: 5 days ago
    start_base = datetime.now() - timedelta(days=5)
    total_generated = 0

    for p_info in PLAYERS:
        player_id = get_or_create_player(p_info["nickname"])
        current_time = start_base + timedelta(hours=random.randint(1, 10))

        for _ in range(num_games_per_player):
            target = random.choice(TECH_WORDS)
            is_won = random.random() < p_info["skill"]

            if is_won:
                # 1 to 6 attempts, weighted towards 3-4
                attempts_count = random.choices([1, 2, 3, 4, 5, 6], weights=[2, 10, 35, 30, 15, 8])[0]
            else:
                attempts_count = 6

            duration = max(12, int(random.gauss(p_info["speed"], 15)))
            game_start = current_time
            game_end = game_start + timedelta(seconds=duration)

            guesses = generate_guesses_for_game(target, is_won, attempts_count)
            record_game(
                player_id=player_id,
                target_word=target,
                is_won=is_won,
                attempts=guesses,
                started_at=game_start,
                ended_at=game_end
            )
            total_generated += 1
            current_time = game_end + timedelta(hours=random.randint(2, 14))

    print(f"Sucesso! {total_generated} partidas sintéticas geradas em data/byteword.duckdb.")

if __name__ == "__main__":
    seed_database()
