
from airless.core.hook import BaseHook


class LLMHook(BaseHook):

    def __init__(self):
        super().__init__()
        self.historic = ''

    def historic_append(self, text, actor):
        self.historic += f"---\n{actor}\n---\n{text}\n"

    def generate_completion(self, content, **kwargs):
        raise NotImplementedError()
