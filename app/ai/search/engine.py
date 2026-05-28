from app.ai.database.repository import AIMemoryRepository

class AISearchEngine:
    """Governs search keyword logic, result formats, and structural weighting placeholders."""

    @staticmethod
    def search(query, limit=10, offset=0):
        """Searches indexed screenshots using tokenized matching and recency sorting.
        
        Returns a detailed formatted dictionary list of matches.
        """
        # Cleanup query text inputs
        query = query.strip() if query else ""

        # Retrieve direct matching items from SQLite Repository
        raw_results = AIMemoryRepository.search_screenshots(query, limit, offset)

        formatted_results = []
        for row in raw_results:
            ocr_status = row.get('ocr_status', 'METADATA_ONLY')
            ocr_text = row.get('ocr_text', '')

            # Format visual details
            formatted_results.append({
                'id': row['id'],
                'filepath': row['filepath'],
                'filename': row['filename'],
                'filesize': row['filesize'],
                'width': row['width'],
                'height': row['height'],
                'folder': row['folder'],
                'created_at': row['created_at'],
                'ocr_status': ocr_status,
                'ocr_text': ocr_text,
                'highlights': AISearchEngine._generate_highlights(ocr_text, query)
            })

        return formatted_results

    @staticmethod
    def _generate_highlights(text, query):
        """Lightweight visual snippet extractor highlighting query word matches."""
        if not text or not query:
            return ""

        words = [w.lower().strip() for w in query.split() if w.strip()]
        if not words:
            return ""

        # Look for occurrences of query tokens and extract a window of text
        lower_text = text.lower()
        snippet_len = 120
        
        for word in words:
            idx = lower_text.find(word)
            if idx != -1:
                start = max(0, idx - 40)
                end = min(len(text), idx + snippet_len)
                snippet = text[start:end]
                
                # Prepend/append ellipsis if snippet is clipped
                prefix = "... " if start > 0 else ""
                suffix = " ..." if end < len(text) else ""
                return f"{prefix}{snippet}{suffix}"

        # Return start of OCR text if no specific word matches
        return text[:snippet_len] + (" ..." if len(text) > snippet_len else "")

    @staticmethod
    def semantic_rerank_placeholder(results, query):
        """Prepared interface placeholder for future cosine-similarity vector embeddings reranking."""
        # Unused in current Phase, reserved for future semantic extensions
        return results

    @staticmethod
    def fuzzy_match_placeholder(token):
        """Prepared interface placeholder for typo-tolerance Levenshtein distance calculations."""
        # Unused in current Phase, reserved for future token expansion
        return token
