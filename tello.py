# coding=utf-8
import logging, socket , cv2
from time import time , sleep
from threading import Thread
from .utils import *
from os import _exit , system
from asyncio import sleep as _sleep


class Tello:    
    UDP_IP = '192.168.10.1'
    UDP_PORT = 8889
    RESPONSE_TIMEOUT = 7  # in seconds
    TIME_BTW_COMMANDS = 2  # in seconds
    TIME_BTW_RC_CONTROL_COMMANDS = 1.5  # in seconds
    RETRY_COUNT = 3
    last_received_command = time()
    HANDLER = logging.StreamHandler()
    FORMATTER = logging.Formatter('%(filename)s - %(lineno)d - %(message)s')
    HANDLER.setFormatter(FORMATTER)
    LOGGER = logging.getLogger('sajjad')
    LOGGER.addHandler(HANDLER)
    LOGGER.setLevel(logging.INFO)
    VS_UDP_IP = '0.0.0.0'
    VS_UDP_PORT = 11111
    STATE_UDP_PORT = 8890
    cap = None
    background_frame_read = None
    stream_on = False
    is_flying = False
    is_connected = False
    # Tello state
    pitch = -1
    roll = -1
    yaw = -1
    speed_x = -1
    speed_y = -1
    speed_z = -1
    temperature_lowest = -1
    temperature_highest = -1
    distance_tof = -1
    height = -1
    battery = -1
    barometer = -1.0
    flight_time = -1.0
    acceleration_x = -1.0
    acceleration_y = -1.0
    acceleration_z = -1.0
    attitude = {'pitch': -1, 'roll': -1, 'yaw': -1}
    
    def __init__(self,host: str ='192.168.10.1',port: int=8889,enable_exceptions: bool =True,retry_count : int=3 , debug : bool = True,clear : bool = False):
        if clear:
            system("clear")
        else:
            print("\n"*3)
        self.clientSocket = None
        self.clientSocket = None
        self.address = (host, port)
        self.response = None
        self.response_state = None  # to attain the response of the states
        self.stream_on = False
        self.enable_exceptions = enable_exceptions
        self.retry_count = retry_count
        self.debug = debug
        
        
    def run_udp_receiver(self):
        while self.is_connected:
            try:
                self.response, _ = self.clientSocket.recvfrom(1024)  # buffer size is 1024 bytes
            except Exception as e:
                if self.debug and self.is_connected: self.LOGGER.error(e)
                break

    def get_states(self):
        while self.is_connected:
            try:
                self.response_state, _ = self.stateSocket.recvfrom(256)
                if self.response_state != 'ok':
                    self.response_state = self.response_state.decode('ASCII')
                    list = self.response_state.replace(';', ':').split(':')
                    self.pitch = int(list[1])
                    self.roll = int(list[3])
                    self.yaw = int(list[5])

                    
                    self.speed_x = int(list[7])
                    self.speed_y = int(list[9])
                    self.speed_z = int(list[11])
                    self.temperature_lowest = int(list[13])
                    self.temperature_highest = int(list[15])
                    self.distance_tof = int(list[17])
                    self.height = int(list[19])
                    self.battery = int(list[21])
                    self.barometer = float(list[23])
                    self.flight_time = float(list[25])
                    self.acceleration_x = float(list[27])
                    self.acceleration_y = float(list[29])
                    self.acceleration_z = float(list[31])
                    self.attitude = {'pitch': int(list[1]), 'roll': int(list[3]), 'yaw': int(list[5])}
            except Exception as e:
                if self.debug and self.is_connected:
                    self.LOGGER.error(e)
                    self.LOGGER.error(f"Response was is {self.response_state}")
                break

    def get_udp_video_address(self):
        return 'udp://' + self.VS_UDP_IP + ':' + str(self.VS_UDP_PORT)  # + '?overrun_nonfatal=1&fifo_size=5000'

    def get_video_capture(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.get_udp_video_address())

        if not self.cap.isOpened():
            self.cap.open(self.get_udp_video_address())

        return self.cap

    def get_frame_read(self):
        if not self.stream_on :
            self.streamon()
        if self.background_frame_read is None:
            self.background_frame_read = BackgroundFrameRead(self, self.get_udp_video_address()).start()
        return self.background_frame_read

    def stop_video_capture(self):
        return self.streamoff()

    @accepts(command=str, timeout=int)
    def send_command_with_return(self, command, timeout=RESPONSE_TIMEOUT):
        diff = time() * 1000 - self.last_received_command
        if diff < self.TIME_BTW_COMMANDS:
            sleep(diff)

        if self.debug:
            self.LOGGER.info('Send command: ' + command)
        timestamp = int(time() * 1000)

        self.clientSocket.sendto(command.encode('utf-8'), self.address)

        while self.response is None:
            if (time() * 1000) - timestamp > timeout * 1000:
                if self.debug : self.LOGGER.warning('Timeout exceed on command ' + command)
                return False

        try:
            response = self.response.decode('utf-8').rstrip("\r\n")
        except UnicodeDecodeError as e:
            if self.debug and self.is_connected: self.LOGGER.error(e)
            return None

        if self.debug:
            self.LOGGER.info(f'Response {command}: {response}')

        self.response = None

        self.last_received_command = time() * 1000
        return response






    @accepts(command=str, timeout=int)
    async def _send_command_with_return(self, command, timeout=RESPONSE_TIMEOUT):
        diff = time() * 1000 - self.last_received_command
        if diff < self.TIME_BTW_COMMANDS:
            await _sleep(diff)

        if self.debug:
            self.LOGGER.info('Send command: ' + command)
        timestamp = int(time() * 1000)

        self.clientSocket.sendto(command.encode('utf-8'), self.address)

        while self.response is None:
            if (time() * 1000) - timestamp > timeout * 1000:
                if self.debug : self.LOGGER.warning('Timeout exceed on command ' + command)
                return False

        try:
            response = self.response.decode('utf-8').rstrip("\r\n")
        except UnicodeDecodeError as e:
            if self.debug and self.is_connected: self.LOGGER.error(e)
            return None

        if self.debug:
            self.LOGGER.info(f'Response {command}: {response}')

        self.response = None

        self.last_received_command = time() * 1000
        return response

    @accepts(command=str)
    def send_command_without_return(self, command):
        self.clientSocket.sendto(command.encode('utf-8'), self.address)
        if self.debug :
            self.LOGGER.info('Send command (no expect response): ' + command)

    @accepts(command=str, timeout=int)
    def send_control_command(self, command, timeout=RESPONSE_TIMEOUT):
        response = None
        for i in range(self.retry_count):
            response = self.send_command_with_return(command, timeout=timeout)
            if response == 'OK' or response == 'ok':
                return True
        return self.return_error_on_send_command(command, response, self.enable_exceptions)
    

    @accepts(command=str, timeout=int)
    async def _send_control_command(self, command, timeout=RESPONSE_TIMEOUT):
        response = None
        for i in range(self.retry_count):
            response = await self._send_command_with_return(command, timeout=timeout)
            if response == 'OK' or response == 'ok':
                return True
        return self.return_error_on_send_command(command, response, self.enable_exceptions)



    @accepts(command=str,)
    def send_read_command(self, command):
        response = self.send_command_with_return(command)

        try:
            response = str(response)
        except TypeError as e:
            if self.debug and self.is_connected: self.LOGGER.error(e)

        if ('error' not in response) and ('ERROR' not in response) and ('False' not in response):
            if response.isdigit():
                return int(response)
            else:
                try:
                    return float(response)  # isdigit() is False when the number is a float(barometer)
                except ValueError:
                    return response
        else:
            return self.return_error_on_send_command(command, response, self.enable_exceptions)

    def return_error_on_send_command(self, command, response, enable_exceptions):
        msg = 'Command ' + command + ' was unsuccessful. Message: ' + str(response)
        if enable_exceptions:
            raise Exception(msg)
        else:
            if self.debug:
                self.LOGGER.error(msg)
            return False
            

    def checker(self) :
        def check(key):
            if "name" in dir(key):
                if key.name == "esc" :
                    if self.is_connected:
                        self.end()
                    print("bye")
                    _exit(0)
            else:
                if key.char == "q" :
                    if self.is_connected:
                        self.end()
                    print("bye")
                    _exit(0)
        with Listener(on_press = check) as listener:   
            listener.join()
    
    def connect(self):
        input("___press enter to start___\n")
        if not self.is_connected:
            if not self.clientSocket:
                self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.clientSocket.bind(('', self.UDP_PORT))  # For UDP response (receiving data)
            self.stateSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            self.stateSocket.bind(('', self.STATE_UDP_PORT))  # for accessing the states of Tello
            self.is_connected = True
            thread1 = Thread(target=self.run_udp_receiver)
            thread2 = Thread(target=self.get_states)
            thread1.daemon = True
            thread2.daemon = True
            thread1.start()
            thread2.start()
            self.is_connected = self.send_control_command("command")
            return self.is_connected
        else: 
            return print("tello is already connected")

    def takeoff(self):
        if self.send_control_command("takeoff", timeout=30):
            self.is_flying = True
            return True
        else:
            return False

    def land(self):
        if self.send_control_command("land"):
            self.is_flying = False
            return True
        else:
            return False

    def streamon(self):
        result = self.send_control_command("streamon")
        if result is True:
            self.stream_on = True
        return result

    def streamoff(self):
        result = self.send_control_command("streamoff")
        if result is True:
            self.stream_on = False
        return result

    def emergency(self):
        return self.send_control_command("emergency")
    def stop(self):
        return self.send_control_command("stop")
    @accepts(direction=str, x=int)
    def move(self, direction, x):
        return self.send_control_command(direction + ' ' + str(x))

    @accepts(x=int)
    def move_up(self, x):
        return self.move("up", x)

    @accepts(x=int)
    def move_down(self, x):
        return self.move("down", x)

    @accepts(x=int)
    def move_left(self, x):
        return self.move("left", x)

    @accepts(x=int)
    def move_right(self, x):
        return self.move("right", x)

    @accepts(x=int)
    def move_forward(self, x):
        return self.move("forward", x)

    @accepts(x=int)
    def move_back(self, x):
        return self.move("back", x)

    @accepts(x=int)
    def rotate_clockwise(self, x):
        return self.send_control_command("cw " + str(x))
    
    @accepts(x=int)
    async def _rotate_clockwise(self, x):
        return await self._send_control_command("cw " + str(x))

    @accepts(x=int)
    def rotate_counter_clockwise(self, x):
        return self.send_control_command("ccw " + str(x))

    @accepts(x=str)
    def flip(self, direction):
        return self.send_control_command("flip " + direction)

    def flip_left(self):
        return self.flip("l")

    def flip_right(self):
        return self.flip("r")

    def flip_forward(self):
        return self.flip("f")

    def flip_back(self):
        return self.flip("b")

    @accepts(x=int, y=int, z=int, speed=int)
    def go_xyz_speed(self, x, y, z, speed):
        return self.send_command_without_return('go %s %s %s %s' % (x, y, z, speed))

    @accepts(x1=int, y1=int, z1=int, x2=int, y2=int, z2=int, speed=int)
    def curve_xyz_speed(self, x1, y1, z1, x2, y2, z2, speed):
        return self.send_command_without_return('curve %s %s %s %s %s %s %s' % (x1, y1, z1, x2, y2, z2, speed))

    @accepts(x=int, y=int, z=int, speed=int, mid=int)
    def go_xyz_speed_mid(self, x, y, z, speed, mid):
        return self.send_control_command('go %s %s %s %s m%s' % (x, y, z, speed, mid))

    @accepts(x1=int, y1=int, z1=int, x2=int, y2=int, z2=int, speed=int, mid=int)
    def curve_xyz_speed_mid(self, x1, y1, z1, x2, y2, z2, speed, mid):
        return self.send_control_command('curve %s %s %s %s %s %s %s m%s' % (x1, y1, z1, x2, y2, z2, speed, mid))

    @accepts(x=int, y=int, z=int, speed=int, yaw=int, mid1=int, mid2=int)
    def go_xyz_speed_yaw_mid(self, x, y, z, speed, yaw, mid1, mid2):
        return self.send_control_command('jump %s %s %s %s %s m%s m%s' % (x, y, z, speed, yaw, mid1, mid2))

    def enable_mission_pads(self):
        return self.send_control_command("mon")

    def disable_mission_pads(self):
        return self.send_control_command("moff")

    def set_mission_pad_detection_direction(self, x):
        return self.send_control_command("mdirection " + str(x))

    @accepts(x=int)
    def set_speed(self, x):
        return self.send_control_command("speed " + str(x))

    last_rc_control_sent = 0

    @accepts(left_right_velocity=int, forward_backward_velocity=int, up_down_velocity=int, yaw_velocity=int)
    def send_rc_control(self, left_right_velocity = 0 , forward_backward_velocity = 0, up_down_velocity = 0, yaw_velocity = 0):
        if not (int(time() * 1000) - self.last_rc_control_sent < self.TIME_BTW_RC_CONTROL_COMMANDS) :
            self.last_rc_control_sent = int(time() * 1000)
            return self.send_command_without_return('rc %s %s %s %s' % (self.round_to_100(left_right_velocity),
            self.round_to_100(forward_backward_velocity),self.round_to_100(up_down_velocity),self.round_to_100(yaw_velocity)))

    @accepts(x=int)
    def round_to_100(self, x):
        if x > 100:
            return 100
        elif x < -100:
            return -100
        else:
            return x

    def set_wifi_credentials(self, ssid, password):
        return self.send_control_command('wifi %s %s' % (ssid, password))

    def connect_to_wifi(self, ssid, password):
        return self.send_control_command('ap %s %s' % (ssid, password))

    def get_speed(self):
        return self.send_read_command('speed?')

    def get_battery(self):
        return self.send_read_command('battery?')

    def get_flight_time(self):
        return self.send_read_command('time?')

    def get_height(self):
        return self.send_read_command('height?')

    def get_temperature(self):
        return self.send_read_command('temp?')

    def get_attitude(self):
        r = self.send_read_command('attitude?').replace(';', ':').split(':')
        return dict(zip(r[::2], [int(i) for i in r[1::2]]))  # {'pitch': xxx, 'roll': xxx, 'yaw': xxx}

    def get_barometer(self):
        return self.send_read_command('baro?')

    def get_distance_tof(self):
        return self.send_read_command('tof?')

    def get_wifi(self):
        return self.send_read_command('wifi?')

    def get_sdk_version(self):
        return self.send_read_command('sdk?')

    def get_serial_number(self):
        return self.send_read_command('sn?')

    def end(self):
        if self.is_flying:
            self.land()
        if self.stream_on:
            self.streamoff()
        if not self.background_frame_read == None:
            self.background_frame_read.stop()
        if not self.cap == None:
            self.cap.release()
        if self.is_connected :
            self.is_connected = False
        sleep(0.1)
        try :
            self.clientSocket.close()
            self.stateSocket.close()
        except: pass
        self.clientSocket = None

    def __del__(self):
        self.end()


class BackgroundFrameRead:
    def __init__(self, tello, address):
        tello.cap = cv2.VideoCapture(address)
        self.cap = tello.cap

        if not self.cap.isOpened():
            self.cap.open(address)

        self.grabbed, self.frame = self.cap.read()
        self.stopped = False

    def start(self):
        _thread = Thread(target=self.update_frame, args=())
        _thread.daemon = True
        _thread.start()
        return self

    def update_frame(self):
        while not self.stopped:
            if not self.grabbed or not self.cap.isOpened():
                self.stop()
            else:
                (self.grabbed, self.frame) = self.cap.read()

    def stop(self):
        self.stopped = True