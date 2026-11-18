"""Render: run from repo root so docs/brochure remains available."""
import os
from pathlib import Path

chdir = str(Path(__file__).resolve().parent)
bind = '0.0.0.0:' + os.getenv('PORT', '10000')
worker_class = 'gthread'
# Socket.IO rooms are process-local; do not scale workers without a queue.
workers = 1
threads = 8
timeout = 60
graceful_timeout = 30
preload_app = False  # Create MongoClient inside the worker, never before fork.
accesslog = '-'
errorlog = '-'
capture_output = True
