#!/usr/bin/env python3
import os, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

port = int(os.environ.get('PORT', 8080))
directory = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(directory)
os.chdir(parent)
print(f"Serving {parent} on http://localhost:{port}")
HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler).serve_forever()
