
from typing import Any

from airless.core.utils import get_config
from airless.core.hook import LLMHook

import vertexai
from vertexai.generative_models import GenerativeModel


class GenerativeModelHook(LLMHook):
    """Hook for interacting with Vertex AI Generative Models."""

    def __init__(self, model_name: str, **kwargs: Any) -> None:
        """Initializes the GenerativeModelHook.

        Args:
            model_name (str): The name of the model to use.
            **kwargs (Any): Additional arguments for model initialization.
        """
        super().__init__()
        vertexai.init(project=get_config('GCP_PROJECT'), location=get_config('GCP_REGION'))
        self.model = GenerativeModel(model_name, **kwargs)

    def generate_completion(self, content: str, **kwargs: Any) -> Any:
        """Generates a completion for the given content.

        Args:
            content (str): The content to generate a completion for.
            **kwargs (Any): Additional arguments for the generation.

        Returns:
            Any: The generated completion.
        """
        return self.model.generate_content(content, **kwargs)
