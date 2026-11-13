import os
import sys
import shutil
import subprocess
import random
from datetime import datetime
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import db
from seed_data import TECH_WORDS, seed_database
from words_validator import is_valid_word

# Configuração da página Streamlit
st.set_page_config(
    page_title="ByteWord | dbt Core + DuckDB",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Diretórios e Executáveis
BASE_DIR = Path(__file__).resolve().parent
DBT_DIR = BASE_DIR / "analytics_dbt"
DBT_EXE = BASE_DIR / ".venv" / "Scripts" / "dbt.exe"

def run_dbt(args):
    """Executa comandos do dbt de forma portável (Windows local ou Streamlit Cloud Linux)."""
    env = os.environ.copy()
    env["DBT_DUCKDB_PATH"] = str(db.DB_PATH)

    if DBT_EXE.exists():
        cmd = [str(DBT_EXE), *args]
    elif shutil.which("dbt"):
        cmd = [shutil.which("dbt"), *args]
    else:
        cmd = [sys.executable, "-m", "dbt.cli.main", *args]

    cmd += ["--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    return subprocess.run(cmd, capture_output=True, text=True, env=env)

def auto_bootstrap():
    """Garante que na primeira execução (local ou Streamlit Cloud) o banco já tenha dados e marts prontos."""
    db.init_db()
    needs_seed = False
    try:
        df_games = db.query_df("SELECT count(*) as cnt FROM raw_games")
        if df_games.empty or df_games.iloc[0]["cnt"] == 0:
            needs_seed = True
    except Exception:
        needs_seed = True

    if needs_seed:
        seed_database(num_games_per_player=4)
        run_dbt(["build"])
    elif not db.table_exists("dim_players_ranking"):
        run_dbt(["build"])

auto_bootstrap()

COMPONENT_DIR = BASE_DIR / "byteword_component"
byteword_component = components.declare_component("byteword_game", path=str(COMPONENT_DIR))

# Estilização CSS customizada
st.markdown("""
<style>
    /* Oculta margens desnecessárias para encaixar o board perfeitamente */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

def evaluate_guess(guess: str, target: str):
    """
    Algoritmo padrão Wordle para coloração de letras:
    - Verde: letra e posição corretas.
    - Amarelo: letra correta em posição diferente.
    - Cinza: letra não existe ou excedente.
    """
    result = [None] * 5
    target_chars = list(target)
    guess_chars = list(guess)

    # 1. Verdes (Match exato)
    for i in range(5):
        if guess_chars[i] == target_chars[i]:
            result[i] = (guess_chars[i], "green")
            target_chars[i] = None

    # 2. Amarelos e Cinzas
    for i in range(5):
        if result[i] is None:
            char = guess_chars[i]
            if char in target_chars:
                result[i] = (char, "yellow")
                target_chars[target_chars.index(char)] = None
            else:
                result[i] = (char, "gray")

    return result

def init_game_state(new_game: bool = False):
    if "nickname_set" not in st.session_state:
        st.session_state.nickname_set = False
    if "player_nickname" not in st.session_state:
        st.session_state.player_nickname = ""
    if "game_id" not in st.session_state or new_game:
        st.session_state.game_id = f"g_{random.randint(1000, 9999)}"
        st.session_state.target_word = random.choice(TECH_WORDS)
        st.session_state.attempts = []
        st.session_state.game_started_at = datetime.now()
        st.session_state.game_over = False
        st.session_state.is_won = False
        st.session_state.last_processed_timestamp = 0

init_game_state()

# ==========================================
# POPUP DIALOGS: NICKNAME & RANKING
# ==========================================
@st.dialog("👋 Bem-vindo ao ByteWord!")
def show_nickname_dialog():
    st.markdown("""
    Digite seu **nickname** para iniciar a partida.  
    Suas jogadas serão persistidas em tempo real no **DuckDB** e rankeadas pelo pipeline **dbt Core**.
    """)
    nick = st.text_input(
        "Seu Nickname de Jogador:",
        value=st.session_state.get("player_nickname", ""),
        placeholder="Ex: Ana_DataEng, Carla_DBA, Bruno_Analytics...",
        max_chars=20,
        key="dialog_nickname_input"
    )
    if st.button("Começar a Jogar 🎮", type="primary", width="stretch"):
        clean_name = nick.strip() if nick.strip() else f"Dev_{random.randint(100, 999)}"
        st.session_state.player_nickname = clean_name
        st.session_state.nickname_set = True
        st.rerun()

# Dispara popup automaticamente se nickname ainda não foi configurado
if not st.session_state.nickname_set:
    show_nickname_dialog()

@st.dialog("🏆 Hall da Fama - Ranking dos Jogadores", width="large")
def show_ranking_dialog():
    if not db.table_exists("dim_players_ranking"):
        st.info("Execute `dbt build` para compilar o ranking dos jogadores.")
        return

    df_ranking = db.query_df("SELECT * FROM dim_players_ranking ORDER BY player_rank ASC")
    if df_ranking.empty:
        st.info("Nenhuma partida registrada ainda.")
        return

    current_nick = st.session_state.get("player_nickname", "")
    player_row = df_ranking[df_ranking["player_nickname"].str.lower() == current_nick.lower()]

    if not player_row.empty:
        p = player_row.iloc[0]
        rank_val = int(p["player_rank"])
        medal = "🥇" if rank_val == 1 else "🥈" if rank_val == 2 else "🥉" if rank_val == 3 else f"#{rank_val}"
        
        st.markdown(f"### Seu Desempenho: **{p['player_nickname']}** ({medal})")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sua Posição", f"#{rank_val}")
        c2.metric("Score Acumulado", f"{int(p['total_score']):,} pts")
        c3.metric("Taxa de Vitória", f"{p['win_rate_percentage']:.1f}%")
        c4.metric("Sequência Atual", f"🔥 {int(p['current_win_streak'])}")
        st.markdown("---")

    st.markdown("#### 🥇 Classificação Geral (Top Players)")
    
    def format_rank(r):
        if r == 1: return "🥇 1º"
        if r == 2: return "🥈 2º"
        if r == 3: return "🥉 3º"
        return f"{r}º"

    display_df = df_ranking.copy()
    display_df["Rank"] = display_df["player_rank"].apply(format_rank)
    display_df = display_df[[
        "Rank", "player_nickname", "total_score", "win_rate_percentage",
        "current_win_streak", "total_wins", "total_games", "avg_attempts_on_win"
    ]].rename(columns={
        "player_nickname": "Jogador",
        "total_score": "Score Total",
        "win_rate_percentage": "Vitória %",
        "current_win_streak": "Win Streak",
        "total_wins": "Vitórias",
        "total_games": "Jogos",
        "avg_attempts_on_win": "Média Tentativas"
    })

    st.dataframe(display_df, width="stretch", hide_index=True)

# Barra Lateral (Sidebar)
with st.sidebar:
    st.image("https://raw.githubusercontent.com/dbt-labs/dbt-core/main/dbt_logo.svg", width=60)
    st.title("ByteWord")
    st.caption("Stack: **Streamlit + DuckDB + dbt Core**")
    st.markdown("---")

    if st.session_state.nickname_set and st.session_state.player_nickname:
        st.markdown(f"👤 Jogador Atual: **`{st.session_state.player_nickname}`**")
        if st.button("✏️ Trocar Nickname", width="stretch"):
            st.session_state.nickname_set = False
            st.rerun()
    else:
        if st.button("🔑 Definir Nickname", type="primary", width="stretch"):
            show_nickname_dialog()

    st.markdown("---")
    st.markdown("### 🎮 Regras & Teclado")
    st.markdown("""
    - Descubra a palavra tech secreta de **5 letras**.
    - Você tem até **6 tentativas**.
    - As teclas no teclado virtual mudam de cor conforme as pistas:
      - 🟩 **Verde**: Posição exata.
      - 🟨 **Amarelo**: Existe em outra posição.
      - ⬛ **Cinza**: Letra não está na palavra.
    - Você pode **digitar direto no teclado físico** ou clicar no **teclado na tela**!
    """)

    st.markdown("---")
    if st.button("🔄 Nova Partida", width="stretch"):
        init_game_state(new_game=True)
        st.rerun()

# Abas principais da aplicação
tab_game, tab_leaderboard, tab_dbt = st.tabs([
    "🎮 Jogar ByteWord", 
    "🏆 Hall da Fama (Marts dbt)", 
    "⚙️ Operações dbt & Qualidade"
])

# ==========================================
# ABA 1: O JOGO BYTEWORD
# ==========================================
with tab_game:
    current_nick = st.session_state.player_nickname if st.session_state.nickname_set else "Não Definido"
    
    # Prepara avaliações e mapa de cores das teclas
    evaluations = []
    key_colors = {}
    target = st.session_state.target_word

    for word in st.session_state.attempts:
        evaluated = evaluate_guess(word, target)
        row_eval = []
        for char, color in evaluated:
            row_eval.append({"letter": char, "color": color})
            current_c = key_colors.get(char)
            if current_c == "green":
                continue
            if color == "green" or (color == "yellow" and current_c != "green"):
                key_colors[char] = color
            elif char not in key_colors:
                key_colors[char] = color
        evaluations.append(row_eval)

    # Centraliza o jogo em uma coluna proporcional e confortável (estilo Wordle/ByteWord)
    col_l, col_center, col_r = st.columns([1.2, 3.6, 1.2])
    with col_center:
        col_hdr1, col_hdr2, col_hdr3 = st.columns([2.6, 1.2, 1.2])
        with col_hdr1:
            st.markdown(f"##### 👤 `{current_nick}` | **{len(st.session_state.attempts)}/6**")
        with col_hdr2:
            if st.button("🏆 Ranking", key="btn_show_ranking", width="stretch"):
                show_ranking_dialog()
        with col_hdr3:
            if st.button("🔄 Novo", key="btn_restart_game", width="stretch"):
                init_game_state(new_game=True)
                st.rerun()

        component_val = byteword_component(
            attempts=st.session_state.attempts,
            evaluations=evaluations,
            keyColors=key_colors,
            gameOver=st.session_state.game_over,
            key=f"comp_{st.session_state.game_id}"
        )

        # Trata evento de palpite recebido do componente
        if component_val and component_val.get("timestamp") != st.session_state.last_processed_timestamp:
            st.session_state.last_processed_timestamp = component_val["timestamp"]
            new_guess = component_val.get("word", "").strip().upper()

            if len(new_guess) == 5 and new_guess.isalpha() and is_valid_word(new_guess):
                st.session_state.attempts.append(new_guess)

                if new_guess == target:
                    st.session_state.game_over = True
                    st.session_state.is_won = True
                elif len(st.session_state.attempts) >= 6:
                    st.session_state.game_over = True
                    st.session_state.is_won = False

                if st.session_state.game_over:
                    player_id = db.get_or_create_player(st.session_state.player_nickname or "Player_Tech")
                    db.record_game(
                        player_id=player_id,
                        target_word=target,
                        is_won=st.session_state.is_won,
                        attempts=st.session_state.attempts,
                        started_at=st.session_state.game_started_at,
                        ended_at=datetime.now()
                    )
                    # Atualiza os Marts do dbt automaticamente para o ranking refletir em tempo real
                    run_dbt(["run", "--select", "fct_games dim_players_ranking dim_words_difficulty"])
                st.rerun()

        # Mensagens de Fim de Jogo (alinhadas ao tamanho do jogo)
        if st.session_state.game_over:
            if st.session_state.is_won:
                st.balloons()
                st.success(f"🎉 **PARABÉNS!** Você acertou `{target}` em {len(st.session_state.attempts)} tentativa(s)!")
            else:
                st.error(f"💀 **Fim de jogo!** A palavra correta era `{target}`.")

            col_btn_end1, col_btn_end2 = st.columns(2)
            with col_btn_end1:
                if st.button("🏆 Ver Meu Ranking", key="btn_view_rank_end", type="primary", width="stretch"):
                    show_ranking_dialog()
            with col_btn_end2:
                if st.button("Jogar Novamente 🎮", key="btn_play_again_end", width="stretch"):
                    init_game_state(new_game=True)
                    st.rerun()


# ==========================================
# ABA 2: LEADERBOARD E ANALYTICS (MARTS DBT)
# ==========================================
with tab_leaderboard:
    st.header("🏆 Hall da Fama & Analytics")
    st.caption("Consumindo dados modelados e transformados via **dbt Core** (`dim_players_ranking`, `fct_games`, `dim_words_difficulty`)")

    marts_ready = db.table_exists("dim_players_ranking") and db.table_exists("fct_games")

    if not marts_ready:
        st.warning("⚠️ As tabelas da camada Marts do dbt ainda não foram criadas no DuckDB.")
        st.info("👉 Vá até a aba **'⚙️ Operações dbt & Qualidade'** e clique em **'Executar dbt build'** para compilar os modelos!")

        if st.button("🚀 Rodar dbt build agora", width="stretch"):
            with st.spinner("Executando dbt build..."):
                res = run_dbt(["build"])
                if res.returncode == 0:
                    st.success("Tabelas Marts construídas com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao executar dbt build:")
                    st.code(res.stdout + "\n" + res.stderr)
    else:
        # Carrega dados dos Marts
        df_ranking = db.query_df("SELECT * FROM dim_players_ranking ORDER BY player_rank ASC")
        df_fct = db.query_df("SELECT * FROM fct_games ORDER BY started_at DESC")
        df_words = db.query_df("SELECT * FROM dim_words_difficulty ORDER BY fail_rate_percentage DESC")

        # KPIs do Topo
        col1, col2, col3, col4 = st.columns(4)
        total_games = len(df_fct)
        total_players = len(df_ranking)
        best_player = df_ranking.iloc[0]["player_nickname"] if not df_ranking.empty else "N/A"
        avg_win_rate = f"{df_ranking['win_rate_percentage'].mean():.1f}%" if not df_ranking.empty else "0%"

        with col1:
            st.metric("Total de Partidas", total_games)
        with col2:
            st.metric("Jogadores Registrados", total_players)
        with col3:
            st.metric("Top Player (#1)", best_player)
        with col4:
            st.metric("Taxa Média de Vitória", avg_win_rate)

        st.markdown("---")

        # Tabela do Ranking de Jogadores
        st.subheader("🥇 Ranking Geral de Jogadores")
        display_ranking = df_ranking[[
            "player_rank", "player_nickname", "total_score", "win_rate_percentage",
            "current_win_streak", "total_wins", "total_games", "avg_attempts_on_win"
        ]].rename(columns={
            "player_rank": "Posição",
            "player_nickname": "Jogador",
            "total_score": "Pontuação Total",
            "win_rate_percentage": "Taxa de Vitória (%)",
            "current_win_streak": "Win Streak Atual",
            "total_wins": "Vitórias",
            "total_games": "Jogos",
            "avg_attempts_on_win": "Média Tentativas (Vitória)"
        })
        st.dataframe(display_ranking, width="stretch", hide_index=True)

        # Gráficos de Apoio
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("📊 Pontuação por Jogador")
            if not df_ranking.empty:
                fig_scores = px.bar(
                    df_ranking.head(10),
                    x="player_nickname",
                    y="total_score",
                    color="win_rate_percentage",
                    color_continuous_scale="Viridis",
                    labels={"player_nickname": "Jogador", "total_score": "Score", "win_rate_percentage": "Win Rate %"},
                    title="Top 10 Jogadores por Score Acumulado"
                )
                fig_scores.update_layout(xaxis_tickangle=-45, height=360)
                st.plotly_chart(fig_scores, width="stretch")

        with col_chart2:
            st.subheader("🧠 Dificuldade das Palavras Tech")
            if not df_words.empty:
                fig_words = px.bar(
                    df_words.head(10),
                    x="target_word",
                    y="fail_rate_percentage",
                    color="difficulty_tier",
                    color_discrete_map={"Difícil": "#e53935", "Médio": "#fdd835", "Fácil": "#43a047"},
                    labels={"target_word": "Palavra", "fail_rate_percentage": "Taxa de Erro (%)", "difficulty_tier": "Nível"},
                    title="Palavras com Maior Taxa de Derrota (%)"
                )
                fig_words.update_layout(xaxis_tickangle=-45, height=360)
                st.plotly_chart(fig_words, width="stretch")

        # Histórico recente de partidas
        with st.expander("🕒 Ver Histórico Recente de Partidas (fct_games)"):
            st.dataframe(
                df_fct[[
                    "game_id", "player_nickname", "target_word", "is_won", 
                    "attempts_count", "duration_seconds", "game_score", "started_at"
                ]].head(20),
                width="stretch",
                hide_index=True
            )


# ==========================================
# ABA 3: OPERAÇÕES DBT & QUALIDADE DE DADOS
# ==========================================
with tab_dbt:
    st.header("⚙️ Pipeline de Transformação & Qualidade (dbt Core)")
    st.markdown("""
    Esta seção demonstra a governança, integridade de dados e compilação do pipeline analítico.
    O dbt orquestra desde a camada de **Staging** até os **Marts**, executando testes automatizados.
    """)

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        run_build = st.button("🚀 Executar `dbt build`", type="primary", width="stretch")
    with col_btn2:
        run_test = st.button("🧪 Executar `dbt test`", width="stretch")
    with col_btn3:
        seed_btn = st.button("🌱 Popular Dados Sintéticos", width="stretch")

    if seed_btn:
        with st.spinner("Gerando partidas sintéticas no DuckDB..."):
            from seed_data import seed_database
            seed_database(num_games_per_player=5)
            st.success("Histórico populado com sucesso! Agora execute `dbt build`.")

    if run_build or run_test:
        cmd = ["build"] if run_build else ["test"]
        with st.spinner(f"Executando dbt {cmd[0]}..."):
            proc = run_dbt(cmd)
            if proc.returncode == 0:
                st.success(f"✅ `dbt {cmd[0]}` concluído com sucesso!")
            else:
                st.error(f"❌ Falha ao executar `dbt {cmd[0]}`:")
            st.code(proc.stdout + "\n" + proc.stderr, language="bash")

    st.markdown("---")
    st.subheader("🛡️ Demonstração de Teste de Integridade (Anti-Cheat)")
    st.markdown("""
    Demonstre ao vivo para seu gestor como o dbt bloqueia anomalias de dados usando o teste singular:  
    `assert_valid_game_duration.sql` (rejeita partidas com duração negativa ou tempo de término antes do início).
    """)

    col_cheat1, col_cheat2 = st.columns(2)
    with col_cheat1:
        if st.button("⚠️ Injetar Dado Corrompido (Duração = -120s)", width="stretch"):
            with db.get_connection(read_only=False) as conn:
                fake_pid = db.get_or_create_player("Hacker_Invalido")
                conn.execute("""
                    INSERT INTO raw_games (
                        id, player_id, target_word, is_won, attempts_count, started_at, ended_at, duration_seconds
                    ) VALUES ('cheat_game_999', ?, 'CHEAT', true, 1, '2026-11-12 12:00:00', '2026-11-12 11:58:00', -120)
                """, [fake_pid])
            st.warning("⚠️ Partida com duração de -120 segundos injetada no DuckDB! Agora clique no teste ao lado para ver o dbt barrá-la.")

    with col_cheat2:
        if st.button("🔍 Executar Teste Anti-Cheat (`assert_valid_game_duration`)", width="stretch"):
            with st.spinner("Executando teste customizado..."):
                res = run_dbt(["test", "--select", "assert_valid_game_duration"])
                if res.returncode != 0:
                    st.error("🚨 O dbt interceptou com sucesso a anomalia anti-cheat!")
                    st.code(res.stdout, language="bash")
                else:
                    st.success("Nenhuma anomalia detectada no momento.")
                    st.code(res.stdout, language="bash")

    if st.button("🧹 Limpar Dados Corrompidos Injetados", width="stretch"):
        with db.get_connection(read_only=False) as conn:
            conn.execute("DELETE FROM raw_games WHERE duration_seconds < 0")
        st.success("Dados inválidos removidos.")
