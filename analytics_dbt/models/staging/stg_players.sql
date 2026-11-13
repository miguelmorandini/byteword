with source as (
    select * from {{ source('main', 'raw_players') }}
),

renamed as (
    select
        cast(id as varchar) as player_id,
        trim(cast(nickname as varchar)) as player_nickname,
        cast(created_at as timestamp) as created_at
    from source
)

select * from renamed
