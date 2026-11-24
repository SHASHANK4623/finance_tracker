from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name='inr')
def inr_filter(value):
    """
    Formats a number with Indian currency grouping (e.g. 1,00,00,000 for 1 Cr, 23,00,000 for 23 Lakhs).
    Usage: {{ amount|inr }}
    """
    if value is None or value == "":
        return "0"
    
    try:
        val = float(value)
    except (ValueError, TypeError):
        return str(value)

    is_neg = val < 0
    val = abs(val)

    # Format integer part and decimals
    # If it has meaningful cents / decimals, preserve them
    rounded_val = round(val, 2)
    s = f"{rounded_val:.2f}"
    int_part, dec_part = s.split(".")
    
    dec_suffix = f".{dec_part}" if int(dec_part) > 0 else ""

    if len(int_part) <= 3:
        formatted = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        parts = []
        while len(remaining) > 2:
            parts.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            parts.insert(0, remaining)
        formatted = ",".join(parts) + "," + last_three

    result = f"{formatted}{dec_suffix}"
    return f"-{result}" if is_neg else result


@register.filter(name='inr_words')
def inr_words_filter(value):
    """
    Formats large currency amounts into Crores / Lakhs representation.
    e.g. 10000000 -> 1.00 Cr, 2300000 -> 23.00 L
    """
    if value is None or value == "":
        return "₹ 0"
    
    try:
        val = float(value)
    except (ValueError, TypeError):
        return str(value)

    is_neg = val < 0
    val = abs(val)

    if val >= 10000000:
        cr = val / 10000000.0
        res = f"{cr:.2f} Cr"
    elif val >= 100000:
        lakhs = val / 100000.0
        res = f"{lakhs:.2f} Lakhs"
    elif val >= 1000:
        k = val / 1000.0
        res = f"{k:.1f} K"
    else:
        res = f"{val:.2f}"

    return f"-₹ {res}" if is_neg else f"₹ {res}"
