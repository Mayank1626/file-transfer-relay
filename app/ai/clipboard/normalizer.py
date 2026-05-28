import re

# Size limit: 20KB (20,480 characters)
MAX_CONTENT_LENGTH = 20480

# Sensitive patterns
JWT_PATTERN = re.compile(r'\beyJ[A-Za-z0-9_-]{2,}\.[A-Za-z0-9_-]{2,}\.[A-Za-z0-9_-]{2,}\b')
CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[\s -]*?){13,16}\b')
SENSITIVE_PARAMS_PATTERN = re.compile(
    r'(?i)\b(?:password|passwd|secret|api_key|apikey|private_key|token|auth_token|client_secret)\s*[:=\s]\s*[^\s]{6,}\b'
)
# Matches OTP / Verification codes: standalone 6-digit numbers or labeled 4-8 digit codes
OTP_STANDALONE = re.compile(r'\b\d{6}\b')
OTP_LABELED = re.compile(r'(?i)\b(?:otp|mfa|verification|auth[-_]?code|passcode|code)\b.*?\b\d{4,8}\b')

def is_sensitive(text):
    """Scans the text for private data signatures (JWTs, credit cards, OTPs, credentials)."""
    if not text:
        return False

    # Check JWT
    if JWT_PATTERN.search(text):
        return True

    # Check Credit Cards (only if digits look like a card check)
    cc_match = CREDIT_CARD_PATTERN.search(text)
    if cc_match:
        # Strip spaces and dashes
        digits = re.sub(r'[\s-]', '', cc_match.group(0))
        if len(digits) in [13, 15, 16]:
            return True

    # Check password/secrets patterns
    if SENSITIVE_PARAMS_PATTERN.search(text):
        return True

    # Check OTP/Verification patterns
    if OTP_STANDALONE.search(text) or OTP_LABELED.search(text):
        return True

    return False

def normalize_clipboard_text(text):
    """Sanitizes text, compacts spaces, enforces 20KB limit, and filters privacy leaks."""
    if not text:
        return ""

    # 1. Enforce max character limit (20KB)
    if len(text) > MAX_CONTENT_LENGTH:
        text = text[:MAX_CONTENT_LENGTH] + " [truncated]"

    # 2. Check privacy guard filters. If any sensitive patterns are matched, discard completely.
    if is_sensitive(text):
        return ""

    # 3. Text whitespace normalization (compaction)
    lines = []
    for line in text.splitlines():
        line_clean = " ".join(line.split())
        if line_clean:
            lines.append(line_clean)
            
    return "\n".join(lines)
