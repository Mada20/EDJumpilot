import cv2
import ctypes
import pynput
from pynput.keyboard import Key, Listener
import pytesseract
import time
import numpy as np
from enum import Enum
from PIL import ImageGrab
from threading import Timer
from random import randint


##### options #####
debug = False

### refuel options ###
min_refuel = 90  # min width of fuel when can be refuel
# crop options where is star name #O
can_refuel_crop_x1 = 85
can_refuel_crop_x2 = 120
can_refuel_crop_y1 = 895
can_refuel_crop_y2 = 920
# crop options where is fuel info #
need_refuel_crop_x1 = 1650
need_refuel_crop_x2 = 1850
need_refuel_crop_y1 = 888
need_refuel_crop_y2 = 950

### radar options ####
margin = 10  # margin of error
move_pause = 0.2  # rotate click pause - it's time of keys pressed
# crop options where radar #
radar_crop_x1 = 670
radar_crop_x2 = 800
radar_crop_y1 = 760
radar_crop_y2 = 960

### scanning options ###
scan_surface_time = 8
scan_system_time = 12

### jump options ###
jump_load_time = 12
# crop options where is jump info #
in_jump_crop_x1 = 1120
in_jump_crop_x2 = 1150
in_jump_crop_y1 = 870
in_jump_crop_y2 = 890

### danger zone options ###
# crop options of danger zone #
danger_zone_crop_x1 = 160
danger_zone_crop_x2 = 1760
danger_zone_crop_y1 = 0
danger_zone_crop_y2 = 700

### avoid options ###
# center of avoid #
avoid_center_x = 800
avoid_center_y = 350
avoid_speed_slow = 0.5  # standard avoid speed - it's time of keys pressed
avoid_speed_fast = 2  # avoid speed after refuel - it's time of keys pressed

### menu options ###
# crop options where is menu after star choose #
select_menu_x1 = 410 
select_menu_x2 = 520
select_menu_y1 = 535
select_menu_y2 = 565
###################

### button options ###
button_startstop = Key.f5
button_debug = Key.f6
button_jump = Key.f7
button_end = Key.f8


# input configurations and classes
SendInput = ctypes.windll.user32.SendInput
UINT = ctypes.c_uint
SendInput.restype = UINT
SendInput.argtypes = [UINT, ctypes.c_void_p, ctypes.c_int]


# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

# Actuals Functions


def press_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def release_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, hexKeyCode, 0x0008 | 0x0002,
                        0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def click_keys(keys, t):
    for key in keys:
        press_key(key)

    time.sleep(t)

    for key in keys:
        release_key(key)

class Buttons:  # http://www.gamespp.com/directx/directInputKeyboardScanCodes.html
    W = 0x11  # increase throttle / ui panel up
    S = 0x1F  # ui panel down
    D = 0x20  # ui panel right
    B = 0x30  # throttle 75%
    C = 0x2E  # throttle 25%
    V = 0x2F  # throttle 0%
    T = 0x14  # target next system in route
    M = 0x32  # hyperspace jump
    BUTTON_1 = 0x02  # target panel
    SPACE = 0x39  # ui panel select
    # NP - number pad
    NP_2 = 0x50  # pitch down
    NP_8 = 0x48  # pitch up
    NP_4 = 0x4B  # yaw left
    NP_6 = 0x4D  # yaw right
    NP_P = 0x4E  # primary fire (discovery scanner)


class State(Enum):
    INIT = 0
    RUN = 1
    CHECK_REFUEL = 2
    REFUELING = 3
    AVOID = 4
    CHECK_DANGER_ZONE = 5
    GO = 6
    JUMP = 7
    JUMPING = 8
    JUMPED = 9
    END = -1
    STOP = -2


def join_images(image1, image2, horizontaly=False):
    h1, w1 = image1.shape[:2]
    h2, w2 = image2.shape[:2]
    if not horizontaly:
        vis = np.zeros((max(h1, h2), w1+w2, 3), np.uint8)
        vis[:h1, :w1, :3] = image1
        vis[:h2, w1:w1+w2, :3] = image2
    else:
        vis = np.zeros((h1+h2, max(w1, w2), 3), np.uint8)
        vis[:h1, :w1, :3] = image1
        vis[h1:h1+h2, :w2, :3] = image2
    return vis


