with source as (
    select * from {{ source('main', 'raw_games') }}
),

renamed as (
    select
        cast(id as varchar) as game_id,
        cast(player_id as varchar) as player_id,
        upper(trim(cast(target_word as varchar))) as target_word,
        cast(is_won as boolean) as is_won,
        cast(attempts_count as integer) as attempts_count,
        cast(started_at as timestamp) as started_at,
        cast(ended_at as timestamp) as ended_at,
        cast(duration_seconds as integer) as duration_seconds
    from source
)

select * from renamed
