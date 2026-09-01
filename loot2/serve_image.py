#!/usr/bin/env python3
"""Serve image via HTTP for browser viewing"""
import http.server
import socketserver
import base64
import os
import json

PORT = 8765

# Read image
img_path = "/root/.hermes/image_cache/img_ae658514bf81.jpg"
with open(img_path, 'rb') as f:
    img_data = f.read()

b64_data = base64.b64encode(img_data).decode('utf-8')

html_content = f"""<!DOCTYPE html>
<html>
<head><title>Image Analysis</title></head>
<body style="margin:0; padding:20px; background:white;">
<img src="data:image/jpeg;base64,{b64_data}" style="max-width:100%;" id="theImage">
</body>
</html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def log_message(self, format, *args):
        print(f"[Server] {args}")

print(f"Serving image on http://localhost:{PORT}")
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
