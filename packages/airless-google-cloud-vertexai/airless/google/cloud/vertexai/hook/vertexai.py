
from typing import Any

from airless.core.utils import get_config
from airless.core.hook import LLMHook

import vertexai
from vertexai.generative_models import GenerativeModel


class VertexAiHook(LLMHook):
    """Hook for interacting with Vertex AI Generative Models."""

    def __init__(self, model_name: str, **kwargs: dict[str, Any]) -> None:
        """Initializes the GenerativeModelHook.

        Note:
            Requires the following environment variables to be set:

              - GCP_PROJECT: The Google Cloud project ID.
              - GCP_REGION: The Google Cloud region.

            These are needed to initialize the Vertex AI client with the correct context.

        Args:
            model_name (str): The name of the model to use.
            **kwargs (Any): Additional arguments for model initialization.
        """
        super().__init__()
        vertexai.init(project=get_config('GCP_PROJECT'), location=get_config('GCP_REGION'))
        self.model = GenerativeModel(model_name, **kwargs)

    def generate_content(self, content: str, **kwargs: dict[str, Any]) -> Any:
        """Generates a content for the given content.

        Args:
            content (str): The content to generate a content for.
            **kwargs (Any): Additional arguments for the generation.

        Returns:
            Any: The generated content.
        """
        return self.model.generate_content(content, **kwargs)
