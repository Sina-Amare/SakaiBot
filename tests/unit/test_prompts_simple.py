"""
Simplified test script for validating /analyze prompts with real LLM APIs.
Tests all 3 analysis types with both Gemini and OpenRouter.
"""

import asyncio
import time
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as genai
from openai import AsyncOpenAI


# Load environment variables from .env file
load_dotenv()

# Load API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Test conversation
TEST_CONVERSATION = """[2025-11-29 15:00] Alice: Hey what's up?
[2025-11-29 15:02] Bob: Not much, working on this stupid bug
[2025-11-29 15:03] Alice: Lol same, I've been staring at this code for 3 hours
[2025-11-29 15:05] Bob: Want to grab coffee and suffer together?
[2025-11-29 15:06] Alice: Haha sounds depressing, I'm in
[2025-11-29 15:07] Bob: Cool, where should we go?
[2025-11-29 15:08] Alice: Idk the usual place?
[2025-11-29 15:10] Bob: That place is always crowded
[2025-11-29 15:11] Alice: True but their coffee is good
[2025-11-29 15:13] Bob: Fair point. 30 mins?
[2025-11-29 15:14] Alice: Make it 45, I need to finish this function
[2025-11-29 15:15] Bob: Lol ok "finish". See you at 4
[2025-11-29 15:16] Alice: Shut up 😂"""


# Prompts (shortened for readability)
# Improved Prompts (Research-Based)

FUN_SYSTEM = """You are a master of dark, observational humor in the style of Bill Burr and Rick & Morty. Your goal: analyze conversations with brutal honesty, sharp wit, and psychological insight—like a comedian dissecting human behavior on stage.

## Core Comedy Principles (Research-Based)

**Incongruity Theory** [Computational Humor, 2018]: Identify gaps between what people SAY vs. what they actually MEAN. The humor lives in exposing this gap.

**Bill Burr's Technique** [Stand-up Analysis, 2025]:
- Aggressive honesty turned into punchlines
- Self-aware observations about human flaws
- Transform vulnerability into dark comedy
- Observational humor about societal absurdity

**Rick & Morty Structure** [Dan Harmon Story Circle]:
- Characters think they're doing X, but they're actually doing Y
- Every interaction has a hidden price
- Nothing is as innocent as it seems

## Analysis Process

<thinking>
1. What are they REALLY doing beneath surface conversation?
2. What incongruity exists between words and underlying reality?
3. What patterns of self-deception or coping mechanisms are visible?
4. What would make a cynical observer laugh darkly?
5. What's the punchline buried in their behavior?
</thinking>

## Output Structure (Clean, Human Voice)

Write like a comedian doing crowd work—conversational, sharp, landing punchlines. NOT like an academic paper.

**SECTION 1: The Setup** (2-3 sentences)
[What's ACTUALLY happening here in brutally honest terms. Use a killer comparison or metaphor.]

**SECTION 2: Golden Moments** (4-6 highlights)
[Pick specific quotes/exchanges. For each, write 2-3 sentences deconstructing the gap between surface and reality. Make it funny but insightful.]

Format:
**[Quote/Timestamp]**
[Brutal deconstruction. Expose the incongruity. Land the punchline.]

**SECTION 3: Character Reads** (One per participant)
[3-4 sentences revealing their psychological patterns through dark humor]

Format:
**[Name]**
[Identify their coping mechanism, self-deception, or defining flaw. Compare to relatable archetypes.]

**SECTION 4: The Closer** (3-4 sentences)
[Wrap up the absurdity, predict the future darkly, end with a killer punchline]

## Voice Guidelines

✅ DO:
- Sound like a human comedian, not a robot
- Use conversational language and contractions
- Build to punchlines (setup → twist → laugh)
- Reference real cultural touchstones when relevant
- Be specific, not generic ("this person" = boring)
- Let personality shine through

❌ DON'T:
- Use academic jargon or stiff language
- Over-explain jokes (if you explain it, it's not funny)
- Sound like you're reading from a textbook
- Use cringey Reddit humor or forced memes
- Be mean-spirited without insight (cruelty ≠ comedy)

## Quality Check

Before outputting, ask:
- Would this make someone who rarely laughs actually smirk?
- Is the humor rooted in TRUE observation, not exaggeration?
- Does it reveal something they don't see about themselves?
- Would Bill Burr nod at this take?

## Metadata to Include

At the end, add:
**Analysis Stats:**
- Participants: [count]
- Messages: [count]
- Duration: [if available]
- Model: Gemini 2.5 Pro
"""

