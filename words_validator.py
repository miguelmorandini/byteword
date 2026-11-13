"""
Módulo de validação de palavras para o ByteWord.
Garante que apenas palavras válidas de 5 letras em Inglês (EN) ou Português (PT-BR)
sejam aceitas como palpites no jogo e registradas no DuckDB.
"""

from pathlib import Path
from typing import Set

_WORDS_CACHE: Set[str] = set()

def get_valid_words() -> Set[str]:
    """Carrega o conjunto de palavras válidas a partir de data/valid_words.txt."""
    global _WORDS_CACHE
    if not _WORDS_CACHE:
        txt_path = Path(__file__).resolve().parent / "data" / "valid_words.txt"
        if txt_path.exists():
            with open(txt_path, "r", encoding="utf-8") as f:
                _WORDS_CACHE = set(line.strip().upper() for line in f if line.strip())
    return _WORDS_CACHE

def is_valid_word(word: str) -> bool:
    """Retorna True se a palavra possuir 5 letras e constar no dicionário EN / PT-BR."""
    if not word or len(word) != 5:
        return False
    clean = word.strip().upper()
    return clean in get_valid_words()
