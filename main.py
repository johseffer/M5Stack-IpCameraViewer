import os, sys, io
import uos
import json
import gc
import M5
from M5 import *
import network
import requests
import time
import usocket

image0 = None
wlan = None
http_req = None
ITER_CHUNK_SIZE = 128
index = 0
image_valid = None

WIFI_SSID = ""
WIFI_PWD = ""

# PHP APP hosted in localhost to resize images to 320x240
RESIZE_HOST = "http://192.168.0.2"

# available in https://search.censys.io/ or https://en.fofa.info/
images_dict = [
  "http://45.237.128.165:8088/shot.jpg?rnd=343590",
  "http://45.234.64.55:8000/webcapture.jpg?command=snap%26channel=1",
  "http://189.84.174.53:81/webcapture.jpg?command=snap%26channel=1",  
  "http://189.7.161.83:9000/cgi-bin/snapshot.cgi",
  "http://45.230.116.178:9000/webcapture.jpg?command=snap%26channel=1",
  "http://168.0.126.43:8001/webcapture.jpg?command=snap%26channel=1"
]

# iter_content not available in Micropython requests package. ref: https://github.com/micropython/micropython-lib/pull/278
class Response:
    def __init__(self, f):
        self.raw = f
        self.encoding = "utf-8"
        self._content_consumed = False
        self._cached = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __iter__(self):
        return self.iter_content()

    def close(self):
        if self.raw:
            self.raw.close()
            self.raw = None
        self._cached = None

    @property
    def content(self):
        if self._cached is None:
            try:
                self._cached = self.raw.read()
            finally:
                self.raw.close()
                self.raw = None
        return self._cached

    def iter_content(self, chunk_size=ITER_CHUNK_SIZE):
        def generate():
            while True:
                chunk = self.raw.read(chunk_size)
                if not chunk:
                    break
                yield chunk
            self._content_consumed = True

        if self._content_consumed:
            raise RuntimeError("response already consumed")
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(
                "chunk_size must be an int, it is instead a %s." % type(chunk_size)
            )

        return generate()

def request(method,url,data=None,json=None,headers={},stream=None,timeout=None,parse_headers=True):
    redirect = None
    try:
        proto, dummy, host, path = url.split("/", 3)
    except ValueError:
        proto, dummy, host = url.split("/", 2)
        path = ""
    if proto == "http:":
        port = 80
    elif proto == "https:":
        import tls
        port = 443
    else:
        raise ValueError("Unsupported protocol: " + proto)

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
    ai = ai[0]

    resp_d = None
    if parse_headers is not False:
        resp_d = {}

    s = usocket.socket(ai[0], ai[1], ai[2])

    if timeout is not None:
        s.settimeout(timeout)
    status = 200
    try:
        s.connect(ai[-1])
        if proto == "https:":
            context = tls.SSLContext(tls.PROTOCOL_TLS_CLIENT)
            context.verify_mode = tls.CERT_NONE
            s = context.wrap_socket(s, server_hostname=host)
        s.write(b"%s /%s HTTP/1.0\r\n" % (method, path))
        if not "Host" in headers:
            s.write(b"Host: %s\r\n" % host)
        for k in headers:
            s.write(k)
            s.write(b": ")
            s.write(headers[k])
            s.write(b"\r\n")
        if json is not None:
            assert data is None
            import ujson

            data = ujson.dumps(json)
            s.write(b"Content-Type: application/json\r\n")
        if data:
            s.write(b"Content-Length: %d\r\n" % len(data))
        s.write(b"\r\n")
        if data:
            s.write(data)

        l = s.readline()
        # print(l)
        l = l.split(None, 2)
        status = int(l[1])
        reason = ""
        if len(l) > 2:
            reason = l[2].rstrip()
        while True:
            l = s.readline()
            if not l or l == b"\r\n":
                break
            # print(l)
            if l.startswith(b"Transfer-Encoding:"):
                if b"chunked" in l:
                    raise ValueError("Unsupported " + str(l, "utf-8"))
            elif l.startswith(b"Location:") and not 200 <= status <= 299:
                if status in [301, 302, 303, 307, 308]:
                    redirect = str(l[10:-2], "utf-8")
                else:
                    raise NotImplementedError("Redirect %d not yet supported" % status)
    except OSError:
        s.close()

    if redirect:
        s.close()
        if status in [301, 302, 303]:
            return request("GET", redirect, None, None, headers, stream)
        else:
            return request(method, redirect, data, json, headers, stream)
    else:
        resp = Response(s)
        resp.status_code = status
        resp.reason = reason
        if resp_d is not None:
            resp.headers = resp_d
        return resp

def get(url, **kw):
    return request("GET", url, **kw)

def error_next():
  global image0
  global image_valid  

  image_valid = False
  print("SET ERROR IMAGE")
  Speaker.tone(2000, 200)
  Speaker.tone(1000, 200)

def download_image_resized(img):
  try:    
    resized = RESIZE_HOST + "/?url=" + img
    http_req = get(resized, headers={'Content-Type': 'application/octet-stream'}, timeout=2000)
    if http_req.status_code == 200:
      with open("res/img/test.jpg", 'wb') as file:
        for chunk in http_req.iter_content(chunk_size=512):
          file.write(chunk)      
    else:      
      print("Response error")
      error_next()
  except Exception as e:
    from utility import print_error_msg
    print_error_msg(e)
    error_next()

def set_image():
  global index
  global images_dict
  global image0
  global image_valid

  if image_valid == True:
    img = images_dict[index]
    download_image_resized(img)
    image0.setImage("res/img/test.jpg")       
  else:    
    image0.setImage("res/img/404.jpg")   

def next_image():
  global index
  global images_dict
  global image_valid

  index = index + 1 if index < len(images_dict)-1 else 0
  print("image: "+str(index)+" - "+images_dict[index])
  image_valid = True

def btnA_wasClicked_event(state):
  Speaker.tone(2000, 50)
  next_image()

def setup():
  global image0 
  global image_valid

  M5.begin() 
  # image flicking when scale < 1
  image0 = Widgets.Image("res/img/default.jpg", 0, 0, scale_x=1, scale_y=1)
  wlan = network.WLAN(network.STA_IF)
  while not wlan.isconnected():
    try:
      print("Connecting to "+ WIFI_SSID + "...")    
      wlan.connect(WIFI_SSID, WIFI_PWD)
      print("Connected Succesfully")
    except Exception as e:
      Widgets.fillScreen(0xff0000)
  image_valid = True
  
def loop():
  # Hold the button to change image carrousel
  BtnA.setCallback(type=BtnA.CB_TYPE.WAS_HOLD, cb=btnA_wasClicked_event)    
  if BtnB.wasPressed():
    error_next()
  M5.update()

if __name__ == '__main__':
  try:
    setup()
    while True:                        
      # async operations still not running on M5Stack      
      set_image()  
      loop()          
  except (Exception, KeyboardInterrupt) as e:
    try:
      from utility import print_error_msg
      print_error_msg(e)
    except ImportError:
      print("please update to latest firmware")