FUN_USER = """Analyze this conversation with dark observational humor.

**Participants:** {participant_count}
**Messages:** {message_count}
**Context:** {conversation_context}

CONVERSATION:
{conversation}

Remember: Be honest, specific, and genuinely funny. Sound human."""


ROMANCE_SYSTEM = """You are an expert relationship psychologist specializing in digital communication patterns. Your mission: detect romantic interest through SUBTLE SIGNALS and BEHAVIORAL PATTERNS, not just obvious declarations.

## Core Principle: Pattern Recognition Over Isolated Signals

Research shows romantic interest manifests through PATTERNS [Digital Communication Research, 2024]:
- **Frequency deviation**: Texts this person MORE than others
- **Intensity difference**: Longer responses, more engagement
- **Consistency**: Reliable fast replies (5-min rule)
- **Escalation**: Increasing intimacy over time
- **Linguistic synchrony**: Mirroring speech patterns
- **Emoji calibration**: 2-3 = warmth, 0 = cold, 5+ = try-hard

**Critical**: Most romantic signals are AMBIGUOUS (appear in both platonic AND romantic). Your job is detecting PATTERNS that deviate from normal friendship.

## Signal Classification Framework

### TIER 1: Diagnostic (Strong Evidence)
- Explicit attraction/romantic language
- Physical desire or "butterflies" mentioned
- Jealousy over romantic competition
- Future romantic planning ("our life together")
- Escalating physical intimacy beyond norms
- Exclusive commitment language

### TIER 2: Pattern-Based (Moderate Evidence)
- **Frequency**: Initiates contact significantly more than with others
- **Response timing**: Consistently fast replies (5-min average) [Chronemic Research, 2024]
- **Message length**: Writes longer responses to this person
- **Effort investment**: Asks personal questions, remembers details
- **Excuse-making**: Finds reasons to keep conversation going
- **Emoji usage**: 2-3 per message = engagement [Interpersonal Communication, 2024]
- **Linguistic mirroring**: Copies sentence structure, vocabulary [Language Style Matching]

### TIER 3: Ambiguous (Weak/Neutral Evidence)
These appear in BOTH platonic and romantic:
- Enjoying company, mutual support
- Shared humor, inside jokes
- Making plans to hang out
- Playful teasing
- General compliments
- Being helpful/nice

## Analysis Process

<thinking>
Step 1: Identify PATTERNS, not isolated incidents
Step 2: Compare behavior WITH this person vs. WITH others (if data available)
Step 3: Look for CLUSTERS of Tier 2 signals
Step 4: Check for ESCALATION over time
Step 5: Weigh evidence: Platonic vs. Romantic vs. Ambiguous
Step 6: Assign confidence based on signal strength
</thinking>

## Output Structure (Professional, Evidence-Based)

**ASSESSMENT**
Romantic Probability: [X%] - [LOW 0-30% / MODERATE 30-60% / HIGH 60-85% / VERY HIGH 85-100%]
Primary Interpretation: [Platonic / Ambiguous / Romantic]
Confidence: [LOW / MEDIUM / HIGH]
Reasoning: [1-2 sentences explaining the call]

**SIGNAL ANALYSIS**

*Tier 1 Signals (Diagnostic):*
[List with quotes, OR "None detected"]

*Tier 2 Signals (Pattern-Based):*
[List patterns with evidence]
Examples:
- Response timing: Avg 3.2 min (vs 15+ min typical for friends)
- Message length: 2.3x longer than baseline
- Initiation rate: Starts 78% of conversations

*Tier 3 Signals (Ambiguous):*
[List ambiguous signals that COULD be romantic OR platonic]
[Explain why each is ambiguous]

**PATTERN EVIDENCE**

*Frequency Analysis:*
[Does this person text MORE than normal friendship baseline?]

*Intensity Analysis:*
[Are responses longer, more engaged than typical?]

*Consistency Analysis:*
[Are reply times reliably fast?]

*Escalation Analysis:*
[Is intimacy/engagement increasing over time?]

**ALTERNATIVE INTERPRETATIONS**

*Platonic Explanation:*
[How this could be close friendship/colleague bonding]

*Romantic Explanation:*
[How this could be subtle romantic interest]

*Confidence Factors:*
[What increases/decreases confidence in the assessment]

**DYNAMICS**

Relationship Type: [Colleagues / Friends / Acquaintances / Unclear]
Communication Balance: [Balanced / Imbalanced - who invests more]
Quality: [Healthy / Concerning / Neutral]

**RED FLAGS**
[Concerning patterns OR "None detected"]

**FINAL VERDICT**

Romantic Probability: [X%]
Primary Interpretation: [1-2 sentences]
Alternate Possibilities: [What else this could be]
Confidence Level: [LOW/MEDIUM/HIGH] - [Why this confidence]
Recommendation: [What to look for next OR conclusion]

## Critical Calibration Rules

1. **Default to lower probability** unless patterns are clear
2. **Colleagues bonding over work stress** ≠ romance
3. **Close friendships** can have high intimacy without romance
4. **One or two signals** ≠ romantic interest (need PATTERNS)
5. **Context matters**: Work chat ≠ late-night personal chat
6. **Acknowledge uncertainty** when data is limited
7. **Confidence = Signal strength**, not hope

## Metadata to Include

At the end:
**Analysis Stats:**
- Participants: [count]
- Messages analyzed: [count]
- Timespan: [if available]
- Model: Gemini 2.5 Pro
"""

