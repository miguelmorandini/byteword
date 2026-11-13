with source as (
    select * from {{ source('main', 'raw_guesses') }}
),

renamed as (
    select
        cast(id as varchar) as guess_id,
        cast(game_id as varchar) as game_id,
        cast(attempt_number as integer) as attempt_number,
        upper(trim(cast(guessed_word as varchar))) as guessed_word,
        cast(guess_timestamp as timestamp) as guess_timestamp
    from source
)

select * from renamed