def get_frame():
    img = ImageGrab.grab()
    img_numpy = np.array(img)
    frame = cv2.cvtColor(img_numpy, cv2.COLOR_BGR2RGB)
    return frame


def rand_rotate(time):
    pos = randint(1, 4)
    key = None
    if pos == 1:
        key = Buttons.NP_2
    elif pos == 2:
        key = Buttons.NP_4
    elif pos == 3:
        key = Buttons.NP_6
    elif pos == 4:
        key = Buttons.NP_8

    click_keys([key], time)


def center_ship(back=False):
    global debug
    global margin
    global move_pause
    global radar_crop_x1
    global radar_crop_x2
    global radar_crop_y1
    global radar_crop_y2

    frame = get_frame()
    frame = frame[radar_crop_y1:radar_crop_y2, radar_crop_x1:radar_crop_x2]
    frame = cv2.resize(frame, (0, 0), fx=2, fy=2.2)

    imshow = None
    if debug:
        imshow = frame.copy()

    # get blue mask
    mask = frame.copy()
    mask[:, :, 0] = 0
    mask[:, :, 1] = 0
    lower_mask = np.array([0, 0, 252])
    upper_mask = np.array([0, 0, 255])
    mask = cv2.inRange(mask, lower_mask, upper_mask)
    mask = cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=10)
    mask = cv2.bitwise_not(mask)

    # get circle
    circles = cv2.HoughCircles(mask, cv2.HOUGH_GRADIENT, 4, 50, param1=100, param2=30, minRadius=62, maxRadius=62)

    center = None
    radius = None
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for c in circles:
            circle = c[0]
            center = (circle[0] - 5, circle[1] - 5)
            radius = circle[2]

    if debug:
        mask2color = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        if center is not None and radius is not None:
            cv2.circle(imshow, center, radius, (0, 255, 0), 1)
            cv2.circle(imshow, center, 4, (0, 255, 0), -1)
            cv2.circle(mask2color, center, radius, (0, 0, 255), 1)
            cv2.circle(mask2color, center, 4, (0, 0, 255), -1)
        imshow = join_images(imshow, mask2color)

    cx = None
    cy = None

    # get position
    point_position = 0
    if center is not None and radius is not None:
        frame = frame[center[1]-60:center[1] + 60, center[0]-60:center[0]+60]

        crop = frame.copy()
        crop[:, :, 1] = 0
        crop[:, :, 2] = 0

        if debug:
            imshow = join_images(imshow, crop)

        # get front point
        lower_mask = np.array([254, 0, 0])
        upper_mask = np.array([255, 0, 0])
        mask = cv2.inRange(crop, lower_mask, upper_mask)
        if mask is not None:
            mask = cv2.resize(mask, (0, 0), fx=2, fy=2)
            _, thresh = cv2.threshold(mask, 127, 255, 0)
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.erode(thresh.copy(), kernel, iterations=3)
            _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) > 0:
                cnt = max(contours, key=cv2.contourArea)
                M = cv2.moments(cnt)
                if M['m00'] > 0:
                    cx = int(M['m10']/M['m00'])
                    cy = int(M['m01']/M['m00'])
                    point_position = 1
            else:
                # get back point
                lower_mask = np.array([240, 0, 0])
                upper_mask = np.array([255, 0, 0])
                mask = cv2.inRange(crop, lower_mask, upper_mask)
                if mask is not None:
                    mask = cv2.resize(mask, (0, 0), fx=2, fy=2)
                    _, thresh = cv2.threshold(mask, 0, 255, 0)
                    mask = cv2.dilate(thresh, kernel, iterations=4)

                    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if len(contours) > 0:
                        cnt = max(contours, key=cv2.contourArea)
                        M = cv2.moments(cnt)
                        if M['m00'] > 0:
                            cx = int(M['m10']/M['m00'])
                            cy = int(M['m01']/M['m00'])
                            point_position = 2
                else:
                    print 'ERROR: MASK IS NULL!'

            if debug:
                if cx is not None and cy is not None:
                    color = (0, 255, 0)
                    if point_position is 2:
                        color = (0, 0, 255)
                    frame = cv2.resize(frame, (0, 0), fx=2, fy=2)
                    cv2.circle(frame, (cx, cy), 2, color, 4)
                    imshow = join_images(imshow, join_images(frame, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), True))
                else:
                    imshow = join_images(imshow, crop)
        else:
            print 'ERROR: MASK IS NULL!'
    else:
        print 'ERROR: CIRCLE NOT FOUND'

    if debug:
        cv2.imshow('Debug', imshow)

    # move
    keys = []
    if cx is not None and cy is not None:
        if (point_position > 0):
            width, height = cv2.resize(crop, (0, 0), fx=2, fy=2).shape[:2]
            deltaX = width/2 - cx
            deltaY = height/2 - cy

            if not back:
                if point_position == 1:
                    if deltaX < -margin:
                        keys.append(Buttons.NP_6)
                    elif deltaX > margin:
                        keys.append(Buttons.NP_4)

                    if deltaY < -margin:
                        keys.append(Buttons.NP_2)
                    elif deltaY > margin:
                        keys.append(Buttons.NP_8)

                elif point_position == 2:
                    if deltaX < -margin:
                        keys.append(Buttons.NP_6)
                    else:
                        keys.append(Buttons.NP_4)

                    if deltaY < -margin:
                        keys.append(Buttons.NP_2)
                    else:
                        keys.append(Buttons.NP_8)
            else:
                if point_position == 1:
                    if deltaX < -margin:
                        keys.append(Buttons.NP_4)
                    else:
                        keys.append(Buttons.NP_6)

                    if deltaY < -margin:
                        keys.append(Buttons.NP_8)
                    else:
                        keys.append(Buttons.NP_2)

                elif point_position == 2:
                    if deltaX < -margin:
                        keys.append(Buttons.NP_4)
                    elif deltaX > margin:
                        keys.append(Buttons.NP_6)

                    if deltaY < -margin:
                        keys.append(Buttons.NP_8)
                    elif deltaY > margin:
                        keys.append(Buttons.NP_2)

            click_keys(keys, move_pause)

    return len(keys) == 0


