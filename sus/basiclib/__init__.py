import math

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