"""
Cross-Model Verification Assistant
------------------------------------
Enterprise pattern: two LLMs (Claude + OpenAI) work on one business command
together. One model DRAFTS a response/action. The other model VERIFIES it
before anything gets implemented (sent, saved, executed). This is the same
"LLM-as-judge" guardrail pattern used in production AI agent systems to
reduce hallucination and error risk before an action is taken autonomously
on behalf of a business.

Flow:
  1. You give a business command
     (e.g. "draft a follow-up email to the vendor about the delayed shipment").
  2. DRAFTER model produces a first response.
  3. VERIFIER model reviews it for accuracy, tone, missing info, and risk.
  4. If APPROVED -> the response is "implemented". Today that means saving
     it to a file. In production, swap the implement() function body for a
     real action: send an email (Gmail/Graph API), post to Slack, update a
     CRM record (Salesforce/HubSpot API), etc.
  5. If NOT APPROVED -> the verifier's feedback goes back to the drafter for
     one revision. If it still fails, nothing is implemented — it's flagged
     for a human to look at instead of silently failing or guessing.

Setup:
  pip install -r requirements.txt --break-system-packages
  cp .env.example .env      # then paste in your real API keys
  python cross_verify.py "draft a follow-up email to the vendor about the delayed shipment"
"""

import os
import sys
import json
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import anthropic
from openai import OpenAI

CLAUDE_MODEL = "claude-sonnet-5"
OPENAI_MODEL = "gpt-4o"

claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_claude(prompt: str) -> str:
    """Send a prompt to Claude and return its text response.

    Claude's response can include multiple content blocks (e.g. a
    "thinking" block followed by the actual text block), so we scan for
    the first block that has a .text attribute instead of assuming
    content[0] is always the text.
    """
    response = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    raise ValueError("No text block found in Claude's response")


def ask_openai(prompt: str) -> str:
    """Send a prompt to OpenAI and return its text response."""
    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def draft_response(command: str, drafter: str = "openai") -> str:
    """Step 1: one model drafts a response to the business command."""
    prompt = (
        "You are a business assistant. Carry out the following command and "
        "produce the actual deliverable (e.g. the email text, the summary, "
        "the plan) — not a description of what you would do.\n\n"
        f"Command: {command}"
    )
    return ask_openai(prompt) if drafter == "openai" else ask_claude(prompt)


def verify_response(command: str, draft: str, verifier: str = "claude") -> dict:
    """Step 2: the other model reviews the draft and returns a verdict."""
    review_prompt = f"""You are a strict reviewer for enterprise business output.

Original command: {command}

Draft response to review:
---
{draft}
---

Check for: factual accuracy, missing information, wrong tone, risk (e.g.
commitments that shouldn't be made without approval), and completeness.

Respond ONLY with valid JSON in this exact shape, no other text:
{{"approved": true or false, "issues": ["issue 1", "issue 2"], "feedback": "short summary"}}
"""
    raw = ask_claude(review_prompt) if verifier == "claude" else ask_openai(review_prompt)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"approved": False, "issues": ["Could not parse verifier output"], "feedback": raw}


def implement(command: str, draft: str) -> str:
    """
    Step 3: if approved, 'implement' the action.
    Today this saves the approved output to a file. In a real deployment,
    replace this function body with: send an email, post to Slack, create
    a CRM record, trigger an n8n webhook, etc.
    """
    os.makedirs("approved_outputs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"approved_outputs/{timestamp}.txt"
    with open(filepath, "w") as f:
        f.write(f"COMMAND: {command}\n\nAPPROVED OUTPUT:\n{draft}\n")
    return filepath


def run(command: str, drafter: str = "openai", verifier: str = "claude", max_revisions: int = 1):
    print(f"\n[1/3] Drafting with {drafter}...")
    draft = draft_response(command, drafter)
    print(f"\nDraft:\n{draft}\n")

    for attempt in range(max_revisions + 1):
        print(f"[2/3] Verifying with {verifier} (attempt {attempt + 1})...")
        verdict = verify_response(command, draft, verifier)
        print(f"Verdict: {json.dumps(verdict, indent=2)}\n")

        if verdict.get("approved"):
            path = implement(command, draft)
            print(f"[3/3] Approved. Implemented -> saved to {path}")
            return

        if attempt < max_revisions:
            print("Not approved. Asking drafter to revise...\n")
            revise_prompt = (
                f"Revise this response based on feedback.\n\nOriginal command: {command}\n\n"
                f"Previous draft: {draft}\n\nReviewer feedback: {verdict.get('feedback')}\n"
                f"Issues: {verdict.get('issues')}\n\nProduce the corrected deliverable only."
            )
            draft = ask_openai(revise_prompt) if drafter == "openai" else ask_claude(revise_prompt)
            print(f"Revised draft:\n{draft}\n")

    print("[3/3] Not approved after revisions. Flagged for human review — nothing was implemented.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_command = " ".join(sys.argv[1:])
    else:
        user_command = input("Enter a business command: ")
    run(user_command)
