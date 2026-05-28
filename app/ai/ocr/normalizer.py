import re

def normalize_text(text):
    """Sanitizes raw OCR text for robust index keyword searches.
    
    Performs:
    1. Lowercase standardization.
    2. Elimination of isolated punctuation / OCR noise symbols (e.g. |, ~, _).
    3. Normalization of consecutive spaces, tabs, and linebreaks.
    4. Unique token deduplication to streamline SQLite index querying.
    """
    if not text:
        return ""

    # 1. Force lowercase
    normalized = text.lower()

    # 2. Clean consecutive whitespace, replacing tabs/newlines with single space
    normalized = re.sub(r'\s+', ' ', normalized)

    # 3. Strip leading/trailing spaces
    normalized = normalized.strip()

    # 4. Tokenize and clean noise
    raw_tokens = normalized.split(' ')
    clean_tokens = []

    for token in raw_tokens:
        # Scrub stray symbols/garbage tokens of length 1 (except common numbers or letters)
        if len(token) == 1:
            if not token.isalnum():
                continue # Skip isolated symbols like '|', '~', '_', '\'
        
        # Strip trailing/leading basic symbols (commas, periods, semicolons, brackets)
        cleaned_token = token.strip('.,;:!?|`~_-\'"()[]{}<>*')
        if cleaned_token:
            clean_tokens.append(cleaned_token)

    # 5. Eliminate duplicate tokens while preserving order
    unique_tokens = []
    seen = set()
    for token in clean_tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)

    # Return unified clean string
    return " ".join(unique_tokens)
