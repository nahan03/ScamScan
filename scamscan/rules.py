"""Rule-based red-flag checks for job ads (requirements FR-2 and FR-3).

Each rule looks for one specific warning sign and returns a Flag with a weight.
Positive signals (a company email, a website, detailed duties) reduce the score.
The result is a rule probability between 0 and 1, plus the reasons behind it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .constants import RULE_SCORE_DENOMINATOR

POSITIVE_CREDIT = 0.75  # score removed for each positive signal

FREE_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "hotmail.com",
        "outlook.com", "live.com", "msn.com", "aol.com", "icloud.com",
        "proton.me", "protonmail.com", "mail.com", "gmx.com", "yandex.com",
    }
)

# Words that make a free-email handle look like a "hiring desk" instead of a person.
GENERIC_HANDLE_WORDS = (
    "job", "hiring", "hire", "recruit", "career", "vacanc", "staff", "dubai", "uae", "gulf",
)
_HR_HANDLE_RE = re.compile(r"(?:^|[._\-\d])hr(?:$|[._\-\d])")

# Words that show an ad actually describes the job.
DETAIL_KEYWORDS = (
    "requirements", "responsibilities", "qualifications", "experience", "skills",
    "salary", "benefits", "duties", "degree", "years",
)

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+\-]+)@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)")
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)

LEGAL_SUFFIX_RE = re.compile(
    r"\b(?:llc|l\.l\.c|fz[\s-]?llc|fze|fzco|ltd|plc|gmbh|pjsc|inc|corp|corporation|holdings)\b",
    re.IGNORECASE,
)
COMPANY_LABEL_RE = re.compile(
    r"\b(?:company\s+name|employer|hiring\s+company)\s*[:\-]", re.IGNORECASE
)

FEE_PATTERNS = [
    re.compile(
        r"\b(?:registration|processing|training|medical|visa|application|admin(?:istration)?|"
        r"security|insurance|uniform|agency|booking|joining)\s+(?:fees?|charges?|deposit)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\badvance\s+(?:payment|fee)s?\b", re.IGNORECASE),
    re.compile(r"\brefundable\s+(?:deposit|fee)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:you|candidates|applicants)\b[^.\n]{0,30}\b"
        r"(?:must|need to|have to|will need to|required to)\s+(?:pay|send|transfer|deposit)\b",
        re.IGNORECASE,
    ),
]

_SEND_VERBS = r"(?:send|share|submit|provide|attach|email|whatsapp|upload|give)"

FINANCIAL_PATTERNS = [
    re.compile(
        rf"\b{_SEND_VERBS}\b[^.\n]{{0,40}}\b(?:bank\s*(?:account|details|statement)|"
        r"credit\s*card|debit\s*card|card\s*(?:number|details)|cvv|otp|iban)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:otp|cvv)\b", re.IGNORECASE),
]

ID_PATTERNS = [
    re.compile(
        rf"\b{_SEND_VERBS}\b[^.\n]{{0,40}}\b(?:passport|emirates\s*id|national\s*id)\b",
        re.IGNORECASE,
    ),
]

TOO_GOOD_PATTERNS = [
    re.compile(
        r"\bearn\s+(?:up\s+to\s+)?(?:aed|usd|\$|inr|rs\.?)?\s?[\d,]{3,}\s*(?:aed|usd|\$)?\s*"
        r"(?:per|a|/)\s*(?:day|daily|week|weekly)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bguaranteed\s+(?:income|job|salary|visa|placement|returns?)\b", re.IGNORECASE
    ),
    re.compile(r"\beasy\s+(?:money|income)\b", re.IGNORECASE),
    re.compile(r"\bno\s+interview\b", re.IGNORECASE),
    re.compile(r"\b100%\s+(?:job\s+)?(?:guarantee|guaranteed|placement)\b", re.IGNORECASE),
]

URGENCY_PATTERNS = [
    re.compile(
        r"\b(?:urgent(?:ly)?\s+(?:hiring|required|needed|vacancy|vacancies)|"
        r"apply\s+(?:now|immediately|today)|"
        r"limited\s+(?:seats|slots|vacancies|positions)|hurry|last\s+chance)\b",
        re.IGNORECASE,
    ),
]

MESSAGING_RE = re.compile(r"\b(?:whatsapp|telegram|wa\.me|t\.me)\b", re.IGNORECASE)

PAY_STATED_RE = re.compile(
    r"\b(?:aed|dhs?|usd|sar|qar|inr)\s?\d[\d,]{2,}|\b\d[\d,]{2,}\s?(?:aed|dhs?)\b",
    re.IGNORECASE,
)

# A negation word just before (or inside) a match cancels it: "no registration fee".
_NEGATION_RE = re.compile(
    r"\b(?:no|without|free of|zero|never|not|don't|dont|doesn't|doesnt)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class Flag:
    """One warning sign found in an ad."""

    code: str
    label: str
    detail: str
    weight: float
    hard: bool = False  # hard flags force a "high" risk level


@dataclass(frozen=True)
class Positive:
    """One reassuring sign found in an ad."""

    code: str
    label: str


@dataclass(frozen=True)
class RuleResult:
    flags: tuple[Flag, ...]
    positives: tuple[Positive, ...]
    raw_score: float
    rule_prob: float

    @property
    def has_hard(self) -> bool:
        return any(flag.hard for flag in self.flags)

    @property
    def codes(self) -> frozenset[str]:
        return frozenset(flag.code for flag in self.flags)


def _find(
    patterns: list[re.Pattern], text: str, negatable: bool = True
) -> re.Match | None:
    """Return the first match of any pattern.

    With negatable=True a negation word just before or inside the match cancels it
    ("no registration fee"). Patterns that contain their own "no" ("no interview")
    must use negatable=False.
    """
    for pattern in patterns:
        for match in pattern.finditer(text):
            if not negatable:
                return match
            sentence_start = re.split(r"[.!?\n]", text[: match.start()])[-1][-30:]
            if not _NEGATION_RE.search(sentence_start + " " + match.group(0)):
                return match
    return None


def _is_generic_handle(local_part: str) -> bool:
    local = local_part.lower()
    return any(word in local for word in GENERIC_HANDLE_WORDS) or bool(
        _HR_HANDLE_RE.search(local)
    )


def analyze_rules(text: str) -> RuleResult:
    """Run every rule on the ad text and return the flags, positives and score."""
    text = text or ""
    if not text.strip():
        return RuleResult((), (), 0.0, 0.0)

    lower = text.lower()
    words = len(text.split())
    emails = EMAIL_RE.findall(text)
    free = [(local, dom) for local, dom in emails if dom.lower() in FREE_EMAIL_DOMAINS]
    corporate = [(local, dom) for local, dom in emails if dom.lower() not in FREE_EMAIL_DOMAINS]
    has_url = bool(URL_RE.search(text))
    named_company = bool(LEGAL_SUFFIX_RE.search(text) or COMPANY_LABEL_RE.search(text))
    detail_hits = sum(1 for keyword in DETAIL_KEYWORDS if keyword in lower)

    flags: list[Flag] = []
    positives: list[Positive] = []

    if _find(FEE_PATTERNS, text):
        flags.append(Flag(
            "fee_request", "Asks you to pay money",
            "Real employers do not charge candidates for a job, visa, training or registration.",
            6.0, hard=True,
        ))
    if _find(FINANCIAL_PATTERNS, text):
        flags.append(Flag(
            "financial_details", "Asks for bank, card or OTP details",
            "No employer needs your bank, card or one-time-password details to review an application.",
            5.0, hard=True,
        ))
    if _find(ID_PATTERNS, text):
        flags.append(Flag(
            "id_documents", "Asks for passport or ID copies up front",
            "Some employers do ask later, but sending these before you have verified the "
            "employer is risky.",
            2.0,
        ))
    if free:
        generic = any(_is_generic_handle(local) for local, _ in free)
        flags.append(Flag(
            "free_email", "Applications go to a free personal email",
            "The contact uses a free email service"
            + (" with a generic 'hiring desk' style name" if generic else "")
            + ". Real companies normally use an email on their own domain.",
            4.0 if generic else 3.0,
        ))
    if words < 60 and detail_hits < 2:
        flags.append(Flag(
            "vague_ad", "Very little detail about the job",
            "The ad is short and does not describe duties, requirements, pay or benefits.",
            2.0,
        ))
    if not (named_company or corporate or has_url):
        flags.append(Flag(
            "no_company", "No identifiable company",
            "No company name, company email domain or website was found. Ask who the employer is.",
            1.5,
        ))
    if _find(TOO_GOOD_PATTERNS, text, negatable=False):
        flags.append(Flag(
            "too_good", "Unrealistic pay or guarantees",
            "Promises such as guaranteed income, easy money or 'no interview' are common in scams.",
            3.0,
        ))
    if _find(URGENCY_PATTERNS, text, negatable=False):
        flags.append(Flag(
            "urgency", "Pressure to act fast",
            "Urgency ('apply now', 'limited seats') discourages you from checking the employer.",
            1.5,
        ))
    if MESSAGING_RE.search(text) and not (corporate or has_url):
        flags.append(Flag(
            "messaging_only", "Contact only through a messaging app",
            "WhatsApp or Telegram alone makes the employer hard to verify.",
            1.0,
        ))
    if not emails and not has_url:
        flags.append(Flag(
            "no_verifiable_contact", "No verifiable contact",
            "There is no email or website you could use to check the employer.",
            2.0,
        ))

    if corporate:
        positives.append(Positive("corporate_email", "Applications go to a company email domain"))
    if has_url:
        positives.append(Positive("website", "Includes a website or link"))
    if named_company:
        positives.append(Positive("named_company", "Names the employer"))
    if words >= 80 and detail_hits >= 3:
        positives.append(Positive("detailed", "Describes duties, requirements or benefits"))
    if PAY_STATED_RE.search(text):
        positives.append(Positive("pay_stated", "States the pay"))

    flags.sort(key=lambda flag: flag.weight, reverse=True)
    raw = max(0.0, sum(flag.weight for flag in flags) - POSITIVE_CREDIT * len(positives))
    rule_prob = min(1.0, raw / RULE_SCORE_DENOMINATOR)
    return RuleResult(tuple(flags), tuple(positives), round(raw, 2), round(rule_prob, 3))
