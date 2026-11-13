# ⚡ Tech Termo Analytics: dbt Core + DuckDB + Streamlit

Uma solução moderna e interativa de Engenharia e Modelagem de Dados de ponta a ponta, desenvolvida para demonstrar o poder e as melhores práticas do ecossistema de **Modern Data Stack** local: **dbt Core**, **DuckDB** e **Streamlit**.

---

## 🎯 Visão Geral da Arquitetura

O projeto une gamificação e engenharia analítica corporativa:
1. **Frontend & Coleta:** Uma aplicação web interativa desenvolvida em **Streamlit** no estilo *Termo / Wordle*, desafiando o usuário a adivinhar termos técnicos (ex: `QUERY`, `TABLE`, `INDEX`, `SPARK`, `CLOUD`). Cada palpite e partida é gravado em tempo real no banco colunar local **DuckDB** (`data/termo.duckdb`).
2. **Transformação & Governança:** Projeto completo em **dbt Core** orquestrando camadas padronizadas (**Sources**, **Staging**, **Marts**), macros Jinja modulares e testes automatizados de qualidade.
3. **Consumo & BI:** Painel com Leaderboard (Hall da Fama), métricas analíticas por jogador e análise de dificuldade das palavras, além de linhagem de dados navegável no **dbt docs**.

```mermaid
flowchart TD
    subgraph Frontend["1. Frontend Interativo (Streamlit)"]
        UI["app.py (Tech Termo Game)"]
    end

    subgraph Storage["2. Banco Analítico Colunar (DuckDB)"]
        RawP[("raw_players")]
        RawG[("raw_games")]
        RawGu[("raw_guesses")]
    end

    subgraph dbt["3. Transformação & Governança (dbt Core)"]
        subgraph Staging["Camada Staging (Views)"]
            StgP["stg_players"]
            StgG["stg_games"]
            StgGu["stg_guesses"]
        end
        subgraph Marts["Camada Marts (Tables)"]
            FctG["fct_games"]
            DimP["dim_players_ranking"]
            DimW["dim_words_difficulty"]
        end
    end

    subgraph BI["4. Visualização & Demonstração"]
        Leaderboard["Aba Hall da Fama no Streamlit"]
        Docs["dbt docs serve (Lineage DAG)"]
    end

    UI -->|Persiste partidas| Storage
    Storage -->|Sources| Staging
    Staging -->|ref| Marts
    Marts -->|Consome dados limpos| Leaderboard
    dbt -.-> Docs
```

---

## 📂 Estrutura do Projeto

```text
dbt/
├── app.py                      # Aplicação Streamlit (Jogo + Leaderboard + Painel dbt)
├── db.py                       # Conexão e gerenciamento DuckDB otimizado para concorrência
├── seed_data.py                # Gerador de partidas sintéticas para inicializar o ambiente
├── requirements.txt            # Dependências Python
├── README.md                   # Documentação executiva e roteiro de apresentação
├── data/
│   └── termo.duckdb            # Banco analítico DuckDB compartilhado
└── analytics_dbt/              # Projeto dbt Core
    ├── dbt_project.yml         # Configurações do projeto e materializações
    ├── profiles.yml            # Adapter DuckDB com suporte a variáveis de ambiente
    ├── macros/
    │   └── calculate_score.sql # Macro Jinja com fórmula de pontuação ponderada
    ├── tests/
    │   └── assert_valid_game_duration.sql # Teste singular customizado (regra anti-cheat)
    └── models/
        ├── staging/
        │   ├── sources.yml     # Declaração das fontes brutas (DuckDB)
        │   ├── stg_players.sql # Limpeza e padronização de jogadores
        │   ├── stg_games.sql   # Tipagem e casts de partidas
        │   ├── stg_guesses.sql # Normalização de palpites
        │   └── schema.yml      # Testes de integridade (unique, not_null)
        └── marts/
            ├── fct_games.sql            # Fato de partidas com score calculado
            ├── dim_players_ranking.sql  # Dimensão com ranking, win rate e win streaks
            ├── dim_words_difficulty.sql # Análise de dificuldade dos termos
            └── schema.yml               # Testes de relacionamentos e accepted_values
```

