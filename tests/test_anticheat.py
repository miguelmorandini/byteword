import os
import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import db

def test_anticheat_rule():
    db.init_db()
    fake_pid = db.get_or_create_player("Hacker_Invalido")

    # Injeta registro anômalo (duração negativa)
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO raw_games (
                id, player_id, target_word, is_won, attempts_count, started_at, ended_at, duration_seconds
            ) VALUES ('cheat_999', ?, 'CHEAT', true, 1, '2026-11-12 12:00:00', '2026-11-12 11:58:00', -120)
        """, [fake_pid])

    print("=== DADO CORROMPIDO INJETADO COM SUCESSO ===")
    
    env = os.environ.copy()
    env["DBT_DUCKDB_PATH"] = str(db.DB_PATH)
    
    DBT_EXE = BASE_DIR / ".venv" / "Scripts" / "dbt.exe"
    
    # Roda teste singular dbt
    proc = subprocess.run(
        [str(DBT_EXE), "test", "--select", "assert_valid_game_duration",
         "--project-dir", str(BASE_DIR / "analytics_dbt"), "--profiles-dir", str(BASE_DIR / "analytics_dbt")],
        capture_output=True,
        text=True,
        env=env
    )
    
    print("Return code com dado anômalo (deve ser != 0):", proc.returncode)
    assert proc.returncode != 0, "O teste dbt deveria ter falhado!"
    print(">>> SUCESSO: dbt bloqueou o dado corrompido conforme esperado!")

    # Limpeza
    with db.get_connection() as conn:
        conn.execute("DELETE FROM raw_games WHERE id = 'cheat_999'")

    print("\n=== DADO CORROMPIDO REMOVIDO ===")
    
    # Roda novamente
    proc2 = subprocess.run(
        [str(DBT_EXE), "test", "--select", "assert_valid_game_duration",
         "--project-dir", str(BASE_DIR / "analytics_dbt"), "--profiles-dir", str(BASE_DIR / "analytics_dbt")],
        capture_output=True,
        text=True,
        env=env
    )
    
    print("Return code após limpeza (deve ser 0):", proc2.returncode)
    if proc2.returncode != 0:
        print("STDOUT:", proc2.stdout)
        print("STDERR:", proc2.stderr)
    assert proc2.returncode == 0, "O teste dbt deveria ter passado!"
    print(">>> SUCESSO: dbt passou com 100% de integridade!")

if __name__ == "__main__":
    test_anticheat_rule()
