"""Live question -> draft -> independent review -> refined response.

Separate from cross_verify.py, preserving the original CLI project.
"""
import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

OPENAI_MODEL = os.getenv('CROSSVERIFY_OPENAI_MODEL', 'gpt-4o')
ANTHROPIC_MODEL = os.getenv('CROSSVERIFY_ANTHROPIC_MODEL', 'claude-sonnet-5')


@dataclass
class AnswerResult:
    initial: str
    feedback: str
    refined: str
    uncertainties: str
    reviewed: bool


def _openai_text(client, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_completion_tokens=1100,
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise RuntimeError('OpenAI returned an empty answer.')
    return content.strip()


def generate_answer(question: str) -> AnswerResult:
    """Use 3 model calls; do not execute side effects or assert factual verification."""
    if not question.strip():
        raise ValueError('Enter a question.')
    if len(question) > 6000:
        raise ValueError('Question too long (maximum 6,000 characters).')
    if not os.getenv('OPENAI_API_KEY') or not os.getenv('ANTHROPIC_API_KEY'):
        raise RuntimeError('Missing OPENAI_API_KEY or ANTHROPIC_API_KEY in .env.')

    # Import on demand so demo/UI can start without credentials.
    from openai import OpenAI
    from anthropic import Anthropic

    openai_client = OpenAI(timeout=45.0, max_retries=1)
    claude_client = Anthropic(timeout=60.0, max_retries=1)

    initial = _openai_text(
        openai_client,
        'Give a useful, well-structured answer. Be honest about ambiguous questions and uncertainty. '
        'Do not fabricate citations, evidence, or facts. Do not claim you looked things up.',
        question,
    )

    reviewer_message = claude_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=(
            'You are a critical answer reviewer, not an approval gate. '
            'Evaluate accuracy to the extent possible WITHOUT browsing, completeness, '
            'unwarranted confidence, ambiguity, and usefulness. Suggest specific corrections. '
            'If facts need external verification, state this explicitly. '
            'Return plain text with headings: Gaps, Improvements, Unverified claims. '
            'Do not claim the answer is verified merely because you agree.'
        ),
        messages=[{"role": "user", "content": f"QUESTION:\n{question}\n\nDRAFT ANSWER:\n{initial}"}],
    )
    feedback = '\n'.join(block.text for block in reviewer_message.content if getattr(block, 'type', '') == 'text').strip()
    if not feedback:
        raise RuntimeError(
            f'Claude returned no text feedback (stop_reason={reviewer_message.stop_reason}, '
            f'content_types={[block.type for block in reviewer_message.content]}). '
            'This can happen when the response exhausts its output-token budget before producing text.'
        )

    refined = _openai_text(
        openai_client,
        'Refine the initial answer using critical feedback. Directly answer the user. '
        'Correct mistakes and ambiguities. Explicitly acknowledge unresolved uncertainty. '
        'Do NOT present the reviewer as factual proof or invent citations. '
        'Do not talk about the approval workflow. Return only the final user-facing answer.',
        f"QUESTION:\n{question}\n\nINITIAL ANSWER:\n{initial}\n\nINDEPENDENT REVIEW:\n{feedback}",
    )
    return AnswerResult(
        initial=initial,
        feedback=feedback,
        refined=refined,
        uncertainties='Model-only review; independent source verification was not performed.',
        reviewed=True,
    )
