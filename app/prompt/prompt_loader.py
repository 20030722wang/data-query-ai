from pathlib import Path


_PROMPTS_DIR = Path(__file__).parents[2] / 'prompts'


def load_prompt(name: str) -> str:
    prompt_path = _PROMPTS_DIR / f"{name}.prompt"
    if not prompt_path.exists():
        available = [p.stem for p in _PROMPTS_DIR.glob("*.prompt")]
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}\n"
            f"Available prompts: {available}"
        )
    return prompt_path.read_text(encoding="utf-8")