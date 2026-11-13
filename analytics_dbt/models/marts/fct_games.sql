with games as (
    select * from {{ ref('stg_games') }}
),

players as (
    select * from {{ ref('stg_players') }}
),

final as (
    select
        g.game_id,
        g.player_id,
        p.player_nickname,
        g.target_word,
        g.is_won,
        g.attempts_count,
        g.started_at,
        g.ended_at,
        g.duration_seconds,
        cast(g.started_at as date) as game_date,
        {{ calculate_score('g.is_won', 'g.attempts_count', 'g.duration_seconds') }} as game_score,
        case 
            when g.is_won then round(100.0 / g.attempts_count, 1)
            else 0.0
        end as accuracy_percentage
    from games g
    inner join players p on g.player_id = p.player_id
)

select * from final
