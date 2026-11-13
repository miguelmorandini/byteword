with games as (
    select * from {{ ref('fct_games') }}
),

players as (
    select * from {{ ref('stg_players') }}
),

games_ranked as (
    select
        game_id,
        player_id,
        is_won,
        started_at,
        row_number() over (partition by player_id order by started_at desc) as rn
    from games
),

streaks as (
    select
        player_id,
        coalesce(
            min(case when not is_won then rn end) - 1,
            count(*)
        ) as current_win_streak
    from games_ranked
    group by player_id
),

player_metrics as (
    select
        g.player_id,
        count(g.game_id) as total_games,
        count(case when g.is_won then 1 end) as total_wins,
        count(case when not g.is_won then 1 end) as total_losses,
        coalesce(sum(g.game_score), 0) as total_score,
        round(count(case when g.is_won then 1 end) * 100.0 / nullif(count(g.game_id), 0), 1) as win_rate_percentage,
        round(avg(case when g.is_won then g.attempts_count end), 2) as avg_attempts_on_win,
        round(avg(g.duration_seconds), 1) as avg_duration_seconds,
        min(g.started_at) as first_game_at,
        max(g.started_at) as last_game_at
    from games g
    group by g.player_id
),

final as (
    select
        p.player_id,
        p.player_nickname,
        coalesce(m.total_games, 0) as total_games,
        coalesce(m.total_wins, 0) as total_wins,
        coalesce(m.total_losses, 0) as total_losses,
        coalesce(m.win_rate_percentage, 0.0) as win_rate_percentage,
        coalesce(s.current_win_streak, 0) as current_win_streak,
        coalesce(m.total_score, 0) as total_score,
        coalesce(m.avg_attempts_on_win, 0.0) as avg_attempts_on_win,
        coalesce(m.avg_duration_seconds, 0.0) as avg_duration_seconds,
        m.first_game_at,
        m.last_game_at,
        dense_rank() over (
            order by 
                coalesce(m.total_score, 0) desc, 
                coalesce(m.win_rate_percentage, 0.0) desc,
                coalesce(m.total_wins, 0) desc
        ) as player_rank
    from players p
    left join player_metrics m on p.player_id = m.player_id
    left join streaks s on p.player_id = s.player_id
)

select * from final
