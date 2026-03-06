"""
Logging utilities for capturing and displaying logs in the Streamlit UI.
"""
import logging
from collections import deque
from datetime import datetime
import threading

class StreamlitLogBuffer:
    """A thread-safe circular buffer to store the latest log messages."""

    def __init__(self, max_size=50):
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()

    def add(self, level, message):
        """Add a log message to the buffer."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        with self.lock:
            self.buffer.append({
                "time": timestamp,
                "level": level,
                "message": message
            })

    def get_logs(self):
        """Retrieve all logs from the buffer."""
        with self.lock:
            return list(self.buffer)

class StreamlitLogHandler(logging.Handler):
    """A logging handler that redirects logs to a StreamlitLogBuffer."""

    def __init__(self, buffer):
        super().__init__()
        self.buffer = buffer

    def emit(self, record):
        """Emit a log record to the buffer."""
        msg = self.format(record)
        self.buffer.add(record.levelname, msg)

# Global buffer instance
log_buffer = StreamlitLogBuffer()

def setup_streamlit_logging():
    """Configure the root logger to use our StreamlitLogHandler."""
    handler = StreamlitLogHandler(log_buffer)
    formatter = logging.Formatter('%(name)s: %(message)s')
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Avoid adding multiple handlers if setup is called multiple times
    if not any(isinstance(h, StreamlitLogHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
