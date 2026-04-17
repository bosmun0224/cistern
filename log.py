# log.py - Persistent file logger for Pico W
# Writes to flash so logs survive crashes and can be read via mpremote.
import time

LOG_FILE = 'device.log'
MAX_SIZE = 16384  # 16KB max, then truncate oldest half

# Most recent WARN/ERR kept in memory for telemetry
last_error = None


def _timestamp():
    t = time.localtime()
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5])


def _check_size():
    """Truncate log if it exceeds MAX_SIZE by keeping the newest half."""
    try:
        import os
        size = os.stat(LOG_FILE)[6]
        if size > MAX_SIZE:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
            half = len(lines) // 2
            with open(LOG_FILE, 'w') as f:
                f.write('--- log truncated ---\n')
                for line in lines[half:]:
                    f.write(line)
    except OSError:
        pass


def log(msg, level='INFO'):
    """Append a timestamped line to the log file and print to console."""
    line = f"[{_timestamp()}] {level}: {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
        _check_size()
    except Exception:
        pass


def info(msg):
    log(msg, 'INFO')


def warn(msg):
    global last_error
    last_error = f"WARN: {msg}"
    log(msg, 'WARN')


def error(msg):
    global last_error
    last_error = f"ERR: {msg}"
    log(msg, 'ERR')


def read_log(tail=30):
    """Return the last `tail` lines of the log (for REPL use)."""
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
        for line in lines[-tail:]:
            print(line, end='')
    except OSError:
        print('No log file.')


def clear():
    """Delete the log file."""
    try:
        import os
        os.remove(LOG_FILE)
        print('Log cleared.')
    except OSError:
        pass
