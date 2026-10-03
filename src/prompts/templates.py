"""
Prompt Templates Module.
Centralizes all AI prompt templates used across the application to ensure consistency,
strict JSON formatting, and clear documentation.
"""

# Unified analysis prompt used by the GeminiUnifiedAnalyzer.
# It evaluates sentiment, categorization, and marketing relevance in a single LLM call.
UNIFIED_ANALYSIS_PROMPT = """
You are an expert AI community analyst for a tech and development community platform.
Analyze the following community message and evaluate it across three specific domains: Sentiment, Categorization, and Marketing Relevance.

Input Message:
- Author: {author}
- Channel: {channel}
- Content: "{text}"

You MUST respond strictly with a valid JSON object matching the following schema, without any markdown formatting (do not use ```json or ```):
{
  "sentiment": {
    "type": "positivo" | "negativo" | "neutral",
    "score": <float between 0.0 and 1.0>,
    "reasoning": "<short explanation in Spanish>"
  },
  "categorization": {
    "category": "duda_tecnica" | "testimonio" | "feedback" | "pregunta_general" | "discusion" | "otro",
    "topics": ["<topic1>", "<topic2>"],
    "entities": ["<entity1>", "<entity2>"]
  },
  "relevance": {
    "score": <float between 0.0 and 1.0>,
    "is_marketing_worthy": <true if score >= 0.6 else false>
  }
}

Guidelines for evaluation:
- Sentiment: Detect if the tone is positive, negative, or neutral. Provide a normalized score.
- Category: Must be exactly one of the 6 allowed categories (duda_tecnica, testimonio, feedback, pregunta_general, discusion, otro).
- Relevance: Rate from 0.0 to 1.0. Set is_marketing_worthy to true if the message contains a concrete success story, career milestone, or high-value community insight (score >= 0.6).
"""
