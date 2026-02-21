"""Debate logic - supports streaming via callback."""
import os
import random
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4.1-mini"
MAX_TURNS = 4
MAX_OUTPUT_TOKENS = 256

BOT_A = {
    "name": "Athena",
    "role": "pro",
    "system": (
        "You are Athena, a structured debate bot arguing the PRO side.\n"
        "Rules:\n"
        "- Stay on the PRO side.\n"
        "- Be concise.\n"
        "- Each section must be 1–2 sentences maximum.\n"
        "- Use this format exactly:\n"
        "Claim:\nEvidence:\nRebuttal:\nQuestion:\n"
    ),
}

BOT_B = {
    "name": "Dion",
    "role": "con",
    "system": (
        "You are Dion, a structured debate bot arguing the CON side.\n"
        "Rules:\n"
        "- Stay on the CON side.\n"
        "- Be concise.\n"
        "- Each section must be 1–2 sentences maximum.\n"
        "- Use this format exactly:\n"
        "Claim:\nEvidence:\nRebuttal:\nQuestion:\n"
    ),
}

MOD_BOT = {
    "name": "Moderator",
    "role": "moderator",
    "system": ("""You are the Moderator of a structured debate. You have exactly one job: to output only the four items below, nothing else.

STRICT RULES—follow with no exceptions:
- You MUST output ONLY these four elements in order. Do not add any other sentences, opinions, or commentary.
- You must NOT express any personal opinion, preference, or judgment on the topic or on either side.
- You must NOT say what you think is right or wrong, better or worse, or who is "winning."
- Simply report what each side said and state the main disagreement and a neutral next-focus instruction.

Output exactly this structure (use the labels; fill in the blanks from the transcript only):

PRO strongest point so far:
- [1–2 short bullets summarizing only what the PRO debater said]

CON strongest point so far:
- [1–2 short bullets summarizing only what the CON debater said]

Main disagreement: [One neutral sentence.]

Next focus: [One sentence instructing the next turns to address the hardest unresolved issue—neutral, no opinion.]

Keep total output under 120 words. Do not invent facts. Do not add anything before or after these four sections.
"""),
}

JUDGE = {
    "name": "Judge",
    "role": "judge",
    "system": ("""You are the Judge of a structured debate. Your ONLY job is to output the exact format below. Do not add any other text.

STRICT RULES—follow with no exceptions:
- You must NOT express any personal opinion on the debate topic itself. You are evaluating debate quality only, not who is "right."
- You must NOT add any preamble, introduction, conclusion, or commentary outside the required format.
- Output ONLY the section headers and lines below. Nothing before "Scores:" and nothing after the last improvement line.
- Score only based on the criteria listed. Do not invent facts. If a debater made an unsupported factual claim, penalize Evidence. If they ignored a direct question, penalize Rebuttal. If equal, declare a tie.
- For "Best point" and "One improvement": use your own words in 1 short phrase or sentence (max 12 words each). Do not quote or paraphrase the debaters.

Use the exact structure below. Replace <BotA name> and <BotB name> with the actual debater names from the transcript.

Scores:
<BotA name>:
- Relevance: X/5
- Evidence: X/5
- Rebuttal: X/5
- Clarity: X/5
- Persuasiveness: X/5
Total: X/25

<BotB name>:
- Relevance: X/5
- Evidence: X/5
- Rebuttal: X/5
- Clarity: X/5
- Persuasiveness: X/5
Total: X/25

Winner: <name or Tie>
Best point from <BotA>: ...
Best point from <BotB>: ...
One improvement for <BotA>: ...
One improvement for <BotB>: ...
"""),
}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_recent_transcript(transcript, k=2):
    """Return the last k turns as a string."""
    recent = transcript[-k:]
    if not recent:
        return "(No previous messages.)"

    lines = []
    for turn in recent:
        lines.append(f"{turn['speaker']}: {turn['text']}")
    return "\n\n".join(lines)


def format_full_transcript_for_judge(transcript):
    """Format the complete debate transcript as a single string for the Judge. No moderator/judge meta—just debater and moderator turns as content."""
    if not transcript:
        return "(No transcript.)"
    lines = []
    for turn in transcript:
        lines.append(f"{turn['speaker']}: {turn['text']}")
    return "\n\n".join(lines)


