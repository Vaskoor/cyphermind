"""
Self-Play Red vs Blue Arena — uses NVIDIA Kimi K2.6 via integrate API.
"""
from __future__ import annotations
import logging

from app.services.rag_service import rag_service
from app.services.llm_service import chat_completion

logger = logging.getLogger(__name__)

RED_SYSTEM = (
    "You are a red-team penetration tester. Analyze the given code and generate "
    "a specific, realistic attack payload or exploitation technique. "
    "Be concise: output ONLY the attack technique, payload, or exploit command. "
    "No explanations unless asked."
)

BLUE_SYSTEM = (
    "You are a defensive security engineer. Given an attack technique, "
    "provide the minimal code patch or configuration change that mitigates it. "
    "Output ONLY the fix. Be precise and technical."
)


async def _call_llm(prompt: str, system: str, temperature: float = 0.5, role: str = "selfplay") -> str:
    return await chat_completion(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=4096,
        role=role,
    )


async def run_selfplay_game(
    target_code: str,
    language: str = "python",
    max_rounds: int = 5,
) -> dict:
    rounds = []
    current_code = target_code

    for round_num in range(1, max_rounds + 1):
        logger.info(f"Self-play round {round_num}")

        red_prompt = f"Target code ({language}):\n```\n{current_code[:3000]}\n```\nGenerate an attack."
        try:
            red_move = await _call_llm(red_prompt, RED_SYSTEM, temperature=0.9, role="selfplay_red")
        except Exception as e:
            red_move = f"[Red team error: {e}]"

        similar = rag_service.retrieve(red_move, top_k=1)
        is_novel = not similar or similar[0].score < 0.7

        blue_prompt = (
            f"Target code ({language}):\n```\n{current_code[:2000]}\n```\n"
            f"Attack technique: {red_move}\nProvide a defensive patch."
        )
        try:
            blue_move = await _call_llm(blue_prompt, BLUE_SYSTEM, temperature=0.1, role="selfplay_blue")
        except Exception as e:
            blue_move = f"[Blue team error: {e}]"

        rounds.append({
            "round": round_num,
            "red_move": red_move,
            "blue_move": blue_move,
            "is_novel": is_novel,
        })

        current_code = current_code + f"\n# PATCH (round {round_num}):\n# {blue_move[:200]}"

        if not is_novel and round_num > 2:
            break

    novel_count = sum(1 for r in rounds if r["is_novel"])
    winner = "red" if novel_count > len(rounds) // 2 else "blue"

    # Auto-ingest novel attacks into attack memory + RAG
    ingested_count = 0
    try:
        from app.services.attack_memory_service import store_selfplay_patterns
        ingested_count = await store_selfplay_patterns(rounds, language)
    except Exception as exc:
        logger.warning("Self-play memory ingest failed: %s", exc)

    return {
        "rounds": rounds,
        "winner": winner,
        "novel_patterns_found": novel_count,
        "total_rounds": len(rounds),
        "ingested_to_kb": ingested_count,
    }
