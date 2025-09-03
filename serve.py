from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib
import requests

class Serv(BaseHTTPRequestHandler):
    def do_GET(self):
       if self.path == '/':
           print("Getting index.html")
           self.path = '/index.html'

       if self.path.startswith("/proxy/"):
            path = self.path[7:]
            print("Proxying", path)
            response = requests.get(path)
            self.send_response(response.status_code)
            self.end_headers()
            self.wfile.write(response.content)
            return
       else:
            try:
                print("Getting", self.path[1:])
                file_to_open = open(self.path[1:]).read()
                self.send_response(200)
            except:
                file_to_open = "File not found"
                self.send_response(404)
       self.end_headers()
       self.wfile.write(bytes(file_to_open, 'utf-8'))

httpd = HTTPServer(('localhost',8000), Serv)
httpd.serve_forever()

