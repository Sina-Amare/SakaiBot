"""Prompt lab — exercise the REWRITTEN prompts on a real OpenRouter free model.

Gemini's API geo-blocks this region, so we tune against OpenRouter free models
(which is where the owner's fallback/alt models live anyway). We assemble each
prompt with the REAL builders from src.ai.prompts, send it to OpenRouter with
retry + model-fallback (free models are flaky), and write outputs to
tools/prompt_lab/out/<tag>/ (gitignored). Mock data only.

Run:  venv/Scripts/python.exe tools/prompt_lab/run.py [tag]
"""

import asyncio
import datetime
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))

from openai import AsyncOpenAI  # noqa: E402

from src.ai.prompts import (  # noqa: E402
    PROMPT_ADAPTIVE_PROMPT,
    build_analysis_prompt,
    build_question_prompt,
)

TAG = sys.argv[1] if len(sys.argv) > 1 else "run"
OUT = Path(__file__).resolve().parent / "out" / TAG
OUT.mkdir(parents=True, exist_ok=True)

CANDIDATE_MODELS = [
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "nvidia/nemotron-nano-9b-v2:free",
]


def _key() -> str:
    for line in (PROJECT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY_1="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no OPENROUTER_API_KEY_1 in .env")


def m(sender, text, hh=18, mm=0):
    ts = datetime.datetime(2026, 6, 24, hh, mm, 0).strftime("%Y-%m-%d %H:%M:%S")
    return f"[{ts}] {sender}: {text}"


# Deliberately messy: typos, missing نیم‌فاصله, slang, attached pronouns, emoji,
# Persian↔English code-switching.
MESSY_FA = "\n".join([
    m("سینا", "سلام داداش چطوری؟ دیشب اون پروژه رو دیدی ک فرستادم؟", 18, 1),
    m("نسترن", "اره بابا دیدم خیلیییی باحال بود فقط یکم باگ داشت 😅", 18, 2),
    m("سینا", "کدوم باگ؟ من ک تست کردم اوکی بود رو سیستمم", 18, 3),
    m("نسترن", "رو موبایل میزنه بهم میریزه. فردا حضوری حلش میکنیم", 18, 5),
    m("سینا", "اوکی پس فردا ساعت ۷ کافه همیشگی. جدی این deadline رو میرسیم؟", 18, 6),
    m("نسترن", "میرسیم نترس. تو backend رو تموم کن من frontend رو میزنم", 18, 7),
    m("سینا", "ولی boss گفته اگه نرسیم پروژه کنسله ها", 18, 9),
    m("نسترن", "وای استرس نده الان 😂 میرسیم گفتم بهت", 18, 10),
    m("سینا", "راستی پول اون سرور رو دادی؟ vless هنوز کار نمیکنه", 18, 12),
    m("نسترن", "نه فردا میدم. برم بخوابم کلاس دارم صبح. شب بخیر اجی", 18, 14),
])

THIN_FA = "\n".join([
    m("علی", "سلام", 9, 0), m("رضا", "سلام خوبی؟", 9, 1),
    m("علی", "مرسی. کاری نداشتی؟", 9, 2),
])

ROMANCE_FA = "\n".join([
    m("مانی", "دلم برات تنگ شده بود امروز", 21, 0),
    m("سارا", "جدی؟ معلوم نبود... دو روزه جواب نمیدی", 21, 1),
    m("مانی", "ببخشید درگیر کار بودم قول میدم جبران کنم", 21, 2),
    m("سارا", "همیشه همینو میگی 🙂", 21, 3),
    m("مانی", "این دفعه فرق داره. آخر هفته بریم همون جایی ک دوست داری؟", 21, 4),
    m("سارا", "باشه ببینم چی میشه", 21, 6),
])

ENGLISH = "\n".join([
    m("Maya", "did you push the fix? prod is still throwing 500s", 14, 0),
    m("Alex", "yeah pushed 10 min ago. lemme check the logs", 14, 1),
    m("Maya", "still seeing it, hard refresh maybe?", 14, 2),
    m("Alex", "oh it's the CDN cache. give it 5 min", 14, 3),
    m("Maya", "ok. also can we move standup to 11? 9am is brutal", 14, 5),
    m("Alex", "lol yes please, i'll ping the team", 14, 6),
])


async def call(client, prompt, temperature):
    last = "no model responded"
    for model in CANDIDATE_MODELS:
        for attempt in range(2):
            try:
                r = await client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000, temperature=temperature,
                )
                txt = (r.choices[0].message.content or "").strip()
                if txt:
                    return f"[model={model}]\n\n{txt}"
                last = f"{model}: empty"
            except Exception as exc:  # noqa: BLE001
                last = f"{model}: {type(exc).__name__}: {str(exc)[:80]}"
                await asyncio.sleep(2)
    return f"<<ALL MODELS FAILED>> {last}"


async def save(client, name, prompt, temperature):
    out = await call(client, prompt, temperature)
    (OUT / f"{name}.txt").write_text(out, encoding="utf-8")
    head = out.replace("\n", " ")[:120].encode("ascii", "replace").decode()
    print(f"  {name:28} -> {len(out):5d} chars | {head}")


async def main():
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=_key())
    print(f"out={OUT}")
    jobs = [
        ("messy_fa__fun", build_analysis_prompt("fun", "persian", MESSY_FA, 10), 0.85),
        ("messy_fa__general", build_analysis_prompt("general", "persian", MESSY_FA, 10), 0.5),
        ("thin_fa__fun", build_analysis_prompt("fun", "persian", THIN_FA, 3), 0.85),
        ("romance_fa", build_analysis_prompt("romance", "persian", ROMANCE_FA, 6), 0.6),
        ("english__fun", build_analysis_prompt("fun", "english", ENGLISH, 6), 0.85),
        ("messy_fa__tellme", build_question_prompt("persian", MESSY_FA, "قرار فردا ساعت چنده و کجاست؟"), 0.6),
        ("prompt__tcp_udp", PROMPT_ADAPTIVE_PROMPT.format(user_prompt="فرق TCP و UDP چیه؟ کوتاه و خودمونی"), 0.7),
    ]
    for name, prompt, temp in jobs:
        await save(client, name, prompt, temp)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
