# -*- coding: utf-8 -*-
"""
CONFIG/envguard.py — پل بین متغیرهای محیطی (Railway) و کانفیگ پایتون
Bridge between environment variables (Railway / Docker) and the Python config.

قاعدهٔ کار:
  • هر مقداری که در Variables ست شده باشد، بر مقدار داخل کد اولویت دارد.
  • اگر متغیری ست نشده باشد، همان مقدار پیش‌فرض `CONFIG/_config.py` استفاده می‌شود.
  • برای «خاموش‌کردن» یک مقدار اختیاری (مثل آدرس کوکی)، مقدار `off` یا `none`
    یا رشتهٔ خالی را بگذارید.

این ماژول عمداً هیچ وابستگی بیرونی ندارد تا در همان لحظهٔ ایمپورت کانفیگ
بدون نصب هیچ پکیجی کار کند.
"""
import json
import os

__all__ = [
    "has", "raw", "s", "opt", "i", "f", "b", "lst", "ints", "js", "mask",
    "require", "require_int", "warn_if_placeholder", "report", "fail_messages",
]

# مقادیری که معنی «ست نشده / خاموش» می‌دهند
_UNSET = {"", "off", "none", "null", "nil", "-", "disabled", "disable", "unset"}
_TRUE = {"1", "true", "yes", "y", "on", "enable", "enabled", "t", "بله", "روشن"}
_FALSE = {"0", "false", "no", "n", "off", "disable", "disabled", "f", "خیر", "خاموش"}

# خطاهایی که در اعتبارسنجی جمع می‌شوند (فارسی/انگلیسی)
_MISSING = []


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def raw(name, default=None):
    """مقدار خام متغیر محیطی (بدون هیچ تفسیری)."""
    if name in os.environ:
        return os.environ[name]
    return default


def has(name):
    """True فقط وقتی متغیر ست شده باشد و مقدارش «خاموش/خالی» نباشد."""
    value = _clean(os.environ.get(name))
    return bool(value) and value.lower() not in _UNSET


def s(name, default=None):
    """رشته؛ اگر متغیر نبود یا خالی بود ⇒ پیش‌فرض."""
    value = _clean(os.environ.get(name))
    return value if value else default


def opt(name, default=None, off_values=_UNSET):
    """رشتهٔ اختیاری؛ `off`/`none`/خالی ⇒ پیش‌فرض (برای غیرفعال‌کردن آدرس‌ها)."""
    value = _clean(os.environ.get(name))
    if not value or value.lower() in off_values:
        return default
    return value


def i(name, default=0, minimum=None, maximum=None):
    """عدد صحیح؛ مقدار نامعتبر ⇒ خطای واضح (تا اشتباه تایپی در Variables دیده شود)."""
    value = _clean(os.environ.get(name))
    if not value:
        return default
    try:
        number = int(float(value.replace(",", "").replace("_", "")))
    except ValueError:
        raise ValueError(
            "متغیر %s باید عدد باشد ولی «%s» داده شده است. | "
            "%s must be an integer, got %r" % (name, value, name, value)
        )
    if minimum is not None and number < minimum:
        raise ValueError("متغیر %s باید ≥ %s باشد (مقدار فعلی: %s)" % (name, minimum, number))
    if maximum is not None and number > maximum:
        raise ValueError("متغیر %s باید ≤ %s باشد (مقدار فعلی: %s)" % (name, maximum, number))
    return number


def f(name, default=0.0):
    """عدد اعشاری."""
    value = _clean(os.environ.get(name))
    if not value:
        return default
    try:
        return float(value.replace(",", ""))
    except ValueError:
        raise ValueError("متغیر %s باید عدد باشد ولی «%s» داده شده است." % (name, value))


def b(name, default=False):
    """بولین؛ true/false/1/0/on/off قابل قبول است."""
    value = _clean(os.environ.get(name))
    if not value:
        return default
    low = value.lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    return default


def lst(name, default=(), cast=str):
    """
    لیست؛ هم JSON قبول می‌کند و هم جداکنندهٔ کاما/فاصله.
      ADMIN="12345,67890"  یا  ADMIN='[12345, 67890]'
    """
    value = _clean(os.environ.get(name))
    if not value:
        return list(default)
    items = None
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                items = parsed
        except Exception:
            items = None
    if items is None:
        items = [part for part in value.replace(",", " ").split() if part]
    out = []
    for item in items:
        try:
            out.append(cast(item))
        except Exception:
            continue
    return out


def ints(name, default=()):
    """لیست عدد صحیح (برای ADMIN و شناسهٔ گروه‌ها/کانال‌ها)."""
    return lst(name, default, int)


def js(name, default=None):
    """دیکشنری از JSON داخل متغیر محیطی (برای FIREBASE_CONF)."""
    value = _clean(os.environ.get(name))
    if not value:
        return default
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else default
    except Exception as exc:
        raise ValueError("متغیر %s باید JSON معتبر باشد (%s)" % (name, exc))


def mask(value, keep=6):
    """پنهان‌کردن مقدارهای حساس در لاگ."""
    text = _clean(value)
    if not text:
        return "(خالی)"
    if len(text) <= keep + 2:
        return text[:2] + "…"
    return text[:keep] + "…" + text[-2:]


def require(name, description=""):
    """اگر متغیر ست نشده باشد، در لیست خطاها ثبت می‌شود و مقدار None برمی‌گردد."""
    if has(name):
        return s(name)
    _MISSING.append((name, description))
    return None


def require_int(name, description="", minimum=1):
    """مثل require ولی عدد صحیح؛ مقدار نامعتبر/صفر ⇒ خطای «ست نشده»."""
    if not has(name):
        _MISSING.append((name, description))
        return 0
    value = i(name, 0)
    if value < minimum:
        _MISSING.append((name, description or "باید عدد مثبت باشد"))
        return 0
    return value


def warn_if_placeholder(name, value, placeholders=("XXXXXXXX", "abc0000", "00000000000:", "@")):
    """هشدار برای مقادیری که به‌جای مقدار واقعی، نمونهٔ داخل کد مانده‌اند."""
    text = _clean(value)
    if not text:
        return False
    for marker in placeholders:
        if marker and marker in text:
            return True
    return False


def fail_messages():
    return list(_MISSING)


def report(title, rows, warnings=()):
    """
    چاپ یک جدول کوتاه در لاگ راه‌اندازی (مقدارهای حساس ماسک می‌شوند).
    rows: لیست (نام، مقدار، آیا حساس است)
    """
    line = "─" * 62
    print("\n" + line)
    print("  " + title)
    print(line)
    for item in rows:
        name, value = item[0], item[1]
        secret = item[2] if len(item) > 2 else False
        shown = mask(value) if secret else (_clean(value) or "(ست نشده)")
        if len(shown) > 34:
            shown = shown[:31] + "…"
        print("   %-26s : %s" % (name, shown))
    for warning in warnings:
        print("   ⚠️  " + warning)
    print(line + "\n")