---

## 🚀 Como Executar o Projeto

### 1. Criar o Ambiente Virtual e Instalar Dependências
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Popular os Dados Iniciais
Para que a apresentação comece já com histórico de partidas e jogadores:
```powershell
python seed_data.py
```

### 3. Compilar e Testar os Modelos dbt
```powershell
cd analytics_dbt
dbt build
cd ..
```

### 4. Iniciar a Aplicação Interativa
```powershell
streamlit run app.py
```

---

## 🎤 Roteiro de Apresentação ao Vivo para o Gestor

Este roteiro foi estruturado para demonstrar **domínio técnico**, **visão de arquitetura** e **governança de dados moderna** em menos de 8 minutos.

### ⏱️ Passo 1: Contexto e Frontend Interativo (2 minutos)
1. Abra a aplicação no navegador (`http://localhost:8501`).
2. Digite um nickname personalizado na barra lateral (ex: `Gestor_Data`).
3. Jogue uma rodada rápida de **Tech Termo** no navegador (palpites com termos como `QUERY`, `TABLE`, `INDEX`, `SPARK`, `CLOUD`).
4. Explique:
   > *"Cada palpite e cada finalização de partida são persistidos em tempo real no DuckDB, um banco analítico colunar ultrarrápido ideal para arquiteturas serverless e edge analytics."*

### ⏱️ Passo 2: A Camada de Engenharia dbt (2 minutos)
1. Navegue até a aba **"⚙️ Operações dbt & Qualidade"**.
2. Clique no botão **"🚀 Executar `dbt build`"**.
3. Mostre o log de execução do dbt ao vivo no terminal e no Streamlit.
4. Explique:
   > *"Seguimos a arquitetura recomendada pelo dbt Labs: camada **Staging** com views efêmeras para normalização e tipagem, e camada **Marts** com tabelas dimensionais prontas para consumo de BI."*
5. Destaque a **Macro Jinja (`macros/calculate_score.sql`)**:
   > *"Em vez de duplicar regras de cálculo de score em SQL, encapsulamos a fórmula ponderada em uma macro Jinja reutilizável e testável."*

### ⏱️ Passo 3: Garantia de Qualidade e Teste Anti-Cheat (2 minutos)
1. Ainda na aba **"⚙️ Operações dbt & Qualidade"**, vá na seção de testes.
2. Clique no botão **"⚠️ Injetar Dado Corrompido"** (simula um registro malicioso com duração negativa de `-120s`).
3. Clique em **"🔍 Executar Teste Anti-Cheat"**.
4. O dbt alertará o erro em vermelho, bloqueando a propagação do dado defeituoso!
5. Explique:
   > *"Demonstramos aqui a governança ativa do dbt. Além de testes de chave primária (`unique` e `not_null`) e integridade referencial (`relationships`), criamos um teste singular de regra de negócio (`assert_valid_game_duration.sql`) que impede que dados fraudulentos ou anomalias contaminem os relatórios de tomada de decisão."*
6. Clique em **"🧹 Limpar Dados Corrompidos"**.

### ⏱️ Passo 4: O Consumo Executivo e Linhagem de Dados (2 minutos)
1. Navegue para a aba **"🏆 Hall da Fama (Marts dbt)"**.
2. Mostre:
   - Os KPIs consolidados (Total de Jogos, Top Player, Taxa de Vitória).
   - O Ranking ordenado consumindo a tabela `dim_players_ranking` com cálculo de *Win Streak* via window functions.
   - O gráfico de **Dificuldade dos Termos Tech** (`dim_words_difficulty`), demonstrando quais termos de engenharia causaram mais derrotas aos jogadores.
3. Para fechar com chave de ouro, abra um novo terminal e rode:
   ```powershell
   cd analytics_dbt
   dbt docs generate
   dbt docs serve --port 8080
   ```
4. Apresente no navegador o **Lineage Graph (DAG)** interativo, mostrando como o dado flui desde as fontes (`raw_games`, `raw_players`, `raw_guesses`) passando pelas views de staging até as dimensões e fatos finais.