def is_refueling():
    global debug
    global need_refuel_crop_x1
    global need_refuel_crop_x2
    global need_refuel_crop_y1
    global need_refuel_crop_y2

    frame = get_frame()
    crop = frame[need_refuel_crop_y1:need_refuel_crop_y2, need_refuel_crop_x1:need_refuel_crop_x2]

    lower_mask = np.array([240, 240, 240])
    upper_mask = np.array([255, 255, 255])
    mask = cv2.inRange(crop, lower_mask, upper_mask)

    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if debug:
        cv2.imshow('Debug', join_images(crop, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)))

    return len(contours) > 0


def need_refuel():
    global debug
    global min_refuel
    global need_refuel_crop_x1
    global need_refuel_crop_x2
    global need_refuel_crop_y1
    global need_refuel_crop_y2

    frame = get_frame()
    crop = frame[need_refuel_crop_y1:need_refuel_crop_y2, need_refuel_crop_x1:need_refuel_crop_x2]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    kernel = np.ones((4, 4), np.uint8)
    dilation = cv2.dilate(gray, kernel, iterations=1)
    erosion = cv2.erode(dilation, kernel, iterations=2)

    _, contours, _ = cv2.findContours(erosion, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    w = 0
    contour = None
    if len(contours) > 0:
        contour = max(contours, key=cv2.contourArea)
        cv2.drawContours(crop, [contour], 0, (255, 255, 0), 1)
        _, _, w, _ = cv2.boundingRect(contour)

    if debug:
        cv2.imshow('Debug', join_images(crop, cv2.cvtColor(erosion, cv2.COLOR_GRAY2RGB)))

    return min_refuel > w


def select_first_star():
    global debug
    global select_menu_x1
    global select_menu_x2
    global select_menu_y1
    global select_menu_y2

    result = False

    click_keys([Buttons.BUTTON_1], 0.1)
    time.sleep(1)

    click_keys([Buttons.D], 0.1)

    click_keys([Buttons.S], 0.1)
    click_keys([Buttons.W], 1)

    click_keys([Buttons.SPACE], 0.1)
    time.sleep(1)

    frame = get_frame()
    crop = frame[select_menu_y1:select_menu_y2, select_menu_x1:select_menu_x2]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    text = None
    try:
        text = pytesseract.image_to_string(gray)
        try:
            print 'SELECTED STAR TEXT: ' + text
        except:
            print 'WARNING: PROBLEM WITH TEXT PRINT'
    except:
        print 'CAN\' FIND TEXT ON STAR SELECT...'

    if text is not None:
        text = text.upper()
        if "UN" in text:
            click_keys([Buttons.W], 0.1)
            click_keys([Buttons.SPACE], 0.1)
            result = True
        elif "LOCK" in text:
            click_keys([Buttons.SPACE], 0.1)
            result = True

    if debug:
        cv2.imshow('Debug', gray)

    click_keys([Buttons.BUTTON_1], 0.1)
    return result


def get_danger_zone_mask():
    global danger_zone_crop_x1
    global danger_zone_crop_x2
    global danger_zone_crop_y1
    global danger_zone_crop_y2

    frame = get_frame()

    crop = frame[danger_zone_crop_y1:danger_zone_crop_y2, danger_zone_crop_x1:danger_zone_crop_x2]

    lower_mask = np.array([60, 60, 60])
    upper_mask = np.array([255, 255, 255])
    mask = cv2.inRange(crop, lower_mask, upper_mask)

    kernel = np.ones((8, 8), np.uint8)
    erosion = cv2.erode(mask, kernel, iterations=4)
    dilation = cv2.dilate(erosion, kernel, iterations=20)

    mask = dilation

    return mask, crop


def in_danger_zone():
    global debug

    mask, crop = get_danger_zone_mask()

    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    w = 0
    h = 0
    if len(contours) > 0:
        contour = max(contours, key=cv2.contourArea)
        if debug:
            cv2.drawContours(crop, [contour], 0, (255, 255, 0), 1)
        (_, _), (width, height), _ = cv2.minAreaRect(contour)
        w = width
        h = height

    if debug:
        cv2.imshow('Debug', cv2.resize(join_images(crop, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), True), (0, 0), fx=0.5, fy=0.5))

    return w > 400 and h > 400


