from sus.config.checker import *

available_options = [
#   [internal name, type, default value, description, extra],
    ["token",                           str, None, None, {"secret": True}],
    ["swapfinder.scan_path",            str, None, None],
    ["swapfinder.report_channel_id",    int, None, None],
    ["swapfinder.max_preview_size",     int, 1024 * 1024 * 8, None],
    ["swapfinder.max_file_size",        int, 1024 * 1024 * 64, None],
    ["swapfinder.preview_size",         int, 400, None],
    ["clickup.token",                   str, None, None, {"secret": True, "checker": clickup_checker}],
    ["clickup.mention_id",              int, None, None],
    ["clickup.report_channel_id",       int, None, None],
]
    