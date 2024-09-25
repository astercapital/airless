
from airless.core.utils import get_config
from airless.core.hook import LLMHook

import vertexai
from vertexai.generative_models import GenerativeModel


class GenerativeModelHook(LLMHook):

    def __init__(self, model_name, **kwargs):
        super().__init__()
        vertexai.init(project=get_config('GCP_PROJECT'), location=get_config('GCP_REGION'))
        self.model = GenerativeModel(model_name, **kwargs)

    def generate_completion(self, content, **kwargs):
        return self.model.generate_content(content, **kwargs)
