#!/usr/bin/env python3
import os, sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

port = int(os.environ.get('PORT', 8080))
_serve_dir = Path(__file__).resolve().parent.parent
os.chdir(_serve_dir)
print(f"Serving {_serve_dir} on http://localhost:{port}")
HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler).serve_forever()
