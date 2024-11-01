# M5Stack-IpCameraViewer

Micropython firmware to remotely access security camera base on jpeg streaming using M5Stack

![3dgifmaker26394](https://github.com/user-attachments/assets/5a1c837d-de8d-467a-ad04-70345c418f27)


## How it works
Module has a list of streaming urls and show the video like a carousel. (Hold the A button until the images change)

## Requirements

- PHP app to resize frames
- UI Flow (> v2.1.6

## Instructions

- Open python file according to UIFlow version (UIFlow 1 uses smartconfig to wifi setup)
- Fill the WIFI settings `WIFI_SSID` and `WIFI_PWD`
- Fill the images list `images_dict = ["http://45.237.128.165:8088/shot.jpg?rnd=343590",]`
- Use Xampp or any other PHP host to run the index.php file on localhost
- Fill the resize endpoint `RESIZE_HOST = "http://192.168.0.181"`
- Use UI Flow to upload 404.jpg to the module in `res/img/404.jpg` path
- Use UI Flow to upload the firmware to the module

## Next steps

- Change to rtsp protocol
- Use opencv
- Remove php app dependency
- scrap directory lising to get camera urls 
- Add menu

Inpired by https://gainsira.medium.com/building-a-tiny-earth-e1e692d76635
