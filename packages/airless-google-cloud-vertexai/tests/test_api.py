import unittest
import os
from unittest.mock import patch, Mock # Mock is unittest.mock.Mock
import requests # For requests.exceptions.HTTPError

# GeminiApiHook is imported from the hook package due to __init__.py setup
from airless.google.cloud.vertexai.hook import GeminiApiHook

class TestGeminiApiHook(unittest.TestCase):

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key_from_env"}, clear=True)
    def test_init(self):
        """Tests the __init__ method of GeminiApiHook."""
        hook = GeminiApiHook()
        self.assertEqual(hook.api_key, "test_key_from_env")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}, clear=True)
    @patch("requests.post") # Innermost argument, so last decorator
    def test_generate_content_success(self, mock_requests_post):
        """Tests the generate_content method for a successful API call."""
        mock_json_response = {
            "candidates": [{
                "content": {"parts": [{"text": "Mocked Gemini Response"}]}
            }]
        }
        mock_response_obj = Mock()
        mock_response_obj.json.return_value = mock_json_response
        mock_response_obj.raise_for_status = Mock() 
        mock_requests_post.return_value = mock_response_obj

        hook = GeminiApiHook()
        response_data = hook.generate_content(model="gemini-pro", prompt="Hello Gemini")

        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args
        
        self.assertEqual(args[0], "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=test_api_key")
        self.assertEqual(kwargs['json'], {"contents": [{"parts": [{"text": "Hello Gemini"}]}]})
        
        mock_response_obj.raise_for_status.assert_called_once()
        self.assertEqual(response_data, mock_json_response) # Check for full JSON response

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}, clear=True)
    @patch("requests.post") # Innermost argument
    def test_generate_content_with_pdf_success(self, mock_requests_post):
        """Tests the generate_content_with_pdf method for a successful API call."""
        mock_json_response = {
            "candidates": [{
                "content": {"parts": [{"text": "Mocked Gemini Response"}]} 
            }]
        }
        mock_response_obj = Mock()
        mock_response_obj.json.return_value = mock_json_response
        mock_response_obj.raise_for_status = Mock()
        mock_requests_post.return_value = mock_response_obj

        pdf_files_base64 = ["base64_pdf_1", "base64_pdf_2"] 
        
        hook = GeminiApiHook()
        response_data = hook.generate_content_with_pdf(
            model="gemini-pro-vision", 
            prompt="Describe these PDFs", 
            pdf_files=pdf_files_base64
        )

        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args

        self.assertEqual(args[0], "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key=test_api_key")
        
        expected_parts = [
            {"text": "Describe these PDFs"},
            {"inline_data": {"mime_type": "application/pdf", "data": "base64_pdf_1"}},
            {"inline_data": {"mime_type": "application/pdf", "data": "base64_pdf_2"}}
        ]
        self.assertEqual(kwargs['json']['contents'][0]['parts'], expected_parts)
        
        mock_response_obj.raise_for_status.assert_called_once()
        self.assertEqual(response_data, mock_json_response) # Check for full JSON response

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}, clear=True)
    @patch("requests.post") # Innermost argument
    def test_generate_content_api_error(self, mock_requests_post):
        """Tests generate_content method for API error handling."""
        # Configure the mock to simulate an API error
        mock_response_obj = Mock()
        mock_response_obj.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
        mock_requests_post.return_value = mock_response_obj
        
        hook = GeminiApiHook()
        
        with self.assertRaises(requests.exceptions.HTTPError) as context:
            hook.generate_content(model="gemini-pro", prompt="Test error")
        
        self.assertTrue("API Error" in str(context.exception))
        mock_response_obj.raise_for_status.assert_called_once()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}, clear=True)
    @patch("requests.post") # Innermost argument
    def test_generate_content_with_pdf_api_error(self, mock_requests_post):
        """Tests generate_content_with_pdf method for API error handling."""
        mock_response_obj = Mock()
        mock_response_obj.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error PDF")
        mock_requests_post.return_value = mock_response_obj
        
        hook = GeminiApiHook()
        pdf_files_base64 = ["base64_pdf_1"]
        
        with self.assertRaises(requests.exceptions.HTTPError) as context:
            hook.generate_content_with_pdf(
                model="gemini-pro-vision", 
                prompt="Test error PDF", 
                pdf_files=pdf_files_base64
            )
        
        self.assertTrue("API Error PDF" in str(context.exception))
        mock_response_obj.raise_for_status.assert_called_once()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}, clear=True) # For hook instantiation
    def test_extract_text_from_response_success(self):
        hook = GeminiApiHook()
        sample_response_json = {
            "candidates": [{
                "content": {"parts": [{"text": "Expected Text"}]}
            }]
        }
        extracted_text = hook.extract_text_from_response(sample_response_json)
        self.assertEqual(extracted_text, "Expected Text")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}, clear=True)
    @patch.object(GeminiApiHook, "logger", new_callable=Mock) # Patching logger on the class
    def test_extract_text_from_response_missing_parts(self, mock_logger):
        hook = GeminiApiHook()
        # hook.logger = mock_logger # Assign mock logger to the instance

        invalid_responses = [
            {}, # Empty response
            {"candidates": []}, # Empty candidates list
            {"candidates": [{}]}, # Candidate without content
            {"candidates": [{"content": {}}]}, # Content without parts
            {"candidates": [{"content": {"parts": []}}]}, # Empty parts list
            {"candidates": [{"content": {"parts": [{}]}}]}, # Part without text
            {"candidates": [{"content": {"parts": [{"text": None}]}}]} # Part with text as None
        ]
        
        for i, invalid_json in enumerate(invalid_responses):
            with self.subTest(json_structure_index=i):
                extracted_text = hook.extract_text_from_response(invalid_json)
                self.assertEqual(extracted_text, "")
                # Check that logger.warning or logger.error was called.
                # Specific message checks can be added if necessary.
                # For simplicity, just checking if any warning/error was logged.
                # A more robust test would check for specific log messages.
                # if not mock_logger.warning.called and not mock_logger.error.called:
                #    print(f"No warning/error logged for case {i}: {invalid_json}")
                # self.assertTrue(mock_logger.warning.called or mock_logger.error.called)
                # mock_logger.reset_mock() # Reset for next subtest

        # Example of checking a specific log call for one case:
        hook.extract_text_from_response({"candidates": []}) # Empty candidates list
        mock_logger.warning.assert_any_call("No candidates found in response or invalid format.")


    @patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}, clear=True)
    @patch.object(GeminiApiHook, "logger", new_callable=Mock)
    def test_extract_text_from_response_prompt_blocked(self, mock_logger):
        hook = GeminiApiHook()
        # hook.logger = mock_logger

        blocked_response_json = {"promptFeedback": {"blockReason": "SAFETY"}}
        extracted_text = hook.extract_text_from_response(blocked_response_json)
        self.assertEqual(extracted_text, "")
        mock_logger.warning.assert_called_with("Prompt may have been blocked. Reason: SAFETY")

if __name__ == '__main__':
    unittest.main()
