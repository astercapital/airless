# It's common to have an __init__.py, even if it's empty or only defines __all__ for future use.
# If other hooks/classes were present, they would remain.
from .hook import GenerativeModelHook, GeminiApiHook # Ensure GeminiApiHook is imported

__all__ = [
    "GenerativeModelHook", # Assuming this is still exported
    "GeminiApiHook",
]
