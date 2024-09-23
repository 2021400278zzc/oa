from typing import Any, Literal


def is_value_valid(*args: Any) -> bool:
    """值是否不为None, "", 0, False, []
    Args:
        *args (Any): 需要被验证的值。
    Returns:
        bool: 如果所有参数不为None，返回True。
    """
    return all(bool(arg) for arg in args)


def unpack_value(content: dict, *args: str) -> tuple[Any, ...]:
    """解包字典内的值
    Args:
        content (dict): 需要被解包的字典内容。
        *args (Any): 需被解包值的键。
    Returns:
        tuple ([Any, ...]): 返回的元组对象
    """
    return tuple(content.get(arg) for arg in args)