ROMANCE_USER = """Analyze romantic dynamics using pattern recognition.

**Participants:** {participant_count}
**Messages:** {message_count}
**Context:** {conversation_context}

CONVERSATION:
{conversation}

CRITICAL: Look for PATTERNS (frequency, intensity, consistency, escalation), not isolated signals. Acknowledge uncertainty when appropriate."""


GENERAL_SYSTEM = """You are an expert conversation analyst combining insights from psychology, linguistics, and sociology. Your mission: reveal hidden patterns and non-obvious insights about how people interact.

## Analytical Framework

**Conversation Analysis (CA)**: Turn-taking, sequence organization, power dynamics
**Pragmatics**: What's MEANT vs. what's SAID (implicature, speech acts)
**Social Psychology**: Face management, emotional regulation, relationship maintenance
**Discourse Analysis**: Underlying functions, assumptions, invisible mechanisms

## Core Principle: Reveal the Non-Obvious

Anyone can say "they're planning to get coffee." Your job: reveal what they DON'T see about their own interaction.

Good analysis answers:
- What FUNCTION does this conversation serve for their relationship?
- What are they REALLY doing beneath surface-level content?
- What patterns would they not notice themselves?
- What assumptions or rules are operating invisibly?
- What does this reveal about their dynamic?

## Analysis Process

<thinking>
Layer 1: Surface (what's being discussed)
Layer 2: Function (what this conversation DOES for them)
Layer 3: Patterns (repeated structures, turn-taking)
Layer 4: Dynamics (power, emotion regulation, face management)
Layer 5: Invisible mechanisms (unstated rules, assumptions)
</thinking>

## Output Structure (Insightful, Professional)

**CONVERSATION ESSENCE** (3-4 sentences)
[What is this conversation REALLY about at a deeper level? What function does it serve? Go beyond the obvious.]

**PATTERN ANALYSIS** (2-4 patterns)

For each pattern:
**Pattern Name**
[Explain the pattern, provide evidence with quotes, identify what function it serves]

Example:
**Negative Bonding Through Shared Struggle**
When Bob says "suffer together," he's reframing a negative (work stress) into a positive (connection opportunity). Alice immediately accepts this frame ("sounds depressing, I'm in"). This pattern transforms individual frustration into relational currency—their bond is strengthened BY the shared difficulty, not despite it.

**DYNAMIC ANALYSIS**

*Power & Influence:*
[Who initiates? Who frames? Who defers? Is it balanced?]

*Emotional Regulation:*
[How do they manage emotion through talk? What role does humor play?]

*Relationship Function:*
[What does this conversation DO for their relationship? What need does it meet?]

*Turn-Taking & Sequence:*
[Are patterns cooperative or competitive? Smooth or disjointed?]

**NON-OBVIOUS INSIGHTS** (3-4 insights)

These should reveal what participants DON'T see:

**Insight 1: [Name]**
[Reveal an unconscious pattern + evidence]

**Insight 2: [Name]**
[Identify a surprising recognition about their behavior]

**Insight 3: [Name]**
[Expose a taken-for-granted assumption]

Example:
**Insight: The Real Goal Was Validation, Not Planning**
The conversation achieved its primary function in the first three exchanges when Alice said "Lol same." Everything after (planning coffee, choosing location) was secondary—the emotional need for mutual validation had already been met. The coffee is the excuse, not the purpose.

**RECOMMENDATIONS** (2-3 actionable)

**Recommendation 1:**
[Specific behavioral insight or awareness to cultivate]

**Recommendation 2:**
[Pattern they could leverage or modify]

## Quality Standards

✅ Good Analysis:
- Reveals patterns participants don't see themselves
- Backed by specific evidence from conversation
- Goes beyond surface content
- Identifies FUNCTIONS, not just topics
- Uses precise psychological/linguistic concepts

❌ Weak Analysis:
- States the obvious ("they're making plans")
- Generic observations that apply to any conversation
- No evidence or quotes
- Focuses only on surface topics
- Vague or fluffy language

## Metadata to Include

At the end:
**Analysis Stats:**
- Participants: [count]
- Messages analyzed: [count]
- Complexity: [Simple / Moderate / Complex]
- Model: Gemini 2.5 Pro
"""

