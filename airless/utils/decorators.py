import logging
import warnings
import functools

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def deprecated(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        message = f"This function is deprecated {func.__name__}."
        warnings.warn(message, category=DeprecationWarning, stacklevel=2)
        logger.warning(message)
        return func(*args, **kwargs)
    return wrapper