def call_bot(bot, topic, transcript):
    """Call one bot with topic + recent context and return its reply text. Used for debaters and moderator only."""
    recent_context = format_recent_transcript(transcript, k=4)

    user_prompt = (
        f"Debate topic:\n{topic}\n\n"
        f"Conversation so far (recent turns):\n{recent_context}\n\n"
        "Write your next debate turn now."
    )

    messages = [
        {"role": "system", "content": bot["system"]},
        {"role": "user", "content": user_prompt},
    ]

    resp = client.responses.create(
        model=MODEL,
        input=messages,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    return resp.output_text.strip()


def run_judge(topic: str, transcript: list) -> str:
    """
    Run the Judge in an isolated step. The Judge sees only:
    - Its system prompt
    - A single user message containing the debate topic and the full wrapped transcript.
    No shared conversation history; no prior messages from debaters or moderator.
    """
    wrapped = format_full_transcript_for_judge(transcript)
    user_message = (
        f"Debate topic:\n{topic}\n\n"
        "Full transcript of the debate (evaluate only based on this):\n\n"
        f"{wrapped}"
    )

    messages = [
        {"role": "system", "content": JUDGE["system"]},
        {"role": "user", "content": user_message},
    ]

    resp = client.responses.create(
        model=MODEL,
        input=messages,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    return resp.output_text.strip()


def _bot_with_name_and_role(base_bot, custom_name, custom_role):
    """Return a bot config with optional custom name and role. Role is the character/perspective (default PRO/CON); bot stays in character."""
    name = (custom_name or base_bot["name"]).strip() or base_bot["name"]
    role_label = (custom_role or "").strip()
    if not role_label:
        role_label = "PRO" if base_bot["role"] == "pro" else "CON"
    side = "PRO" if base_bot["role"] == "pro" else "CON"
    system = base_bot["system"].replace(base_bot["name"], name, 1)
    role_instruction = (
        f"You are arguing the {side} side. Your role/character in this debate is: {role_label}. "
        "You MUST stay in character as this role in every response—argue only from this perspective. "
        "Do not break character or speak as a neutral party. "
        "If your role is a specific character (e.g. scientist, advocate), argue the {side} side from that character's viewpoint.\n\n"
    )
    system = system.replace("Rules:\n", role_instruction + "Rules:\n", 1)
    return {
        **base_bot,
        "name": name,
        "system": system,
        "role_label": role_label,
    }


def run_debate(topic: str, on_message=None, bot_a_name=None, bot_b_name=None, bot_a_role=None, bot_b_role=None, max_turns=None):
    """
    Run debate, optionally calling on_message for each message.
    bot_a_name / bot_b_name override the PRO and CON bot names.
    bot_a_role / bot_b_role set the character/role for each debater (default "PRO" / "CON"); they stay in character.
    max_turns: number of turns (1-100), default 4.
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    transcript = []

    max_turns = max(1, min(100, max_turns or MAX_TURNS))

    bot_a = _bot_with_name_and_role(BOT_A, bot_a_name, bot_a_role)
    bot_b = _bot_with_name_and_role(BOT_B, bot_b_name, bot_b_role)

    current = bot_a if random.choice([True, False]) else bot_b
    other = bot_b if current is bot_a else bot_a

    for turn_idx in range(1, max_turns + 1):
        text = call_bot(current, topic, transcript)

        turn_data = {
            "turn": turn_idx,
            "speaker": current["name"],
            "role": current["role"],
            "role_label": current.get("role_label", "PRO" if current["role"] == "pro" else "CON"),
            "text": text,
        }
        transcript.append(turn_data)

        if on_message:
            on_message(turn_data)

        if (turn_idx % 2) == 0:
            moderator_text = call_bot(MOD_BOT, topic, transcript)
            mod_data = {
                "turn": f"{turn_idx}.M",
                "speaker": MOD_BOT["name"],
                "role": MOD_BOT["role"],
                "text": moderator_text,
            }
            transcript.append(mod_data)

            if on_message:
                on_message(mod_data)

        current, other = other, current

    # Debate loop is finished. Run the Judge in a separate, isolated step:
    # Judge receives only system prompt + single wrapped transcript; no shared history.
    judge_text = run_judge(topic, transcript)
    judge_data = {
        "turn": f"{max_turns}.J",
        "speaker": JUDGE["name"],
        "role": JUDGE["role"],
        "text": judge_text,
        "run_id": run_id,
    }
    transcript.append(judge_data)

    if on_message:
        on_message(judge_data)

    run_data = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "model": MODEL,
        "max_turns": max_turns,
        "bots": {
            "bot_a": {"name": bot_a["name"], "role_label": bot_a.get("role_label", "PRO"), "system": bot_a["system"]},
            "bot_b": {"name": bot_b["name"], "role_label": bot_b.get("role_label", "CON"), "system": bot_b["system"]},
            "moderator": {"name": MOD_BOT["name"], "system": MOD_BOT["system"]},
            "judge": {"name": JUDGE["name"], "system": JUDGE["system"]},
        },
        "transcript": transcript,
        "judge_report": judge_text,
    }

    return run_data


def save_run(run_data):
    Path("runs").mkdir(exist_ok=True)
    run_id = run_data["run_id"]
    with open(f"runs/{run_id}.json", "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2, ensure_ascii=False)


def list_runs():
    """Return list of past debate runs, newest first."""
    runs_dir = Path("runs")
    if not runs_dir.exists():
        return []
    runs = []
    for f in runs_dir.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                runs.append({
                    "run_id": data.get("run_id", f.stem),
                    "topic": data.get("topic", "Unknown topic"),
                    "timestamp": data.get("timestamp", ""),
                })
        except (json.JSONDecodeError, IOError):
            continue
    runs.sort(key=lambda r: r["timestamp"], reverse=True)
    return runs


def get_run(run_id):
    """Load a single run by ID."""
    path = Path("runs") / f"{run_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
