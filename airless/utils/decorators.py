
import warnings
import functools


def deprecatedF(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if hasattr(func, '__self__'):
            cls_name = func.__self__.__class__.__name__
        else:
            cls_name = func.__module__
        message = f"This function is deprecated {cls_name}.{func.__name__}."

        warnings.simplefilter('always', DeprecationWarning)  # turn off filter
        warnings.warn(message, category=DeprecationWarning, stacklevel=2)
        warnings.simplefilter('default', DeprecationWarning)  # reset filter

        return func(*args, **kwargs)
    return wrapper


def deprecatedCls(cls):
    class NewCls(cls):
        def __init__(self, *args, **kwargs):
            super(NewCls, self).__init__(*args, **kwargs)
            message = f"This class is deprecated {cls.__name__}."
            warnings.simplefilter('always', DeprecationWarning)  # turn off filter
            warnings.warn(message, category=DeprecationWarning, stacklevel=2)
            warnings.simplefilter('default', DeprecationWarning)  # reset filter

        def __getattribute__(self, name):
            attr = super(NewCls, self).__getattribute__(name)
            if callable(attr):
                @functools.wraps(attr)
                def wrapper(*args, **kwargs):
                    message = f"This method is deprecated {cls.__name__}.{name}."
                    warnings.simplefilter('always', DeprecationWarning)  # turn off filter
                    warnings.warn(message, category=DeprecationWarning, stacklevel=2)
                    warnings.simplefilter('default', DeprecationWarning)  # reset filter
                    return attr(*args, **kwargs)
                return wrapper
            return attr

    return NewCls
