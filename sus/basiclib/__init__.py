import datetime
import math
import re

def convert_bytes(n):
    prefix = ['', 'K', 'M', 'G', 'T']
    for i in reversed(range(len(prefix))):
        if n >= 1 << (10 * i):
            return "%.2f %sB" % (float(n) / (1 << (10 * i)), prefix[i])

def convert_time(t):
    unit = ['ms', 's', 'm', 'h', 'd']
    ratio = [0.001, 1, 60, 60 * 60, 24 * 60 * 60]
    for i in reversed(range(1, len(unit))):
        if t >= ratio[i]:
            first = math.floor(t / ratio[i])
            t = t - ratio[i] * first
            second = round(t / ratio[i - 1])
            return "%d%s %d%s" % (first, unit[i], second, unit[i - 1])
        
def unix_to_date(t):
    return datetime.datetime.fromtimestamp(t).strftime("%b %d")

def unix_to_datetime(t):
    return datetime.datetime.fromtimestamp(t).strftime("%b %d %H:%M")

def escape_url(s):
    "Heuristically put angle brackets (<>) around urls. Useful to send a message without embed (preview)."
    # Detect URLs to disable embeded, see [https://regexr.com/37i6s] 
    pattern = r"<?(https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\b(?:[-a-zA-Z0-9@:%_\+.~#?&\/=]*))>?"
    return re.sub(pattern, r"\1", s)