def avoid(last_keys=None, speed=1):
    global debug
    global avoid_center_x
    global avoid_center_y

    mask, crop = get_danger_zone_mask()

    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    M = None
    deltaX = 0
    deltaY = 0
    if len(contours) > 0:
        contour = max(contours, key=cv2.contourArea)

        if debug:
            cv2.drawContours(crop, [contour], 0, (255, 255, 0), 1)

        M = cv2.moments(contour)
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        cv2.circle(crop, (cX, cY), 7, (0, 0, 0), -1)
        deltaX = avoid_center_x - cX
        deltaY = avoid_center_y - cY

        if deltaX < 5 and deltaX > -5:
            deltaX = 0
        if deltaY < 5 and deltaY > -5:
            deltaY = 0

    keys = []
    if last_keys is not None:
        keys = last_keys
    elif M is not None:
        if deltaX <= 0:
            keys.append(Buttons.NP_4)

        elif deltaX > 0:
            keys.append(Buttons.NP_6)

        if deltaY >= 0:
            keys.append(Buttons.NP_2)

        if deltaY < 0:
            keys.append(Buttons.NP_8)

    if len(keys) > 0:
        click_keys(keys, speed)

    if debug:
        cv2.imshow('Debug', cv2.resize(join_images(crop, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), True), (0, 0), fx=0.5, fy=0.5))

    return M is not None, keys


def is_jumping():
    global debug
    global radar_crop_x1
    global radar_crop_x2
    global radar_crop_y1
    global radar_crop_y2

    frame = get_frame()
    crop = frame[radar_crop_y1:radar_crop_y2, radar_crop_x1:radar_crop_x2]

    lower_mask = np.array([200, 200, 200])
    upper_mask = np.array([255, 255, 255])
    mask = cv2.inRange(crop, lower_mask, upper_mask)

    kernel = np.ones((4, 4), np.uint8)
    dilation = cv2.dilate(mask, kernel, iterations=1)

    rows = dilation.shape[0]
    circles = cv2.HoughCircles(dilation, cv2.HOUGH_GRADIENT, 2,
                               rows / 8, param1=20, param2=50, minRadius=26, maxRadius=29)

    center = None
    radius = None
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for c in circles:
            circle = c[0]
            center = (circle[0], circle[1])
            radius = circle[2]

    # draw debug
    if debug:
        if center is not None and radius is not None:
            cv2.circle(crop, center, radius, (0, 0, 255), 5)
        cv2.imshow('Debug', join_images(
            crop, cv2.cvtColor(dilation, cv2.COLOR_GRAY2RGB)))

    return circles is not None and len(circles) > 0


