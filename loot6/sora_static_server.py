from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = 8099
DIRECTORY = "/home/ubuntu/sora-images"

class NoListHandler(SimpleHTTPRequestHandler):
    def list_directory(self, path):
        self.send_error(403, "Directory listing disabled")
        return None

handler = partial(NoListHandler, directory=DIRECTORY)
server = ThreadingHTTPServer(("0.0.0.0", PORT), handler)
print(f"Serving {DIRECTORY} on 0.0.0.0:{PORT}", flush=True)
server.serve_forever()
