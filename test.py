from Tello import Tello
from time import sleep
import cv2
from threading import Thread

def stream(bot,cap):
    while bot.stream_on:
        cv2.imshow("id drone", cap.frame)
        k = cv2.waitKey(1)
    cv2.destroyAllWindows()


def main():
    bot = Tello(clear=True)
    bot.connect()
    rc = bot.send_rc_control
    
    cap = bot.get_frame_read()
    
    Thread(target = stream,args=[bot,cap]).start()
    bot.takeoff()
    rc()
    rc(yaw_velocity=60)
    sleep(2)
    
    print(bot.battery)
    bot.end()
    
if __name__ == "__main__":
    main()