def can_refuel():
    global debug
    global scan_surface_time
    global can_refuel_crop_x1
    global can_refuel_crop_x2
    global can_refuel_crop_y1
    global can_refuel_crop_y2

    result = False

    frame = get_frame()
    crop = frame[can_refuel_crop_y1:can_refuel_crop_y2, can_refuel_crop_x1:can_refuel_crop_x2]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    gray = cv2.resize(gray, (0, 0), fx=2, fy=2)
    gray = cv2.bitwise_not(gray)

    text = None
    try:
        text = pytesseract.image_to_string(gray)
    except:
        print 'CAN\'T FIND STAR TEXT...'

    star_type = None
    if text is not None:
        text = text[:1].upper()

        if "O" in text or "B" in text or "A" in text or "F" in text or "G" in text or "K" in text or "M" in text:
            star_type = text
            if debug:
                try:
                    print 'STAR TYPE IS: ' + text
                except:
                    print 'WARNING: PROBLEM WITH TEXT PRINT'
            result = True
        elif "S" in text or "UN" in text:
            if debug:
                try:
                    print 'STAR SCANNING, FOUNDED: ' + text
                except:
                    print 'WARNING: PROBLEM WITH TEXT PRINT'
            time.sleep(scan_surface_time)
        else:
            try:
                print 'WARNING, STAR TYPE FOUNDED: ' + text
            except:
                print 'WARNING: PROBLEM WITH TEXT PRINT'

    if debug:
        cv2.imshow('Debug', gray)

    return result, star_type


def is_in_jump():
    global debug
    global in_jump_crop_x1
    global in_jump_crop_x2
    global in_jump_crop_y1
    global in_jump_crop_y2

    frame = get_frame()
    crop = frame[in_jump_crop_y1:in_jump_crop_y2, in_jump_crop_x1:in_jump_crop_x2]

    lower_mask = np.array([250, 250, 250])
    upper_mask = np.array([255, 255, 255])
    mask = cv2.inRange(crop, lower_mask, upper_mask)

    kernel = np.ones((4, 4), np.uint8)
    dilation = cv2.dilate(mask, kernel, iterations=1)

    _, contours, _ = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if debug:
        cv2.imshow('Debug', dilation)

    return len(contours) > 0


def end_scan():
    print('END SCAN')
    release_key(Buttons.NP_P)


def start_scan():
    global scan_system_time
    print 'START SCAN'
    press_key(Buttons.NP_P)
    r = Timer(scan_system_time, end_scan)
    r.start()


start = True
star = False
last_back_keys = None
count = 0
refueling_count = 0
avoid_speed = 0.5
star_type = None
jump_started = False
fail_jumps = 0
state = State.INIT


def on_press(key):
    # listener keyboards
    global state
    global debug
    global button_startstop
    global button_debug
    global button_jump
    global button_end

    if key == button_startstop and state == State.INIT:
        state = State.RUN
    elif key == button_startstop:
        state = State.INIT
    elif key == button_debug:
        debug = not debug
    elif key == button_jump:
        state = State.JUMP
    elif key == button_end:
        state = State.END


listener = pynput.keyboard.Listener(on_press=on_press)
listener.start()


