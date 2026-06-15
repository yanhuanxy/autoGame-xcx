"""Java WeixinMessage / MessageItem ↔ Python dict 转换。

SDK 模型类是 Java bean（getXxx 风格 getter）。
JPype convertStrings=True 时 String 自动转 Python str，
但 long/int 等仍以 Java 对象形式返回，需显式 int()。
"""
from __future__ import annotations

from typing import Any


def weixin_to_python(msg: Any) -> dict:
    """转换 com.github.wechat.ilink.sdk.core.model.WeixinMessage 为 dict。

    Args:
        msg: JPype 包装的 WeixinMessage Java 对象。

    Returns:
        {
            "message_id": int | None,
            "message_type": int | None,         # 1=text 2=image 3=voice 4=file 5=video
            "from_user_id": str,
            "to_user_id": str,
            "create_time_ms": int | None,
            "context_token": str | None,
            "items": [item_dict, ...],
        }
    """
    return {
        "message_id": _safe_int(getattr(msg, "getMessage_id", lambda: None)),
        "message_type": _safe_int(getattr(msg, "getMessage_type", lambda: None)),
        "from_user_id": _safe_str(getattr(msg, "getFrom_user_id", lambda: None)),
        "to_user_id": _safe_str(getattr(msg, "getTo_user_id", lambda: None)),
        "create_time_ms": _safe_int(getattr(msg, "getCreate_time_ms", lambda: None)),
        "context_token": _safe_str(getattr(msg, "getContext_token", lambda: None)),
        "items": [message_item_to_python(item) for item in _iter_items(msg)],
    }


def message_item_to_python(item: Any) -> dict:
    """转换 MessageItem。

    type=1: text_item.getText()
    type=2: image_item.getMedia() / getAeskey()
    type=3: voice_item.getMedia() / getPlaytime()
    type=4: file_item.getMedia() / getFile_name()
    type=5: video_item.getMedia() / getPlay_length()
    """
    result: dict = {"type": _safe_int(getattr(item, "getType", lambda: 0))}

    text_item = _get(item, "getText_item")
    if text_item is not None:
        result["text"] = _safe_str(_get(text_item, "getText"))
        return result

    image_item = _get(item, "getImage_item")
    if image_item is not None:
        result["image"] = {
            "media": _safe_str(_get(image_item, "getMedia")),
            "aeskey": _safe_str(_get(image_item, "getAeskey")),
        }
        return result

    voice_item = _get(item, "getVoice_item")
    if voice_item is not None:
        result["voice"] = {
            "media": _safe_str(_get(voice_item, "getMedia")),
            "playtime_ms": _safe_int(_get(voice_item, "getPlaytime")),
        }
        return result

    file_item = _get(item, "getFile_item")
    if file_item is not None:
        result["file"] = {
            "media": _safe_str(_get(file_item, "getMedia")),
            "file_name": _safe_str(_get(file_item, "getFile_name")),
        }
        return result

    video_item = _get(item, "getVideo_item")
    if video_item is not None:
        result["video"] = {
            "media": _safe_str(_get(video_item, "getMedia")),
            "play_length_ms": _safe_int(_get(video_item, "getPlay_length")),
        }
        return result

    return result


def _iter_items(msg: Any) -> list:
    """从 WeixinMessage.getItem_list() 取列表。

    Spike 发现：JPype 的 java.util.List 不能直接当 Python list，
    但可以迭代。这里转为 Python list 兜底。
    """
    items = _get(msg, "getItem_list")
    if items is None:
        return []
    try:
        return list(items)
    except Exception:
        # 退化到索引访问
        result = []
        try:
            length = len(items)
            for i in range(length):
                result.append(items[i])
        except Exception:
            pass
        return result


def _get(java_obj: Any, method_name: str) -> Any:
    """安全调用 Java getter，不存在时返回 None。"""
    method = getattr(java_obj, method_name, None)
    if method is None:
        return None
    try:
        return method()
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