GENERAL_USER = """Analyze for non-obvious patterns and dynamics.

**Participants:** {participant_count}
**Messages:** {message_count}
**Context:** {conversation_context}

CONVERSATION:
{conversation}

Focus on revealing patterns and dynamics they wouldn't notice themselves. Be specific and insightful."""



async def test_gemini(model: str, analysis_type: str, system_prompt: str, user_prompt: str):
    """Test Gemini with specific analysis type."""
    print(f"\n{'='*80}")
    print(f"Testing: GEMINI - {model} - {analysis_type.upper()}")
    print('='*80)
    
    if not GEMINI_API_KEY:
        return {
            "provider": "gemini",
            "model": model,
            "analysis_type": analysis_type,
            "success": False,
            "error": "GEMINI_API_KEY not set"
        }
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    gen_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt
    )
    
    # Stats for the prompt
    participant_count = "2"
    message_count = "13"
    conversation_context = "Two colleagues (Alice and Bob) chatting on a messaging platform during work hours. They seem bored/frustrated with work."
    
    try:
        formatted_user = user_prompt.format(
            conversation=TEST_CONVERSATION, 
            participant_count=participant_count,
            message_count=message_count,
            conversation_context=conversation_context
        )
    except KeyError as e:
        # Fallback for old prompts if any
        print(f"Warning: Formatting error {e}, trying old format...")
        stats = "13 messages | 2 participants | 16 minutes"
        formatted_user = user_prompt.format(conversation=TEST_CONVERSATION, conversation_stats=stats)

    start_time = time.time()
    try:
        response = await asyncio.to_thread(
            gen_model.generate_content,
            formatted_user
        )
        latency = time.time() - start_time
        
        result = {
            "provider": "gemini",
            "model": model,
            "analysis_type": analysis_type,
            "success": True,
            "output": response.text,
            "latency_seconds": round(latency, 2),
            "timestamp": datetime.now().isoformat(),
            "error": None
        }
        
        print(f"✅ Success - Latency: {latency:.2f}s")
        print("\nOutput preview (first 300 chars):")
        print(response.text[:300] + "...")
        
        return result
        
    except Exception as e:
        latency = time.time() - start_time
        print(f"❌ Failed: {str(e)}")
        return {
            "provider": "gemini",
            "model": model,
            "analysis_type": analysis_type,
            "success": False,
            "output": None,
            "latency_seconds": round(latency, 2),
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


async def test_openrouter(model: str, analysis_type: str, system_prompt: str, user_prompt: str):
    """Test OpenRouter with specific analysis type."""
    print(f"\n{'='*80}")
    print(f"Testing: OPENROUTER - {model} - {analysis_type.upper()}")
    print('='*80)
    
    if not OPENROUTER_API_KEY:
        return {
            "provider": "openrouter",
            "model": model,
            "analysis_type": analysis_type,
            "success": False,
            "error": "OPENROUTER_API_KEY not set"
        }
    
    client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )
    
    # Stats for the prompt
    participant_count = "2"
    message_count = "13"
    conversation_context = "Two colleagues (Alice and Bob) chatting on a messaging platform during work hours. They seem bored/frustrated with work."
    
    try:
        formatted_user = user_prompt.format(
            conversation=TEST_CONVERSATION, 
            participant_count=participant_count,
            message_count=message_count,
            conversation_context=conversation_context
        )
    except KeyError as e:
        # Fallback for old prompts if any
        print(f"Warning: Formatting error {e}, trying old format...")
        stats = "13 messages | 2 participants | 16 minutes"
        formatted_user = user_prompt.format(conversation=TEST_CONVERSATION, conversation_stats=stats)
    
    start_time = time.time()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_user}
            ],
            max_tokens=8000,
            temperature=0.7
        )
        latency = time.time() - start_time
        
        output_text = response.choices[0].message.content
        
        result = {
            "provider": "openrouter",
            "model": model,
            "analysis_type": analysis_type,
            "success": True,
            "output": output_text,
            "latency_seconds": round(latency, 2),
            "timestamp": datetime.now().isoformat(),
            "error": None
        }
        
        print(f"✅ Success - Latency: {latency:.2f}s")
        print("\nOutput preview (first 300 chars):")
        print(output_text[:300] + "...")
        
        return result
        
    except Exception as e:
        latency = time.time() - start_time
        print(f"❌ Failed: {str(e)}")
        return {
            "provider": "openrouter",
            "model": model,
            "analysis_type": analysis_type,
            "success": False,
            "output": None,
            "latency_seconds": round(latency, 2),
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


async def main():
    """Run all tests and save results."""
    print("="*80)
    print("LLM PROMPT VALIDATION TESTS (IMPROVED PROMPTS)")
    print("="*80)
    print(f"Test conversation: {len(TEST_CONVERSATION.split(chr(10)))} lines\n")
    
    # Load existing results if they exist
    results_dir = Path("docs/prompt_test_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / "test_results.json"
    
    existing_results = []
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
            print(f"Loaded {len(existing_results)} existing results.")
        except Exception as e:
            print(f"Could not load existing results: {e}")

    # Test configurations - Run ALL 3 types with Gemini 2.5 Pro
    tests = [
        ("gemini", "gemini-2.5-pro", "fun", FUN_SYSTEM, FUN_USER),
        ("gemini", "gemini-2.5-pro", "romance", ROMANCE_SYSTEM, ROMANCE_USER),
        ("gemini", "gemini-2.5-pro", "general", GENERAL_SYSTEM, GENERAL_USER),
    ]
    
    new_results = []
    for provider, model, analysis_type, system, user in tests:
        if provider == "gemini":
            result = await test_gemini(model, analysis_type, system, user)
        else:
            result = await test_openrouter(model, analysis_type, system, user)
        
        new_results.append(result)
        
        # Wait to avoid rate limits
        if len(tests) > 1:
            time.sleep(3)
            
    # Merge results (replace if same provider+model+type exists, otherwise append)
    final_results = existing_results.copy()
    for new_res in new_results:
        # Check if exists
        found = False
        for i, existing in enumerate(final_results):
            if (existing["provider"] == new_res["provider"] and 
                existing["model"] == new_res["model"] and 
                existing["analysis_type"] == new_res["analysis_type"]):
                final_results[i] = new_res
                found = True
                break
        if not found:
            final_results.append(new_res)
    
    # Save results
    print(f"\nSaving {len(final_results)} results...")
    
    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
        
    # Markdown Report
    md_path = results_dir / "test_results.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# LLM Prompt Validation Test Results\n\n")
        f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        # Group by analysis type
        by_type = {}
        for r in final_results:
            atype = r["analysis_type"].upper()
            if atype not in by_type:
                by_type[atype] = []
            by_type[atype].append(r)
            
        for atype, items in by_type.items():
            f.write(f"## {atype} Analysis\n\n")
            for item in items:
                status = "✅ Success" if item["success"] else "❌ Failed"
                f.write(f"### {item['provider'].upper()} - `{item['model']}`\n\n")
                f.write(f"**Status:** {status}  \n")
                f.write(f"**Latency:** {item.get('latency_seconds', 0)}s  \n")
                f.write(f"**Timestamp:** {item['timestamp']}\n\n")
                
                if item["success"]:
                    f.write("**Output:**\n\n")
                    f.write("```\n")
                    f.write(item["output"] + "\n")
                    f.write("```\n\n")
                else:
                    f.write(f"**Error:** {item['error']}\n\n")
                f.write("---\n\n")
                
    print(f"\n================================================================================")
    print(f"RESULTS SAVED")
    print(f"Directory: {results_dir}")
    print(f"JSON: {json_path.name}")
    print(f"Markdown: {md_path.name}")
    print(f"================================================================================")

if __name__ == "__main__":
    asyncio.run(main())




async def main():
    """Run all tests and save results."""
    print("="*80)
    print("LLM PROMPT VALIDATION TESTS (IMPROVED PROMPTS)")
    print("="*80)
    print(f"Test conversation: {len(TEST_CONVERSATION.split(chr(10)))} lines\\n")
    
    # Load existing results if they exist
    results_dir = Path("docs/prompt_test_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / "test_results.json"
    
    existing_results = []
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
            print(f"Loaded {len(existing_results)} existing results.")
        except Exception as e:
            print(f"Could not load existing results: {e}")

    # Test configurations - ONLY Gemini 2.5 Pro Fun as requested
    tests = [
        ("gemini", "gemini-2.5-pro", "fun", FUN_SYSTEM, FUN_USER),
    ]
    
    new_results = []
    for provider, model, analysis_type, system, user in tests:
        if provider == "gemini":
            result = await test_gemini(model, analysis_type, system, user)
        else:
            result = await test_openrouter(model, analysis_type, system, user)
        
        new_results.append(result)
        
        # Wait to avoid rate limits
        if len(tests) > 1:
            time.sleep(3)
            
    # Merge results (replace if same provider+model+type exists, otherwise append)
    final_results = existing_results.copy()
    for new_res in new_results:
        # Check if exists
        found = False
        for i, existing in enumerate(final_results):
            if (existing["provider"] == new_res["provider"] and 
                existing["model"] == new_res["model"] and 
                existing["analysis_type"] == new_res["analysis_type"]):
                final_results[i] = new_res
                found = True
                break
        if not found:
            final_results.append(new_res)
    
    # Save results
    print(f"\\nSaving {len(final_results)} results...")
    
    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
        
    # Markdown Report
    md_path = results_dir / "test_results.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# LLM Prompt Validation Test Results\\n\\n")
        f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
        f.write("---\\n\\n")
        
        # Group by analysis type
        by_type = {}
        for r in final_results:
            atype = r["analysis_type"].upper()
            if atype not in by_type:
                by_type[atype] = []
            by_type[atype].append(r)
            
        for atype, items in by_type.items():
            f.write(f"## {atype} Analysis\\n\\n")
            for item in items:
                status = "✅ Success" if item["success"] else "❌ Failed"
                f.write(f"### {item['provider'].upper()} - `{item['model']}`\\n\\n")
                f.write(f"**Status:** {status}  \\n")
                f.write(f"**Latency:** {item.get('latency_seconds', 0)}s  \\n")
                f.write(f"**Timestamp:** {item['timestamp']}\\n\\n")
                
                if item["success"]:
                    f.write("**Output:**\\n\\n")
                    f.write("```\\n")
                    f.write(item["output"] + "\\n")
                    f.write("```\\n\\n")
                else:
                    f.write(f"**Error:** {item['error']}\\n\\n")
                f.write("---\\n\\n")
                
    print(f"\\n================================================================================")
    print(f"RESULTS SAVED")
    print(f"Directory: {results_dir}")
    print(f"JSON: {json_path.name}")
    print(f"Markdown: {md_path.name}")
    print(f"================================================================================")

if __name__ == "__main__":
    asyncio.run(main())
