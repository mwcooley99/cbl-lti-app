def safe_round(num, digits):
    if num:
        return round(num, 2)
    else:
        return num