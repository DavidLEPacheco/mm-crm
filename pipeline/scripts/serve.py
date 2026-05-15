#!/usr/bin/env python3
import os, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

port = int(os.environ.get('PORT', 8080))
os.chdir('/Users/gf/Downloads')
print(f"Serving /Users/gf/Downloads on http://localhost:{port}")
HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler).serve_forever()
