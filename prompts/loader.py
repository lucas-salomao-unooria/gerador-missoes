"""Módulo utilitário para carregamento, edição e persistência de arquivos de prompt (.md)."""

import os
from pathlib import Path
from typing import Any, Dict

PROMPTS_DIR = Path(__file__).resolve().parent


def get_prompt_raw(filename: str) -> str:
    """Retorna o conteúdo bruto do arquivo de prompt sem interpolações."""
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    file_path = PROMPTS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo de prompt não encontrado: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def save_prompt(filename: str, content: str) -> bool:
    """Salva o conteúdo atualizado no arquivo de prompt correspondente."""
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    file_path = PROMPTS_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    return True


def load_prompt(filename: str, **kwargs: Any) -> str:
    """Carrega o conteúdo de um arquivo Markdown de prompt a partir da pasta prompts/.
    
    Substitui apenas as variáveis estáticas fornecidas em kwargs (ex: figma_folder_url),
    preservando as variáveis dinâmicas de estado do Google ADK (como {requirements_spec}).
    
    Args:
        filename: Nome do arquivo (ex: 'a1_requirements.md' ou 'a1_requirements').
        **kwargs: Variáveis estáticas de configuração para interpolação.
        
    Returns:
        String com a instrução / prompt do sistema.
    """
    content = get_prompt_raw(filename)

    # Substitui de forma segura apenas as variáveis passadas em kwargs
    for key, val in kwargs.items():
        placeholder = f"{{{key}}}"
        content = content.replace(placeholder, str(val))

    return content.strip()
