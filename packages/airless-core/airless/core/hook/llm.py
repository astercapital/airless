
from airless.core.hook import BaseHook


class LLMHook(BaseHook):

    def __init__(self):
        super().__init__()
        self.user_prompt = []
        self.responses = []

    def config(self, model_name, **kwargs):
        raise NotImplementedError()

    def generate_completion(self, user, **kwargs):
        raise NotImplementedError()
