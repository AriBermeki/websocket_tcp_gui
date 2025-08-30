import asyncio
import inspect
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import ValidationError, create_model

_event_callbacks: Dict[str, List[Callable[..., Union[None, Awaitable[None]]]]] = {}
_dependency_cache: Dict[type, Any] = {}


def command(func_or_event: Union[None, str, Callable] = None):
    """
    Register a function as an event command handler.

    If used as a decorator, the function will be stored in the
    global ``_event_callbacks`` dictionary and invoked when the
    matching event is dispatched.

    :param func_or_event: Either the function to register directly,
        or the event name as a string. If ``None``, the function name
        is used as the event key.
    :return: The decorated function.
    """
    if callable(func_or_event):
        func = func_or_event
        key = func.__name__
        _event_callbacks.setdefault(key, []).append(func)
        return func

    def decorator(func: Callable):
        key = func_or_event or func.__name__
        _event_callbacks.setdefault(key, []).append(func)
        return func

    return decorator


def _resolve_final_type(tp: Any) -> Any:
    """
    Resolve the underlying type from type hints.

    Handles Annotated, Union, and generic origins to return the
    final usable type.

    :param tp: A typing annotation.
    :return: The resolved base type.
    """
    origin = get_origin(tp)

    if origin is Union:
        return tp
    elif origin is Annotated:
        return get_args(tp)[0]
    elif origin:
        return origin

    return tp


async def resolve_dependency(dep_type: type) -> Any:
    """
    Resolve or instantiate a dependency type.

    Instances are cached globally in ``_dependency_cache`` to avoid
    repeated instantiations.

    :param dep_type: The type to resolve.
    :return: An instance of the dependency.
    :raises RuntimeError: If the dependency cannot be instantiated.
    """
    if dep_type in _dependency_cache:
        return _dependency_cache[dep_type]
    try:
        instance = dep_type()
        if asyncio.iscoroutine(instance):
            instance = await instance
        _dependency_cache[dep_type] = instance
        return instance
    except Exception as e:
        raise RuntimeError(f"Cannot instantiate type '{dep_type}': {e}")


async def make_callback(
    event: str,
    result_id: int,
    error_id: int,
    data: dict,
) -> dict:
    """
    Execute a registered callback for a given event.

    Validates input parameters against type hints using Pydantic
    models, resolves dependencies if required, and returns the result.

    :param event: The event name to dispatch.
    :param result_id: Identifier for the success response.
    :param error_id: Identifier for error responses.
    :param data: Input data to pass to the callback function.
    :return: A dictionary containing either ``{"result_id": ..., "result": ...}``
        on success or ``{"error_id": ..., "error": ...}`` on failure.
    """
    for func in _event_callbacks.get(event, []):
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        values: Dict[str, Any] = {}
        errors = []
        data_fields = {}

        for name, param in sig.parameters.items():
            hint = type_hints.get(name, Any)
            final_type = _resolve_final_type(hint)
            is_dependency = inspect.isclass(final_type) and not isinstance(final_type, type(Any))

            if name in data:
                data_fields[name] = (final_type, ...)
                values[name] = data[name]
            elif param.default is not inspect.Parameter.empty:
                data_fields[name] = (final_type, param.default)
            elif is_dependency:
                try:
                    values[name] = await resolve_dependency(final_type)
                except Exception as e:
                    errors.append(f"{name}: {e}")
            else:
                errors.append(f"{name} is missing")

        if errors:
            return {"error_id": error_id, "error": f"Invalid parameters: {', '.join(errors)}"}

        if data_fields:
            Model = create_model(f"{func.__name__}_Validator", **data_fields)
            try:
                validated = Model(**{k: values[k] for k in data_fields})
                for field in data_fields:
                    values[field] = getattr(validated, field)
            except ValidationError as e:
                return {"error_id": error_id, "error": f"Pydantic validation failed: {e}"}

        try:
            result = await func(**values) if inspect.iscoroutinefunction(func) else func(**values)
            return {"result_id": result_id, "result": result}
        except Exception as e:
            return {"error_id": error_id, "error": str(e)}

    return {"error_id": error_id, "error": f"No handler registered for event '{event}'"}
