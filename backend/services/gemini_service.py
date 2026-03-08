import os
import json
import re
from typing import List, Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")


def _safe_json(text: str) -> Optional[dict]:
    """Try to extract JSON from Gemini response."""
    try:
        # Try direct parse first
        return json.loads(text.strip())
    except Exception:
        pass
    # Try extracting JSON block from markdown
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────
# Feature 1 — Analyze + Auto-Tag (per video)
# ─────────────────────────────────────────────

def analyze_batch(videos: List[Dict]) -> List[Dict]:
    """
    Analyze a batch of videos using Gemini.
    Returns each video enriched with: explanation, level, type, topics,
    estimated_minutes, requires_previous.
    """
    results = []

    for video in videos:
        title = video.get("title", "")
        description = video.get("description", "")[:1500]
        transcript = video.get("transcript", "")[:5000]
        position = video.get("position", 0)

        context_parts = [f"عنوان الفيديو: {title}"]
        if description:
            context_parts.append(f"وصف الفيديو:\n{description}")
        if transcript:
            context_parts.append(f"محتوى الفيديو (Transcript):\n{transcript}")
        context = "\n\n".join(context_parts)

        prompt = f"""أنت مساعد تعليمي متخصص في تحليل محتوى الفيديوهات التقنية والتعليمية باللغة العربية.

بناءً على المعلومات التالية للفيديو رقم {position + 1}:

{context}

أجب بـ JSON فقط (بدون أي نص خارجه) بالشكل التالي:

{{
  "explanation": "اكتب شرحاً مفصلاً وعميقاً لا يقل عن 600 كلمة يتضمن بالضرورة:\n\n**1. الهدف الرئيسي والسياق العام:**\nما الذي يسعى الفيديو لتعليمه؟ لماذا هذا الموضوع مهم في مجاله؟ ما السياق الأكبر الذي ينتمي إليه؟\n\n**2. المفاهيم والمواضيع المغطاة بالتفصيل:**\nاشرح كل مفهوم ورد في الفيديو بعمق — ليس مجرد ذكر الاسم، بل اشرح ما هو، كيف يعمل، ولماذا يُستخدم. استخدم أمثلة إذا أمكن.\n\n**3. ماذا ستتعلم وما المهارة التي ستكتسبها:**\nبعد المشاهدة، ماذا يستطيع الشخص أن يفعل؟ ما التحول في المعرفة أو المهارة الذي يحدث؟\n\n**4. الأهمية العملية والتطبيقية:**\nأين يُطبَّق هذا في الواقع؟ ما المشكلات التي يحلها؟ من يستفيد منه في أي مجال؟\n\n**5. الترابط والتدرج مع المحتوى الأوسع:**\nهل يعتمد على مفاهيم سابقة؟ ما الذي يجب معرفته قبله؟ ما الموضوعات التي تأتي بعده طبيعياً لمن أراد الاستمرار؟\n\nالشرح يجب أن يكون غنياً ومفيداً حقاً، كأنك تشرح لشخص يريد أن يفهم كل جوانب هذا الفيديو دون أن يشاهده. لا تكتفِ بسطرين أو ثلاثة لأي نقطة.",
  "level": "مبتدئ أو متوسط أو متقدم",
  "type": "نظري أو تطبيقي أو مراجعة أو مشروع",
  "topics": ["موضوع1", "موضوع2", "موضوع3"],
  "estimated_minutes": 30,
  "requires_previous": true
}}"""

        try:
            response = model.generate_content(prompt)
            parsed = _safe_json(response.text.strip())
            if parsed and "explanation" in parsed:
                results.append({
                    **video,
                    "explanation": parsed.get("explanation", ""),
                    "level": parsed.get("level", ""),
                    "type": parsed.get("type", ""),
                    "topics": parsed.get("topics", []),
                    "estimated_minutes": parsed.get("estimated_minutes"),
                    "requires_previous": parsed.get("requires_previous", False),
                    "analyzed": True
                })
            else:
                # Fallback: treat whole response as explanation
                results.append({
                    **video,
                    "explanation": response.text.strip(),
                    "level": "",
                    "type": "",
                    "topics": [],
                    "estimated_minutes": None,
                    "requires_previous": False,
                    "analyzed": True
                })
        except Exception as e:
            results.append({
                **video,
                "explanation": f"تعذر تحليل هذا الفيديو: {str(e)}",
                "level": "",
                "type": "",
                "topics": [],
                "estimated_minutes": None,
                "requires_previous": False,
                "analyzed": True
            })

    return results


