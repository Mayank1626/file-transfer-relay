import re
import json

# Compile regexes for speed
SQL_KEYWORDS = re.compile(
    r'(?i)^\s*(?:select|insert|update|delete|create\s+table|alter\s+table|drop\s+table|grant|revoke|truncate|replace)\b'
)
URL_PATTERN = re.compile(
    r'^(?:https?|ftp)://[^\s/$.?#].[^\s]*$', re.IGNORECASE
)
COMMAND_KEYWORDS = re.compile(
    r'^\s*(?:npm|yarn|pnpm|pip|pip3|poetry|uv|docker|docker-compose|git|cargo|mvn|gradle|python|python3|node|curl|wget|sudo|apt-get|brew|kubectl|systemctl|ipconfig|ping|ssh|scp)\b'
)

# Common programming syntax rules
CODE_INDICATORS = [
    re.compile(r'\b(?:def|class|const|let|var|function|import|from|require|package|public|private|protected|struct|fn|impl|func|lambda|enum)\b'),
    re.compile(r'[{};()\[\]]'), # Common syntax symbols
    re.compile(r'(?:=>|==|!=|!==|===|\+=|-=|\*=|\/=|&&|\|\|)'), # Operators
]

def classify_content(text):
    """Detects content type of a text block using fast structural and keyword heuristics."""
    if not text:
        return 'TEXT'

    stripped = text.strip()
    
    # 1. URL Check
    if URL_PATTERN.match(stripped):
        return 'URL'

    # 2. JSON Check
    if (stripped.startswith('{') and stripped.endswith('}')) or (stripped.startswith('[') and stripped.endswith(']')):
        try:
            json.loads(stripped)
            return 'JSON'
        except ValueError:
            pass

    # 3. SQL Check
    if SQL_KEYWORDS.search(stripped):
        return 'SQL'

    # 4. Command check (CLI/Terminal)
    if COMMAND_KEYWORDS.search(stripped) or stripped.startswith('$ ') or stripped.startswith('> '):
        return 'COMMAND'

    # 5. Code block check
    lines = stripped.splitlines()
    code_signals = 0
    
    for indicator in CODE_INDICATORS:
        if indicator.search(stripped):
            code_signals += 1

    if code_signals >= 2 and len(lines) > 1:
        return 'CODE'
        
    if code_signals >= 1 and (
        'def ' in stripped or 
        'class ' in stripped or 
        'const ' in stripped or 
        'let ' in stripped or 
        'import ' in stripped or 
        'console.log' in stripped or 
        'print(' in stripped
    ):
        return 'CODE'

    return 'TEXT'
