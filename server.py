from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import parse_qs
import http.cookies as cookies

import cli as control

class Handler(BaseHTTPRequestHandler):
	# Add CORS support
	def end_headers(self):
		self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
		self.send_header("Access-Control-Allow-Headers", "Content-Type, Content-Length")
		self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT")
		self.send_header("Access-Control-Allow-Credentials", "true")
		self.sendCookie()
		BaseHTTPRequestHandler.end_headers(self)

	def handle404(self):
		self.send_response(404)
		self.send_header("Content-Type", "text/plain")
		self.end_headers()

		self.wfile.write("This path doesn't exist.".encode("utf-8"))

	def getJSON(self):
		# --- Error handling ---
		if "Content-Length" not in self.headers:
			print("Content-Length not present in headers")
			return (400, {})
		if self.headers["Content-Length"] == "0":
			print("Content-Length is equal to 0")
			return (400, {})

		# Parse body
		raw_body = self.rfile.read(int(self.headers["Content-Length"]))

		try:
			body = json.loads(raw_body.decode("utf-8"))
		except json.decoder.JSONDecodeError:
			print("JSON not valid.")
			print(raw_body)
			body = {}
			return (400, {})

		print("Body: " + str(body))
		return (201, body)

	def loadCookie(self):
		if "Cookie" in self.headers:
			self.cookie = cookies.SimpleCookie(self.headers["Cookie"])
		else:
			self.cookie = cookies.SimpleCookie()

	def sendCookie(self):
		if not hasattr(self, "cookie"): return

		for morsel in self.cookie.values():
			self.send_header("Set-Cookie", morsel.OutputString())

	def checkPath(self, mask):
		mask_parts = mask[1:].split("/")
		path_parts = self.path[1:].rstrip("/").split("/")
		if len(mask_parts) != len(path_parts):
			self.urlVars = {}
			return False

		vars = {}
		for i in range(len(mask_parts)):
			if mask_parts[i][0] == "{":
				vars[mask_parts[i][1:-1]] = path_parts[i]
			else:
				if mask_parts[i] != path_parts[i]:
					self.urlVars = {}
					return False

		self.url_vars = vars
		return True

	def sendError(self, status_code, error):
		self.send_response(status_code)
		self.send_header("Content-Type", "text/plain")
		self.end_headers()
		self.wfile.write(error.encode("utf-8"))

	def do_OPTIONS(self):
		self.send_response(200)
		self.end_headers()

	def do_GET(self):
		self.loadCookie()	# Always load the cookie regardless of whether it's used or not

		if self.checkPath("/songs"):
			self.send_response(200)
			self.send_header("Content-Type", "application/json")
			self.end_headers()

			self.wfile.write(json.dumps(control.getSongs()).encode("utf-8"))
		elif self.checkPath("/engineState"):
			self.send_response(200)
			self.send_header("Content-Type", "application/json")
			self.end_headers()

			self.wfile.write(json.dumps(control.engineState).encode("utf-8"))
		else:
			self.handle404()

	def do_POST(self):
		self.loadCookie()

		if self.checkPath("/startEngine"):
			if control.engineState["active"]:
				self.sendError(409, "Engine is already running.")
				return

			status_code, body = self.getJSON()
			if status_code < 200 or status_code > 299:
				self.sendError(status_code, "Could not parse request body as JSON.")
				return

			bigRange = False
			if "bigrange" in body:
				bigRange = body["bigrange"]

			self.send_response(200)
			self.end_headers()
			
			control.startEngine(bigRange=bigRange)

		elif self.checkPath("/stopEngine"):
			if not control.engineState["active"]:
				self.sendError(409, "Engine isn't running.")
				return

			self.send_response(200)
			self.end_headers()

			control.stopEngine()

		elif self.checkPath("/play"):
			# check if engine is started or not
			if not control.engineState["active"]:
				self.sendError(409, "Engine isn't running.")
				return

			status_code, body = self.getJSON()
			if status_code < 200 or status_code > 299:
				self.sendError(status_code, "Could not parse request body as JSON.")
				return

			if "song" not in body:
				self.sendError(400, "Song key isn't present in request body.")
				return

			bigRange = False
			if "bigrange" in body:
				bigRange = body["bigrange"]

			self.send_response(200)
			self.end_headers()

			control.playSong(body["song"], bigRange=bigRange)

		elif self.checkPath("/stopSong"):
			if not control.engineState["active"] or not control.songPlaying:
				self.sendError(409, "Engine isn't on and/or no song is currently playing.")
				return

			self.send_response(200)
			self.end_headers()

			control.stopSong()

		else:
			self.handle404()


def main():
	listen = ("0.0.0.0", 3055)
	server = HTTPServer(listen, Handler)

	print("Listening...")
	server.serve_forever()

if __name__ == "__main__":
	main()
