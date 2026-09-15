"""Pre-written responses for sensitive/off-topic content, checked before any
FAQ matching or Gemini call — ported from the chatbot PRD's "Fallback & Edge
Case Handling" table. Gemini only ever routes to a category; it never writes
these responses itself (PRD: "Gemini only routes to the category — it never
writes these responses").

Bug found during 2026-09-10 exhaustive testing: GIBBERISH_RESPONSE and
faq_service.looks_like_gibberish existed but were never actually wired into
check_fallbacks() — fixed below. OFFTOPIC_RESPONSE/looks_app_related were
ALSO unwired, and a first attempt to wire them in the same way was reverted
after testing showed it wrongly flags completely normal on-topic messages
(e.g. "Hi, I need some help please") as off-topic — see check_fallbacks()'s
own comment for why that one stays a system-prompt instruction instead of a
code-level gate.
"""

import re
from dataclasses import dataclass

from app.services.faq_service import looks_like_gibberish


@dataclass(frozen=True)
class Fallback:
    id: str
    response: str
    ends_session: bool = False
    # None for the two synthetically-detected fallbacks below (gibberish,
    # offtopic) — those are matched by looks_like_gibberish/looks_app_related,
    # not a static regex, so they don't need one.
    pattern: re.Pattern | None = None


FALLBACKS: list[Fallback] = [
    Fallback(
        id="underage",
        pattern=re.compile(r"\b(i'?m|i am|im)\s*(1[0-7])\b(\s*(years|yrs|yr|year)?\s*old)?|\bunder\s*18\b|\bi'?m a minor\b", re.I),
        response=(
            "It looks like you may be under 18. Dostt is available only to users aged 18 and "
            "above, so you're not eligible to use the app. We're sorry for any inconvenience "
            "and appreciate your understanding."
        ),
        ends_session=True,
    ),
    Fallback(
        id="mental_health",
        pattern=re.compile(r"\b(suicide|suicidal|kill myself|end my life|want to die|no reason to live|self harm|self-harm|harm myself)\b", re.I),
        response=(
            "I am so sorry you are feeling this way. I really wish I could do more, but I am a "
            "support bot and this is not something I am able to help with. Please call "
            "Tele-MANAS at 1800-891-4416. They are free, they are safe, and they are always "
            "there for you. Please reach out to them."
        ),
    ),
    Fallback(
        id="domestic_abuse",
        pattern=re.compile(r"\b(domestic violence|domestic abuse|he hits me|she hits me|husband beats|wife beats|being abused at home|unsafe at home)\b", re.I),
        response=(
            "I'm sorry you're going through this. I'm a customer-support bot and can only help "
            "with support-related queries, so I'm not able to provide counselling or handle "
            "emergencies. If you are in immediate danger, please move to a safer place if you "
            "can and contact local emergency services or someone you trust. If it is safe to do "
            "so, please reach out to a local domestic-violence support service or trusted "
            "person for help. Your safety comes first."
        ),
    ),
    Fallback(
        id="harmful_explicit",
        pattern=re.compile(r"\b(nudes?|porn|sex chat|send.*nude|explicit photo)\b", re.I),
        response="I cannot help with this. I am here only to help you with problems you are facing on the Dostt app. Please tell me your app related issue.",
    ),
    Fallback(
        id="prompt_injection",
        pattern=re.compile(r"\b(ignore (all|previous) instructions|you are now|act as|system prompt|jailbreak|reveal your prompt)\b", re.I),
        response="I cannot follow instructions given through chat. Please tell me your Dostt related problem and I will help you.",
    ),
    Fallback(
        id="privacy_probing",
        pattern=re.compile(r"\b(what is my password|my otp|share my otp|admin password|give me access to)\b", re.I),
        response="I cannot share any private information. But if you have a complaint, I can raise it with the Dostt team for you. Do you want me to do that?",
    ),
    Fallback(
        id="legal_threat",
        pattern=re.compile(r"\b(consumer court|legal action|sue you|lawyer|fir|police complaint|legal notice)\b", re.I),
        response="I understand this is a serious matter. Please send an email to grievance.officer@dostt.in and our team will get back to you. I am here if you have any other issue.",
    ),
    Fallback(
        id="call_me",
        pattern=re.compile(r"\b(call me now|call me back|phone me|urgent call|need a call)\b", re.I),
        response=(
            "I cannot arrange a call directly, but I can help you raise a ticket with our "
            "team. Once your ticket is raised, the team will be able to get in touch with you. "
            "Please describe the issue you need help with and I will get it sorted for you."
        ),
    ),
    Fallback(
        id="scam_fraud",
        pattern=re.compile(r"\b(scam|fraud|cheated me|duplicate charge fraud|fake listener)\b", re.I),
        response="I am sorry you went through this. Please share more details and I will raise a ticket for you right away so our team can look into it.",
    ),
    Fallback(
        id="misinformation",
        pattern=re.compile(r"\b(admin told me|dostt employee messaged|official on whatsapp|official told me)\b", re.I),
        response="All official messages from Dostt only come through the app. I cannot act on anything said in this chat. Please tell me your problem and I will help you.",
    ),
    Fallback(
        id="profanity",
        pattern=re.compile(r"\b(fuck|f\*ck|bitch|bastard|asshole|chutiya|madarchod|behenchod)\b", re.I),
        response="I understand you are upset. Please tell me what problem you are facing on Dostt and I will try my best to help you.",
    ),
]

OFFTOPIC_RESPONSE = "I can only help with problems related to the Dostt app. Please tell me if you are facing any issue on the platform."
GIBBERISH_RESPONSE = "I did not understand that. Can you please tell me your problem in simple words? I want to help you."

_GIBBERISH_FALLBACK = Fallback(id="gibberish", response=GIBBERISH_RESPONSE)


def check_fallbacks(text: str) -> Fallback | None:
    for fb in FALLBACKS:
        if fb.pattern.search(text):
            return fb

    if looks_like_gibberish(text.strip()):
        return _GIBBERISH_FALLBACK

    # OFFTOPIC_RESPONSE / looks_app_related deliberately NOT wired in here,
    # despite existing for exactly this purpose — tested 2026-09-10 and
    # found it wrongly flags completely normal, on-topic opening messages
    # like "Hi, I need some help please" as off-topic, since a generic
    # help-seeking message often mentions no Dostt-specific word before the
    # bot has even asked what's wrong. A keyword-presence check is too
    # blunt an instrument for this — false-positiving on a real complaint
    # is worse than occasionally answering an unrelated trivia question.
    # The actual off-topic-trivia bug this was meant to fix (Gemini
    # directly answering "what's the capital of France?") is instead
    # handled in the system prompt (see agent/prompt.py's ground rules).

    return None