# ─────────────────────────────────────────────
# Feature 2 — Playlist Executive Summary
# ─────────────────────────────────────────────

def generate_playlist_summary(videos: List[Dict], playlist_name: str) -> str:
    """
    Generate a comprehensive executive summary for the entire playlist.
    """
    # Build a compact context: position, title, topics, level
    video_lines = []
    for v in videos:
        if not v.get("analyzed"):
            continue
        topics_str = "، ".join(v.get("topics", [])) if v.get("topics") else "—"
        level = v.get("level", "—")
        video_lines.append(
            f"فيديو {v.get('position', 0) + 1}: {v.get('title', '')} | المستوى: {level} | المواضيع: {topics_str}"
        )

    if not video_lines:
        return "لا توجد فيديوهات محللة بعد."

    content = "\n".join(video_lines)

    prompt = f"""أنت خبير تعليمي. تم تحليل الـ Playlist التالية:

اسم الـ Playlist: {playlist_name}

قائمة الفيديوهات المحللة:
{content}

اكتب ملخصاً تنفيذياً شاملاً يتضمن:

1. **نظرة عامة**: ما الذي تغطيه هذه الـ Playlist بشكل عام؟
2. **أهم 5 مفاهيم**: أبرز المواضيع التي يكتسبها المشاهد.
3. **المستوى العام**: هل هي مناسبة للمبتدئين أم المتقدمين؟
4. **نقاط القوة**: ما الذي يميز هذا المنهج؟
5. **الثغرات أو النواقص**: هل هناك مواضيع مهمة غير مغطاة؟
6. **التوصية النهائية**: لمن تناسب هذه الـ Playlist؟

اكتب بأسلوب احترافي وواضح بالعربية."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"تعذر توليد الملخص: {str(e)}"


# ─────────────────────────────────────────────
# Feature 3 — Learning Path Generator
# ─────────────────────────────────────────────

def generate_learning_path(videos: List[Dict]) -> Dict:
    """
    Generate a smart learning path grouping videos into phases.
    Returns: { phases: [ { title, description, video_ids, order } ] }
    """
    analyzed = [v for v in videos if v.get("analyzed")]
    if not analyzed:
        return {"phases": []}

    video_lines = []
    for v in analyzed:
        topics_str = "، ".join(v.get("topics", [])) if v.get("topics") else "—"
        video_lines.append(
            f"ID:{v['video_id']} | رقم:{v.get('position', 0) + 1} | العنوان:{v.get('title', '')} | المستوى:{v.get('level', '—')} | المواضيع:{topics_str} | يعتمد على سابق:{v.get('requires_previous', False)}"
        )

    content = "\n".join(video_lines)

    prompt = f"""أنت خبير تعليمي. لديك قائمة الفيديوهات التالية:

{content}

صمم مسار تعلم ذكياً يقسم هذه الفيديوهات إلى مراحل منطقية (من 2 إلى 4 مراحل).
أجب بـ JSON فقط بالشكل التالي:

{{
  "phases": [
    {{
      "title": "عنوان المرحلة",
      "description": "وصف مختصر للمرحلة وما ستتعلمه",
      "video_ids": ["video_id_1", "video_id_2"]
    }}
  ]
}}

ضع الفيديوهات في ترتيب منطقي للتعلم بغض النظر عن ترقيمها الأصلي."""

    try:
        response = model.generate_content(prompt)
        parsed = _safe_json(response.text.strip())
        if parsed and "phases" in parsed:
            return parsed
        return {"phases": [], "raw": response.text.strip()}
    except Exception as e:
        return {"phases": [], "error": str(e)}


# ─────────────────────────────────────────────
# Feature 4 — Chat with Playlist (Q&A)
# ─────────────────────────────────────────────

def chat_with_playlist(
    question: str,
    videos: List[Dict],
    playlist_name: str,
    chat_history: List[Dict]
) -> Dict:
    """
    Answer a user's question based on the analyzed playlist content.
    chat_history: list of {role: 'user'|'assistant', content: str}
    Returns: { answer: str, referenced_videos: [ {video_id, title, position} ] }
    """
    analyzed = [v for v in videos if v.get("analyzed")]

    # Build compact video context
    video_context = []
    for v in analyzed:
        topics_str = "، ".join(v.get("topics", [])) if v.get("topics") else "—"
        video_context.append(
            f"[فيديو {v.get('position', 0) + 1} | ID:{v['video_id']}] عنوان: {v.get('title', '')} | "
            f"مستوى: {v.get('level', '—')} | مواضيع: {topics_str} | "
            f"ملخص: {(v.get('explanation', '') or '')[:300]}"
        )

    context_str = "\n".join(video_context)

    # Build history string
    history_str = ""
    if chat_history:
        history_lines = []
        for msg in chat_history[-6:]:  # last 6 messages only
            role = "المستخدم" if msg.get("role") == "user" else "المساعد"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        history_str = "\n".join(history_lines)

    prompt = f"""أنت مساعد ذكي متخصص في Playlist YouTube باسم "{playlist_name}".
