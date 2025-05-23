
import requests

from airless.core.hook import LLMHook
from airless.core.utils import get_config


class GeminiApiHook(LLMHook):
    def __init__(self) -> None:
        super().__init__()
        self.api_key = get_config("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def generate_content(self, model: str, prompt: str, **kwargs) -> dict:
        """Generates content using the Gemini API via a POST request.

        Args:
            model: The name of the Gemini model to use.
            prompt: The text prompt for generation.
            **kwargs: Additional parameters to include in the request payload,
                      such as systemInstruction or generationConfig.

        Returns:
            The full JSON response from the Gemini API as a dictionary.
        """
        url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        payload.update(kwargs)

        response = requests.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    def generate_content_with_pdf(self, model: str, prompt: str, pdf_files: list[str], **kwargs) -> dict:
        """Generates content using the Gemini API with PDF context via a POST request.

        Args:
            model: The name of the Gemini model to use (e.g., 'gemini-pro-vision').
            prompt: The text prompt for generation.
            pdf_files: A list of base64 encoded strings, each representing a PDF file.

        Returns:
            The full JSON response from the Gemini API as a dictionary.
        """
        url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"

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
        payload.update(kwargs)

        response = requests.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    def extract_text_from_response(self, response_json: dict) -> str:
        """Extracts text content from a Gemini API JSON response.

        Args:
            response_json: The JSON response from the Gemini API as a dictionary.

        Returns:
            The extracted text content if found, otherwise an empty string.
        """
        try:
            if 'promptFeedback' in response_json:
                block_reason = response_json.get('promptFeedback', {}).get('blockReason')
                if block_reason:
                    raise ValueError(f"Prompt was blocked. Reason: {block_reason}")

            candidates = response_json.get('candidates')
            if not candidates or not isinstance(candidates, list) or not candidates[0]:
                raise ValueError("No candidates found in response or invalid format.")

            content = candidates[0].get('content')
            if not content or not isinstance(content, dict):
                raise ValueError("No content found in candidate or invalid format.")

            parts = content.get('parts')
            if not parts or not isinstance(parts, list) or not parts[0]:
                raise ValueError("No parts found in content or invalid format.")

            text = parts[0].get('text')
            if text is None:
                raise ValueError("'text' key found but value is None.")
            return str(text)

        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Error extracting text from response: {e} - Response: {response_json}")
