import os
from airless.core.hook import LLMHook

class GeminiApiHook(LLMHook):
    def __init__(self) -> None:
        super().__init__()
        self.api_key = os.getenv("GEMINI_API_KEY")

    def generate_content(self, model: str, prompt: str) -> dict:
        """Generates content using the Gemini API via a POST request.

        Args:
            model: The name of the Gemini model to use.
            prompt: The text prompt for generation.

        Returns:
            The full JSON response from the Gemini API as a dictionary.
        """
        import requests # Import requests inside the method as per original instruction, or at module level
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        response = requests.post(url, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        response_json = response.json()
        return response_json

    def extract_text_from_response(self, response_json: dict) -> str:
        """Extracts text content from a Gemini API JSON response.

        Args:
            response_json: The JSON response from the Gemini API as a dictionary.

        Returns:
            The extracted text content if found, otherwise an empty string.
        """
        try:
            # Check for 'promptFeedback' which might indicate a blocked prompt
            if 'promptFeedback' in response_json:
                block_reason = response_json.get('promptFeedback', {}).get('blockReason')
                if block_reason:
                    self.logger.warning(f"Prompt may have been blocked. Reason: {block_reason}")
                    # Depending on desired behavior, could return a specific message or empty string
                    return "" 
            
            # Ensure candidates, content, and parts are present and valid
            candidates = response_json.get('candidates')
            if not candidates or not isinstance(candidates, list) or not candidates[0]:
                self.logger.warning("No candidates found in response or invalid format.")
                return ""
            
            content = candidates[0].get('content')
            if not content or not isinstance(content, dict):
                self.logger.warning("No content found in candidate or invalid format.")
                return ""
                
            parts = content.get('parts')
            if not parts or not isinstance(parts, list) or not parts[0]:
                self.logger.warning("No parts found in content or invalid format.")
                return ""
            
            text = parts[0].get('text')
            if text is None: # Explicitly check for None if 'text' key might exist with null value
                 self.logger.warning("'text' key found but value is None.")
                 return ""
            return str(text) # Ensure it's a string
        except (KeyError, IndexError, TypeError) as e:
            self.logger.error(f"Error extracting text from response: {e} - Response: {response_json}")
            return ""

    def generate_content_with_pdf(self, model: str, prompt: str, pdf_files: list[str]) -> dict:
        """Generates content using the Gemini API with PDF context via a POST request.

        Args:
            model: The name of the Gemini model to use (e.g., 'gemini-pro-vision').
            prompt: The text prompt for generation.
            pdf_files: A list of base64 encoded strings, each representing a PDF file.

        Returns:
            The full JSON response from the Gemini API as a dictionary.
        """
        import requests # Ensure requests is imported; ideally at module level
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        api_parts = []
        api_parts.append({"text": prompt})

        for pdf_base64 in pdf_files:
            api_parts.append({
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": pdf_base64
                }
            })
            
        payload = {
            "contents": [{"parts": api_parts}]
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        response_json = response.json()
        return response_json
