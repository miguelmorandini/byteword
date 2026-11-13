with games as (
    select * from {{ ref('fct_games') }}
),

word_stats as (
    select
        target_word,
        count(game_id) as times_played,
        count(case when is_won then 1 end) as times_solved,
        count(case when not is_won then 1 end) as times_failed,
        round(count(case when is_won then 1 end) * 100.0 / nullif(count(game_id), 0), 1) as solve_rate_percentage,
        round(count(case when not is_won then 1 end) * 100.0 / nullif(count(game_id), 0), 1) as fail_rate_percentage,
        round(avg(attempts_count), 2) as avg_attempts_needed,
        round(avg(duration_seconds), 1) as avg_duration_seconds
    from games
    group by target_word
),

final as (
    select
        target_word,
        times_played,
        times_solved,
        times_failed,
        solve_rate_percentage,
        fail_rate_percentage,
        avg_attempts_needed,
        avg_duration_seconds,
        case 
            when fail_rate_percentage >= 50.0 or avg_attempts_needed >= 4.8 then 'Difícil'
            when fail_rate_percentage >= 25.0 or avg_attempts_needed >= 3.8 then 'Médio'
            else 'Fácil'
        end as difficulty_tier
    from word_stats
)

select * from final
order by fail_rate_percentage desc, avg_attempts_needed desc
