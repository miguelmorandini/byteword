-- Singular test: assert_valid_game_duration.sql
-- Retorna registros onde a duração do jogo é inválida ou negativa (regra de negócio anti-cheat).
-- O teste passa se retornar 0 linhas.

select
    game_id,
    player_id,
    started_at,
    ended_at,
    duration_seconds
from {{ ref('stg_games') }}
where duration_seconds < 0
   or ended_at < started_at
