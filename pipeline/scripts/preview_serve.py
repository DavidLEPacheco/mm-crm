#!/usr/bin/env python3
import os, sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

os.chdir(Path(__file__).resolve().parent)
port = int(os.environ.get('PORT', 8080))
print(f"Serving on http://localhost:{port}")
sys.stdout.flush()
HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler).serve_forever()
