{% macro calculate_score(is_won, attempts_count, duration_seconds) %}
    case 
        when not {{ is_won }} then 0
        else cast(
            1000 
            + ((7 - {{ attempts_count }}) * 150) 
            + greatest(0, 300 - (cast({{ duration_seconds }} as integer) * 2))
            as integer
        )
    end
{% endmacro %}
