from m5stack import *
from m5ui import *
from uiflow import *
import network
import smartconfig
import time
import os, sys, io
import uos
import json
import gc
import network
import time
import usocket
import nvs

image0 = None
wlan = None
http_req = None
ITER_CHUNK_SIZE = 128
index = 0
image_valid = None
mute = True

WIFI_SSID = ""
WIFI_PWD = ""

# PHP APP hosted in localhost to resize images to 320x240
RESIZE_HOST = "http://192.168.0.1"

# available in https://search.censys.io/ or https://en.fofa.info/
images_dict = [  
  "http://189.84.174.53:81/webcapture.jpg?command=snap%26channel=1",  
  "http://189.7.161.83:9000/cgi-bin/snapshot.cgi",  
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
  global mute

  image_valid = False
  if mute == False:
    speaker.tone(2000, 200)
    speaker.tone(1000, 200)

def download_image_resized(img):
  try:    
    resized = RESIZE_HOST + "/?url=" + img
    http_req = get(resized, headers={'Content-Type': 'application/octet-stream'}, timeout=2000)
    if http_req.status_code == 200:
      with open("res/test.jpg", 'wb') as file:
        for chunk in http_req.iter_content(chunk_size=512):
          file.write(chunk)      
    else:      
      print("Response error")
      error_next()
  except Exception as e:
    print(repr(e))
    error_next()

def set_image():
  global index
  global images_dict
  global image0
  global image_valid

  if image_valid == True:
    img = images_dict[index]
    download_image_resized(img)
    image0.changeImg("res/test.jpg")       
  else:    
    image0.changeImg("res/404.jpg")   

def next_image():
  global index
  global images_dict
  global image_valid

  index = index + 1 if index < len(images_dict)-1 else 0
  print("image: "+str(index)+" - "+images_dict[index])
  image_valid = True

def buttonA_wasPressed():
  global mute
  if mute == False:
    speaker.tone(2000, 50)
  next_image()

def smartconfig():
  smartconfig.set_type(smartconfig.ESPTOUCH)
  smartconfig.start()
  while (smartconfig.status()) != (smartconfig.EVENT_SEND_ACK_DONE):
    wait_ms(10)
  WIFI_SSID = smartconfig.get_ssid()
  WIFI_PWD = smartconfig.get_password()
  
  nvs.write(str('WIFI_SSID'), WIFI_SSID)
  nvs.write(str('WIFI_PWD'), WIFI_PWD)
  #print(smartconfig.geMt_phoneip())
  smartconfig.stop()
  
def setup():
  global image0 
  global image_valid
  
  image0 = M5Img(0, 0, "res/default.jpg", True)

  wlan = network.WLAN(network.STA_IF)
  wlan.active(False)
  wlan.active(True)
  
  if nvs.read_str('WIFI_SSID'):
    WIFI_SSID = nvs.read_str('WIFI_SSID')
    WIFI_PWD = nvs.read_str('WIFI_PWD')
  else:
    smartconfig()

  try:
    print("Connecting to "+ WIFI_SSID + "...")    
    wlan.connect(WIFI_SSID, WIFI_PWD)
    print("Connected Succesfully")
    setScreenColor(0x33ff33)
  except Exception as e:
    setScreenColor(0xff0000)
  image_valid = True

def buttonB_wasPressed():
  error_next()

def buttonB_wasDoublePress():
  global mute
  mute = not mute
  
def buttonC_wasPressed():
  wlan = network.WLAN(network.STA_IF)
  wlan.disconnect()
  print("disconnected!")
  smartconfig()
  
def loop():
  # Hold the button to change image carrousel
  btnA.wasPressed(buttonA_wasPressed)
  btnB.wasPressed(buttonB_wasPressed)
  btnB.wasDoublePress(buttonB_wasDoublePress)
  btnC.wasPressed(buttonC_wasPressed)
  

setup()
while True:                        
  # async operations still not running on M5Stack      
  set_image()  
  loop()          
 