لديك المعلومات التالية عن فيديوهات هذه الـ Playlist:

{context_str}

{"سجل المحادثة السابقة:" + chr(10) + history_str if history_str else ""}

سؤال المستخدم: {question}

أجب بـ JSON فقط بالشكل التالي:
{{
  "answer": "إجابة واضحة ومفيدة بالعربية مبنية على محتوى الـ Playlist",
  "referenced_videos": [
    {{"video_id": "...", "title": "...", "position": 0}}
  ]
}}

إذا كان السؤال غير متعلق بالـ Playlist، وضح ذلك بلطف واقترح ما يمكنك مساعدته به."""

    try:
        response = model.generate_content(prompt)
        parsed = _safe_json(response.text.strip())
        if parsed and "answer" in parsed:
            return {
                "answer": parsed.get("answer", ""),
                "referenced_videos": parsed.get("referenced_videos", [])
            }
        return {"answer": response.text.strip(), "referenced_videos": []}
    except Exception as e:
        return {"answer": f"تعذر الإجابة: {str(e)}", "referenced_videos": []}


# ─────────────────────────────────────────────
# Feature 5 — Playlist Comparison
# ─────────────────────────────────────────────

def compare_playlists(
    playlist_a: Dict,   # { name, videos: List[Dict] }
    playlist_b: Dict    # { name, videos: List[Dict] }
) -> Dict:
    """
    Compare two analyzed playlists and return structured comparison.
    """
    def summarize(playlist: Dict) -> str:
        name = playlist.get("name", "—")
        videos = [v for v in playlist.get("videos", []) if v.get("analyzed")]
        topics_all = []
        levels = []
        for v in videos:
            topics_all.extend(v.get("topics", []))
            if v.get("level"):
                levels.append(v.get("level"))

        unique_topics = list(set(topics_all))[:15]
        level_summary = "، ".join(set(levels)) if levels else "—"
        return (
            f"اسم الـ Playlist: {name}\n"
            f"عدد الفيديوهات المحللة: {len(videos)}\n"
            f"المستويات: {level_summary}\n"
            f"أبرز المواضيع: {', '.join(unique_topics)}"
        )

    summary_a = summarize(playlist_a)
    summary_b = summarize(playlist_b)

    prompt = f"""أنت خبير تعليمي. قارن بين الـ Playlist التاليتين:

--- Playlist A ---
{summary_a}

--- Playlist B ---
{summary_b}

أجب بـ JSON فقط بالشكل التالي:
{{
  "criteria": [
    {{
      "name": "المستوى",
      "playlist_a": "وصف A",
      "playlist_b": "وصف B"
    }},
    {{
      "name": "التغطية",
      "playlist_a": "وصف A",
      "playlist_b": "وصف B"
    }},
    {{
      "name": "عدد الفيديوهات",
      "playlist_a": "وصف A",
      "playlist_b": "وصف B"
    }},
    {{
      "name": "المواضيع الحصرية",
      "playlist_a": "وصف A",
      "playlist_b": "وصف B"
    }},
    {{
      "name": "المناسب لـ",
      "playlist_a": "وصف A",
      "playlist_b": "وصف B"
    }}
  ],
  "recommendation": "توصية واضحة: أيهما أفضل ولماذا؟ وهل يمكن الجمع بينهما؟",
  "winner": "A أو B أو كلاهما"
}}"""

    try:
        response = model.generate_content(prompt)
        parsed = _safe_json(response.text.strip())
        if parsed and "criteria" in parsed:
            return {
                **parsed,
                "playlist_a_name": playlist_a.get("name", "Playlist A"),
                "playlist_b_name": playlist_b.get("name", "Playlist B")
            }
        return {
            "criteria": [],
            "recommendation": response.text.strip(),
            "winner": "—",
            "playlist_a_name": playlist_a.get("name", "Playlist A"),
            "playlist_b_name": playlist_b.get("name", "Playlist B")
        }
    except Exception as e:
        return {"criteria": [], "recommendation": f"تعذر المقارنة: {str(e)}", "winner": "—"}
