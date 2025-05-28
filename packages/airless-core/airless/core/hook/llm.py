
from airless.core.hook import BaseHook


class LLMHook(BaseHook):
    """Base class for Large Language Model (LLM) hooks.

    This class provides a basic structure for interacting with LLMs.
    It includes methods for managing conversation history and generating
    text completions.

    Attributes:
        historic (str): A string storing the conversation history.
    """

    def __init__(self):
        """Initializes the LLMHook.

        Sets up the conversation history attribute.
        """
        super().__init__()
        self.historic = ''

    def historic_append(self, text, actor):
        """Appends text to the conversation history.

        Args:
            text (str): The text to append.
            actor (str): The actor who produced the text (e.g., 'user', 'model').
        """
        self.historic += f"---\n{actor}\n---\n{text}\n"

    def generate_completion(self, content, **kwargs):
        """Generates a text completion using the LLM.

        This method should be implemented by subclasses to interact with
        a specific LLM API.

        Args:
            content (str): The prompt or content to generate a completion for.
            **kwargs: Additional keyword arguments for the LLM API.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError()
