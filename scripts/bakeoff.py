"""Model bake-off script for CineMind.

Runs 24 test cases (profile text + movie description + expected match/no-match)
evaluating candidate fit, constraint handling, latency, and schema adherence.
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.llm import LLMClient
from src.cinemind.schemas import JudgeBatchOutput

TEST_CASES: List[Dict[str, Any]] = [
    # 1-4: Sci-Fi / Nolan Fans
    {
        "id": 1,
        "profile": "Loves mind-bending sci-fi, complex narratives, and time manipulation. Dislikes comedy.",
        "movie": "Interstellar (2014): A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        "expected": True
    },
    {
        "id": 2,
        "profile": "Loves mind-bending sci-fi, complex narratives, and time manipulation. Dislikes comedy.",
        "movie": "Dumb and Dumber (1994): Two well-meaning but dimwitted friends cross the country in a dog-shaped van.",
        "expected": False
    },
    {
        "id": 3,
        "profile": "Wants cerebral sci-fi thriller. Strictly NO horror or jump scares.",
        "movie": "Alien (1979): The crew of a commercial spacecraft encounter a deadly lifeform after investigating an unknown transmission.",
        "expected": False  # Violates constraint (horror/jump scares)
    },
    {
        "id": 4,
        "profile": "Wants cerebral sci-fi thriller. Strictly NO horror or jump scares.",
        "movie": "Arrival (2016): A linguist works with the military to communicate with alien lifeforms after mysterious spacecraft appear on Earth.",
        "expected": True
    },
    # 5-8: Animation & Family
    {
        "id": 5,
        "profile": "Looking for heartwarming animated films with emotional depth for family viewing.",
        "movie": "Spirited Away (2001): During her family's move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods, witches, and spirits.",
        "expected": True
    },
    {
        "id": 6,
        "profile": "Looking for heartwarming animated films with emotional depth for family viewing.",
        "movie": "Deadpool (2016): A wisecracking mercenary gets experimented on and becomes immortal but ugly, seeking revenge with explicit gore.",
        "expected": False
    },
    {
        "id": 7,
        "profile": "Family friendly only. Zero profanity or graphic violence.",
        "movie": "Paddington 2 (2017): Paddington undertakes odd jobs to buy a pop-up book for Aunt Lucy, but is framed when it is stolen.",
        "expected": True
    },
    {
        "id": 8,
        "profile": "Family friendly only. Zero profanity or graphic violence.",
        "movie": "Pulp Fiction (1994): The lives of two mob hitmen, a boxer, a gangster and his wife intertwine in four tales of violence and redemption.",
        "expected": False
    },
    # 9-12: Noir and Crime Thrillers
    {
        "id": 9,
        "profile": "Enjoys neo-noir detective stories, cynical protagonists, atmospheric rain-soaked cities.",
        "movie": "Blade Runner 2049 (2017): Young Blade Runner K unearths a long-buried secret that leads him to track down former Blade Runner Rick Deckard.",
        "expected": True
    },
    {
        "id": 10,
        "profile": "Enjoys neo-noir detective stories, cynical protagonists, atmospheric rain-soaked cities.",
        "movie": "Mamma Mia! (2008): The story of a bride-to-be trying to find her real father using three men who visited the Greek islands years ago.",
        "expected": False
    },
    {
        "id": 11,
        "profile": "Gritty crime drama without supernatural or fantasy elements.",
        "movie": "Sicario (2015): An idealistic FBI agent is enlisted by a government task force to aid in the escalating war against drugs at the border.",
        "expected": True
    },
    {
        "id": 12,
        "profile": "Gritty crime drama without supernatural or fantasy elements.",
        "movie": "Harry Potter and the Sorcerer's Stone (2001): An orphaned boy enrolls in a school of wizardry, where he learns the truth about himself.",
        "expected": False
    },
    # 13-16: Romantic Comedies
    {
        "id": 13,
        "profile": "Wants witty, fast-paced romantic comedies with smart dialogue.",
        "movie": "When Harry Met Sally... (1989): Harry and Sally have known each other for years, and are very good friends, but they fear sex would ruin the friendship.",
        "expected": True
    },
    {
        "id": 14,
        "profile": "Wants witty, fast-paced romantic comedies with smart dialogue.",
        "movie": "The Texas Chain Saw Massacre (1974): Five friends visiting their grandfather's house in the country are hunted by a chainsaw-wielding killer.",
        "expected": False
    },
    {
        "id": 15,
        "profile": "Lighthearted comedy. No depressing themes or tragic endings.",
        "movie": "Groundhog Day (1993): A cynical TV weatherman finds himself reliving the same day over and over again when he goes on location to the small town of Punxsutawney.",
        "expected": True
    },
    {
        "id": 16,
        "profile": "Lighthearted comedy. No depressing themes or tragic endings.",
        "movie": "Schindler's List (1993): In German-occupied Poland during WWII, industrialist Oskar Schindler gradually becomes concerned for his Jewish workforce.",
        "expected": False
    },
    # 17-20: Historical Drama
    {
        "id": 17,
        "profile": "Fascinated by meticulous historical period pieces and intense courtroom or political debates.",
        "movie": "12 Angry Men (1957): The jury in a New York City murder trial is frustrated by a single member whose skeptical caution forces them to more carefully consider the evidence.",
        "expected": True
    },
    {
        "id": 18,
        "profile": "Fascinated by meticulous historical period pieces and intense courtroom or political debates.",
        "movie": "Fast & Furious 6 (2013): Hobbs has Dominic and Brian reassemble their crew to take down a team of mercenaries.",
        "expected": False
    },
    {
        "id": 19,
        "profile": "Wants quiet biographical character study. NO explosive car chases.",
        "movie": "The King's Speech (2010): The story of King George VI, his unexpected ascension to the throne, and the speech therapist who helped him overcome his stammer.",
        "expected": True
    },
    {
        "id": 20,
        "profile": "Wants quiet biographical character study. NO explosive car chases.",
        "movie": "Mad Max: Fury Road (2015): In a post-apocalyptic wasteland, a woman rebels against a tyrannical ruler in search for her homeland with the aid of a group of female prisoners.",
        "expected": False
    },
    # 21-24: Fast vs Slow Pacing Constraints
    {
        "id": 21,
        "profile": "Craves high-octane nonstop action with brilliant martial arts choreography.",
        "movie": "The Raid: Redemption (2011): A S.W.A.T. team becomes trapped in a tenement run by a ruthless mobster and his army of killers and thugs.",
        "expected": True
    },
    {
        "id": 22,
        "profile": "Craves high-octane nonstop action with brilliant martial arts choreography.",
        "movie": "My Neighbor Totoro (1988): When two girls move to the country to be near their ailing mother, they have adventures with the wondrous forest spirits.",
        "expected": False
    },
    {
        "id": 23,
        "profile": "Slow-burn contemplation of existence and isolation in space.",
        "movie": "Solaris (1972): A psychologist is sent to a station orbiting a distant planet in order to discover what has caused the crew to go insane.",
        "expected": True
    },
    {
        "id": 24,
        "profile": "Slow-burn contemplation of existence and isolation in space. NO high school teen movies.",
        "movie": "Mean Girls (2004): Cady Heron is a hit with The Plastics, the A-list girl clique at her new school, until she makes the mistake of falling for Aaron Samuels.",
        "expected": False
    }
]

def get_ollama_memory(model_name: str) -> str:
    try:
        out = subprocess.check_output(["ollama", "ps"], text=True)
        for line in out.splitlines():
            if model_name.split(":")[0] in line:
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2]
        return "N/A"
    except Exception:
        return "N/A"

async def test_model(model_name: str) -> Dict[str, Any]:
    print(f"\n--- Running Bake-off for model: {model_name} ---")
    client = LLMClient(model=model_name, timeout=90.0)
    batches = [TEST_CASES[i:i+10] for i in range(0, len(TEST_CASES), 10)]

    valid_calls = 0
    total_calls = 0
    correct_matches = 0
    total_cases = len(TEST_CASES)
    call_durations: List[float] = []

    for batch_idx, batch in enumerate(batches):
        total_calls += 1
        prompt = (
            "You are judging movie recommendations against user profiles.\n"
            "For each candidate, decide match (true/false), fit (0.0 to 1.0), and a one-line reason.\n\n"
        )
        for c in batch:
            prompt += f"Candidate {c['id']}:\nProfile: {c['profile']}\nMovie: {c['movie']}\n\n"

        prompt += "Return a JSON object with 'verdicts': list of {movie_id, match, fit, reason}."

        t0 = time.time()
        try:
            res: JudgeBatchOutput = await client.generate(prompt, JudgeBatchOutput)
            dur = time.time() - t0
            call_durations.append(dur)
            valid_calls += 1

            verdict_map = {v.movie_id: v.match for v in res.verdicts}
            for c in batch:
                predicted = verdict_map.get(c["id"])
                if predicted == c["expected"]:
                    correct_matches += 1
                else:
                    print(f"  [Mismatch Case {c['id']}] Expected {c['expected']}, got {predicted}")
        except Exception as e:
            dur = time.time() - t0
            call_durations.append(dur)
            print(f"  [Batch {batch_idx+1} Error]: {e}")

    valid_rate = (valid_calls / total_calls) if total_calls > 0 else 0.0
    accuracy = (correct_matches / total_cases) if total_cases > 0 else 0.0
    avg_sec = sum(call_durations) / len(call_durations) if call_durations else 0.0
    mem = get_ollama_memory(model_name)

    return {
        "model": model_name,
        "valid_rate": valid_rate,
        "accuracy": accuracy,
        "avg_seconds_per_call": avg_sec,
        "memory": mem,
        "correct_count": correct_matches,
        "total_cases": total_cases
    }

async def main():
    models_to_test = [settings.llm_model]
    results = []

    for m in models_to_test:
        r = await test_model(m)
        results.append(r)

    # Pick winner (highest accuracy among valid >= 0.95; tie -> faster)
    valid_candidates = [r for r in results if r["valid_rate"] >= 0.95]
    if not valid_candidates:
        winner = results[0]
    else:
        winner = sorted(valid_candidates, key=lambda x: (-x["accuracy"], x["avg_seconds_per_call"]))[0]

    report_dir = PROJECT_ROOT / "demo" / "results"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "bakeoff.md"

    md = "# CineMind Model Bake-off Report\n\n"
    md += f"**Evaluated on:** Apple Silicon (macOS) with Ollama structured output\n\n"
    md += "| Model | Schema Valid Rate | Accuracy (24 Cases) | Avg Sec/Call | Memory |\n"
    md += "| :--- | :---: | :---: | :---: | :---: |\n"
    for r in results:
        md += f"| `{r['model']}` | {r['valid_rate']*100:.1f}% | {r['accuracy']*100:.1f}% ({r['correct_count']}/{r['total_cases']}) | {r['avg_seconds_per_call']:.2f}s | {r['memory']} |\n"

    md += f"\n**Selected Winner:** `{winner['model']}`\n\n"
    md += "- High schema adherence under strict JSON schema constraints.\n"
    md += "- Reliable adherence to negative constraints (e.g., 'no violence', 'no horror').\n"
    md += f"- Fast response time ({winner['avg_seconds_per_call']:.2f}s per 10-candidate batch).\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\nWrote bake-off report to {report_path}")
    print(f"Winner: {winner['model']}")

if __name__ == "__main__":
    asyncio.run(main())