while(True):
    if state.value > 0:
        if start:
            print 'STARTED'
            start = False
            start_scan()
            select_first_star()
            time.sleep(1)
        if state == State.RUN:
            print 'RUN: ' + str(count)
            if center_ship():
                count += 1
            else:
                count = 0

            if count > 10:
                print 'RUN FINISHED'
                count = 0
                star = True
                state = State.CHECK_REFUEL
        elif state == State.CHECK_REFUEL:
            print 'CHECK REFUEL: ' + str(count)
            can, star_type = can_refuel()
            if can and need_refuel():
                count += 1
            else:
                count -= 1

            if count > 5:
                print 'START REFUEL'
                count = 0
                state = State.REFUELING
                avoid_speed = avoid_speed_fast
            elif count < -5:
                print 'NO NEED REFUEL'
                count = 0
                state = State.AVOID
                avoid_speed = avoid_speed_slow
        elif state == State.REFUELING:
            if is_refueling():
                print 'REFUELING: ' + str(refueling_count)
                refueling_count = 0
                check_refuel_count = 0
                click_keys([Buttons.V], 0.1)
            else:
                refueling_count += 1

            if refueling_count > 50:
                refueling_count = 50
                print 'CAN I GO TO STAR? ' + str(count)
                if need_refuel():
                    count += 1
                else:
                    count -= 1

                if count > 10:
                    print 'YES, GO TO STAR'
                    count = 0
                    click_keys([Buttons.C], 0.1)
                    center_ship()
                elif count < -10:
                    print 'NO, NO NEED REFUEL'
                    count = 0
                    refueling_count = 0
                    state = State.AVOID
        elif state == State.AVOID:
            print 'AVOID: ' + str(count)
            runned, last_back_keys = avoid(last_back_keys, avoid_speed)
            if runned:
                star = False
                count = 0
            else:
                count += 1
                last_back_keys = None

            if count > 10:
                print 'AVOIDED'
                count = 0

                if star or star_type is None:
                    print 'WARNING: TRY GO AWAY...'
                    rotate = 0
                    while(rotate < 5 and state.value > 0):
                        print 'WARNING: TRY GO AWAY: ' + str(rotate)
                        if not center_ship(True):
                            rotate = 0
                        else:
                            rotate += 1
                        cv2.waitKey(25)

                    star = False

                state = State.CHECK_DANGER_ZONE
        elif state == State.CHECK_DANGER_ZONE:
            print 'CHECK DANGER ZONE: ' + str(count)
            if in_danger_zone():
                print 'RAND ROTATE...'
                rand_rotate(5)
            else:
                count += 1
                click_keys([Buttons.C], 1)

            if is_refueling():
                print 'AUTO REFUELING'
                count = 5

            if count > 10:
                print 'DANGER ZONE CLEAR'
                count = 0
                click_keys([Buttons.W], 10)
                click_keys([Buttons.V], 0.1)
                state = State.GO
        elif state == State.GO:
            print 'GO GO GO!'
            click_keys([Buttons.T], 0.1)
            state = State.JUMP
        elif state == State.JUMP:
            print 'JUMP: ' + str(count)
            if not center_ship():
                count = 0
            else:
                count += 1

            if count > 5:
                print 'JUMPING!'
                count = 0
                if in_danger_zone():
                    state = State.AVOID
                else:
                    jump_started = False
                    click_keys([Buttons.M], 0.1)
                    state = State.JUMPING
        elif state == State.JUMPING:
            print 'JUMPING: ' + str(count)
            if is_jumping():
                if not jump_started:
                    jump_started = True
                    time.sleep(jump_load_time)
                    click_keys([Buttons.W], 2)
                count = 0
            else:
                count += 1
            if count > 100:
                count = 0
                if not jump_started:
                    print 'JUMP STOPPED!'
                    fail_jumps += 1
                    click_keys([Buttons.M], 0.1)
                    if fail_jumps > 5:
                        print 'PROBLEM WITH JUMP!'
                        state = State.STOP
                    else:
                        state = State.AVOID
                else:
                    print 'IN JUMP!'
                    fail_jumps = 0
                    state = State.JUMPED
            elif count is 0:
                center_ship()
        elif state == State.JUMPED:
            print 'JUMPED: ' + str(count)
            click_keys([Buttons.V], 0.1)
            if is_in_jump():
                count = 0
            else:
                count += 1

            if count > 10:
                print 'JUMP FINISHED!'
                count = 0
                start_scan()
                select_first_star()
                time.sleep(1)
                state = State.RUN
    else:
        cv2.destroyWindow('Debug')

    if state == State.END:
        cv2.destroyAllWindows()
        break

    cv2.waitKey(25)
