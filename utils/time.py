from datetime import datetime


def timey_whimy(secs):
    intervals = (('years', 31536000), ('months', 2592000), ('weeks', 604800),
                 ('days', 86400), ('hours', 3600), ('minutes', 60), ('seconds', 1))
    result = []
    for name, count in intervals:
        value = secs // count
        if value:
            secs -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append(f"{value} {name}")
    if not result:
        result = ["0 secon- well I guess now"]
    return ', '.join(result)


def datey_whity(time):
    date_time = datetime.fromtimestamp(time)
    return date_time.strftime('%a, %b %-d %Y\n%-I:%M:%S %p (GMT)')
