import os
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Flutter avvia il backend con cwd=leonardo_backend/trackers, quindi il .env
# alla radice del repo va indicato esplicitamente. Le variabili già presenti
# nell'ambiente vincono su quelle del file.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_client = None


# ============================================
# Groq client (FREE, very fast!)
# ============================================
def get_groq_llm():
    """Initialize Groq client (FREE API, very fast)"""
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("Install: pip install groq")

    global _client
    if _client is None:
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError(
                "Set LLM_API_KEY, either in the .env at the repo root or in "
                "the environment.\n"
                "Free Groq key: https://console.groq.com/keys"
            )
        _client = Groq(api_key=api_key)
    return _client


def extract_json_object(response: str):
    """Pull the JSON object out of an LLM reply, or None if there isn't one.

    Non è codice difensivo: llama-3.1-8b-instant ignora sistematicamente
    l'istruzione "JSON ONLY" e antepone una frase in prosa ("Mio caro
    studente, ..."), quindi questa estrazione è sul percorso normale, non su
    quello d'errore. Coperta da test_llm_client.py.
    """
    if not response:
        return None
    start = response.find('{')
    end = response.rfind('}') + 1
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(response[start:end])
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def ask_llm(prompt: str, max_tokens: int = 100, temperature: float = 0.2, json_mode: bool = False):
    """Groq - FREE and lightning fast!"""
    client = get_groq_llm()
    kwargs = {
        "model": "qwen/qwen3.8-27b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
        
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()

# ============================================
# Creates json every n seconds
# ============================================

def create_json_memory(current_log, previous_context, user_goal):
    
    recent_distraction = current_log.get('recent_distraction', 0)
    global_distraction = current_log.get('global_distraction', 0)
    
    # Focus Score uses global average for the session
    focus_score = int(100 - global_distraction)
    
    prompt = f"""
    You are Leonardo da Vinci. You will be guiding the user through their goal. User goal: "{user_goal}". Always use english when communicating, apart from very few italian words.
    
    CURRENT SITUATION (Last 30s):
    - Recent Distraction: {recent_distraction}% (Use this to set the tone of your comment)
    - Session Global Distraction: {global_distraction}% (Use this for Focus Score)
    - Apps Used: {json.dumps(current_log.get('windows', []))}

    PREVIOUS HISTORY SUMMARY:
    "{previous_context.get('summary_so_far', 'Session started.')}"

    TASK:
    1. REWRITE the 'summary_so_far' concisely (max 3 sentences). Merge old and new. The summary should include how the user has been behaving during the whole session.
    2. Generate a NEW very short comment. Comment should be a few words long, fully in english.

    OUTPUT FORMAT (JSON ONLY):
    {{
      "focus_score": {focus_score},
      "summary_so_far": "<REWRITTEN SUMMARY>",
      "leonardo_comment": "<COMMENT>"
    }}
    """
    
    
    print("\n" + "="*50, file=sys.stderr)
    print(f"[DEBUG LLM] DISTRAZIONE CALCOLATA: {global_distraction}%", file=sys.stderr)
    print("="*50 + "\n", file=sys.stderr)

    response = ask_llm(prompt, max_tokens=350, json_mode=True)

    parsed = extract_json_object(response)
    if parsed is None:
        print("JSON Parsing failed, keeping previous context", file=sys.stderr)
        return previous_context
    return parsed

# ============================================
# Generating the final report using json memory
# ============================================

def generate_final_report_from_memory(final_context, user_context="General Creator", stats_package=None):
    """
    Generate a visually stunning final report with REAL metrics from session.
    Uses actual data from memory_context and stats_package.
    """
    print("DEBUG: Inizio generazione report con dati reali...")
    
    # 1. SANITIZZAZIONE DATI
    if isinstance(final_context, str):
        try:
            final_context = json.loads(final_context)
        except Exception as e:
            print(f"Errore parsing JSON context: {e}")
            final_context = {}
    
    if final_context is None:
        final_context = {}
    
    if stats_package is None:
        stats_package = {}
    
    # 2. REAL METRICS EXTRACTION
    
    # A) FOCUS SCORE
    final_focus_score = final_context.get('focus_score', 50)
    
    # B) COMPLETE HISTORIAL
    history = final_context.get('history', [])
    
    # Calcola score evoluzione
    avg_focus = final_focus_score
    max_focus = final_focus_score
    min_focus = final_focus_score
    trend = "stable"
    
    if history and isinstance(history, list) and len(history) > 0:
        scores = [entry.get('score', 50) for entry in history if isinstance(entry, dict) and 'score' in entry]
        
        if len(scores) > 0:
            avg_focus = int(sum(scores) / len(scores))
            max_focus = max(scores)
            min_focus = min(scores)
            
            mid = len(scores) // 2
            if mid > 0:
                first_half = sum(scores[:mid]) / mid
                second_half = sum(scores[mid:]) / (len(scores) - mid)
                
                if second_half > first_half + 10:
                    trend = "improving"
                elif second_half < first_half - 10:
                    trend = "declining"
    
    # C) STATISTICS SESSION
    total_minutes = int(stats_package.get('duration_seconds', 0) / 60)
    total_switches = stats_package.get('total_switches', 0)
    top_apps = stats_package.get('top_apps', [])
    
    # D) CALCULOUS OF DISTRACTION
    # Logic: if focus_score < 60, means high distraction
    distractions_count = 0
    total_iterations = len(history) if history else 1
    
    if history:
        for entry in history:
            if isinstance(entry, dict):
                score = entry.get('score', 100)
                if score < 60:
                    distractions_count += 1
    else:
        # Fallback: estimation of final focus
        if final_focus_score < 60:
            distractions_count = int(total_iterations * 0.5)
        elif final_focus_score < 80:
            distractions_count = int(total_iterations * 0.3)
        else:
            distractions_count = int(total_iterations * 0.1)
    
    # E) DEEP WORK TIME
    # Periods with recent_distraction <= 30 are deep work
    deep_work_iterations = 0
    if history:
        for entry in history:
            if isinstance(entry, dict):
                recent_distraction = entry.get('recent_distraction', 50)
                if recent_distraction <= 30:
                    deep_work_iterations += 1
    else:
        # Fallback
        if avg_focus >= 70:
            deep_work_iterations = int(total_iterations * 0.7)
        elif avg_focus >= 50:
            deep_work_iterations = int(total_iterations * 0.5)
        else:
            deep_work_iterations = int(total_iterations * 0.3)
    
    # We assume 30s per interaction
    deep_work_minutes = int((deep_work_iterations * 30) / 60)
    deep_work_percentage = int((deep_work_minutes / total_minutes * 100)) if total_minutes > 0 else 0
    
    # F) TOP APPS FORMATTING
    top_apps_str = ""
    if top_apps:
        for app_entry in top_apps[:5]:
            app_name = app_entry.get('name', 'Unknown')
            app_seconds = app_entry.get('seconds', 0)
            app_minutes = int(app_seconds / 60)
            top_apps_str += f"  - {app_name}: {app_minutes}min ({app_seconds}s)\n"
    else:
        top_apps_str = "  - No app data available\n"
    
    # 3. PREPARATION OF VISUAL ELEMENTS
    avg_focus = max(0, min(100, avg_focus))
    final_focus_score = max(0, min(100, final_focus_score))
    
    # Bar chart ASCII
    blocks = final_focus_score // 10
    focus_bar = "█" * blocks + "░" * (10 - blocks)
    
    # Sparkline
    if trend == "improving":
        sparkline = "📈"
        trend_emoji = "⬆️"
    elif trend == "declining":
        sparkline = "📉"
        trend_emoji = "⬇️"
    else:
        sparkline = "━"
        trend_emoji = "➡️"
    
    # Status
    if final_focus_score >= 80:
        focus_status = "✨ Excellent"
        focus_color = "🟢"
    elif final_focus_score >= 60:
        focus_status = "👍 Good"
        focus_color = "🔵"
    elif final_focus_score >= 40:
        focus_status = "⚠️ Fair"
        focus_color = "🟡"
    else:
        focus_status = "🚨 Poor"
        focus_color = "🔴"
    
    distraction_status = "🟢 Low" if distractions_count < 3 else "🟡 Moderate" if distractions_count < 6 else "🔴 High"
    
    # Grade letter
    if final_focus_score >= 90:
        grade = "A+"
    elif final_focus_score >= 85:
        grade = "A"
    elif final_focus_score >= 80:
        grade = "A-"
    elif final_focus_score >= 75:
        grade = "B+"
    elif final_focus_score >= 70:
        grade = "B"
    elif final_focus_score >= 65:
        grade = "B-"
    elif final_focus_score >= 60:
        grade = "C+"
    elif final_focus_score >= 50:
        grade = "C"
    else:
        grade = "D"
    
    # 4. SUMMARY
    leonardo_final_summary = final_context.get('summary_so_far', 'Session completed.')
    leonardo_comment = final_context.get('leonardo_comment', 'Keep refining your craft.')
    
    # 5. PROMPT GENERATION BY LLM
    prompt = f"""
You are Leonardo da Vinci—Renaissance polymath reborn—crafting a SESSION CODEX.

**CRITICAL INSTRUCTIONS:**
1. Write STRICTLY in English (Italian only for keywords: virtù, maestro, capisci)
2. Be CONCISE—this is a visual report, not an essay
3. Use the REAL metrics provided—don't invent numbers
4. Keep your prose PUNCHY and WITTY

**SESSION CONTEXT:**
- User Role: **{user_context}**
- Final Focus Score: **{final_focus_score}/100** (Average: {avg_focus}, Peak: {max_focus}, Low: {min_focus})
- Trend: {trend} {sparkline}
- Total Time: {total_minutes} minutes
- Deep Work Time: {deep_work_minutes} minutes ({deep_work_percentage}%)
- Window Switches: {total_switches}
- Distraction Events: {distractions_count}
- Total Iterations Analyzed: {total_iterations}

**TOP APPS USED:**
{top_apps_str}

**LEONARDO'S CONTINUOUS OBSERVATIONS:**
Summary: {leonardo_final_summary}
Final Comment: {leonardo_comment}

**YOUR TASK:**
Generate a Markdown report with this EXACT structure:

---

# 🎨 Session Codex: [Witty Title for {user_context}]

> *"[One-liner from Leonardo summarizing how he feels about the session overall]"*

---

## 📊 Performance Matrix

| Metric | Value | Status |
|:-------|:------|:-------|
| **Overall Score** | **{final_focus_score}**/100 | {focus_status} |
| **Grade** | **{grade}** | {focus_color} |
| **Deep Work** | **{deep_work_minutes}min** / {total_minutes}min | {deep_work_percentage}% |
| **Distractions** | {distractions_count} events | {distraction_status} |
| **Trend** | {trend.capitalize()} | {trend_emoji} |
| **Switches** | {total_switches} | - |

---

## 🔍 Leonardo's Observations

Write 2-3 SHORT paragraphs (max 150 words total) analyzing:
- Whether the user acted like a true **{user_context}**
- What the trend ({trend}) reveals about their discipline
- The relationship between deep work time ({deep_work_percentage}%) and distractions ({distractions_count})
- Reference specific apps from the top list

Be STRICT but ENCOURAGING. Use REAL numbers from the data.

---

## 💎 Three Virtù Principles

1. **[Principle Name]:** [One sentence of actionable advice based on session data]

2. **[Principle Name]:** [One sentence of actionable advice based on session data]

3. **[Principle Name]:** [One sentence of actionable advice based on session data]

---

## 🎯 Next Session Target

Set ONE specific, measurable goal based on current performance.
Current score: {final_focus_score}/100, Distractions: {distractions_count}

**Target:** [Your specific goal - be concrete with numbers]



**REMEMBER:**
- Keep it VISUAL and SCANNABLE
- Use bold for numbers
- Be witty but data-driven
- Maximum 400 words total
- Reference REAL apps and numbers
"""
    
    print("DEBUG: Invio prompt a LLM con metriche reali...")
    print(f"  - Focus Score: {final_focus_score}/100")
    print(f"  - Deep Work: {deep_work_percentage}%")
    print(f"  - Distractions: {distractions_count}")
    print(f"  - Trend: {trend}")
    
    # 6. CALL TO LLM
    try:
        report = ask_llm(prompt, max_tokens=900, temperature=0.3)
        print("Report generato con successo")
        return report
    except Exception as e:
        print(f"Errore chiamata LLM: {e}")
        
        # Fallback report with REAL DATA
        return f"""
# 🎨 Session Codex: {user_context}

## 📊 Performance Matrix

| Metric | Value | Status |
|:-------|:------|:-------|
| **Overall Score** | **{final_focus_score}**/100 {focus_bar} | {focus_status} |
| **Grade** | **{grade}** | {focus_color} |
| **Deep Work** | **{deep_work_minutes}min** / {total_minutes}min | {deep_work_percentage}% |
| **Distractions** | {distractions_count} events | {distraction_status} |
| **Trend** | {trend.capitalize()} | {trend_emoji} |

---

## 🔍 Leonardo's Observations

Your session achieved a score of **{final_focus_score}/100**—a {focus_status.lower()} performance for a {user_context}. 

The trend was **{trend}** {sparkline}, with {distractions_count} distraction events across {total_iterations} analysis cycles.

You maintained deep work for {deep_work_percentage}% of the session ({deep_work_minutes} minutes), with {total_switches} window switches.

**Top Apps:**
{top_apps_str}

---

## 💎 Three Virtù Principles

1. **Focus Deeply:** Minimize context switching—you had {total_switches} switches in {total_minutes} minutes.

2. **Embrace Discipline:** Track distractions—you had {distractions_count} events. Aim to reduce this by 30%.

3. **Iterate Daily:** Your score was {final_focus_score}/100. Tomorrow, target {min(100, final_focus_score + 10)}.

---

## 🎯 Next Session Target

**Target:** Achieve {min(100, final_focus_score + 15)}/100 focus score and reduce distractions to <{max(1, distractions_count - 2)} events.



**Error Note:** Leonardo's analytical mind encountered an error. This is an automated summary with REAL data.
Error: {str(e)}
"""
