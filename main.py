import cv2
import time
import numpy as np

from enum import Enum
from threading import Timer
from random import randint
from pynput.keyboard import Key, Listener
import pytesseract

from controls import Buttons, press_key, release_key, click_keys
from utils import get_frame, join_images, show_images, match_template
from options import Anaconda as ship

##### options #####
debug = True
test = False

### button options ###
button_startstop = Key.f5
button_debug = Key.f6
button_jump = Key.f7
button_end = Key.f8


# states
class State(Enum):
    INIT = 0
    TURN_FORWARD = 1
    TURN_AROUND = 2
    CHECK_REFUEL = 3
    REFUELING = 4
    AVOID = 5
    AUTO_REFUEL = 6
    AUTO_REFUELING = 7
    GO = 8
    JUMP = 9
    JUMPING = 10
    JUMPED = 11
    END = -1
    STOP = -2


def center_ship(debug, opt, back=False):
    frame = get_frame()
    frame = frame[opt.radar_crop_y1:opt.radar_crop_y2, opt.radar_crop_x1:opt.radar_crop_x2]
    frame = cv2.resize(frame, (0, 0), fx=2, fy=2.2)

    debug_img = None
    if debug:
        debug_img = frame.copy()

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

    if debug_img is not None:
        mask2color = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        if center is not None and radius is not None:
            cv2.circle(debug_img, center, radius, (0, 255, 0), 1)
            cv2.circle(debug_img, center, 4, (0, 255, 0), -1)
            cv2.circle(mask2color, center, radius, (0, 0, 255), 1)
            cv2.circle(mask2color, center, 4, (0, 0, 255), -1)
        debug_img = join_images(debug_img, mask2color)

    cx = None
    cy = None

    # get position
    point_position = 0
    if center is not None and radius is not None:
        frame = frame[center[1]-60:center[1] + 60, center[0]-60:center[0]+60]

        crop = frame.copy()
        crop[:, :, 1] = 0
        crop[:, :, 2] = 0

        if debug_img is not None:
            debug_img = join_images(debug_img, crop)

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

            if debug_img is not None:
                if cx is not None and cy is not None:
                    color = (0, 255, 0)
                    if point_position is 2:
                        color = (0, 0, 255)
                    frame = cv2.resize(frame, (0, 0), fx=2, fy=2)
                    cv2.circle(frame, (cx, cy), 2, color, 4)
                    debug_img = join_images(debug_img, join_images(frame, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), True))
                else:
                    debug_img = join_images(debug_img, crop)
        else:
            print 'ERROR: MASK IS NULL!'
    else:
        print 'ERROR: CIRCLE NOT FOUND'        

    # move
    keys = []
    if cx is not None and cy is not None:
        if (point_position > 0):
            width, height = cv2.resize(crop, (0, 0), fx=2, fy=2).shape[:2]
            deltaX = width/2 - cx
            deltaY = height/2 - cy

            if not back:
                if point_position == 1:
                    if deltaX < -opt.margin:
                        keys.append(Buttons.NP_6)
                    elif deltaX > opt.margin:
                        keys.append(Buttons.NP_4)

                    if deltaY < -opt.margin:
                        keys.append(Buttons.NP_2)
                    elif deltaY > opt.margin:
                        keys.append(Buttons.NP_8)

                elif point_position == 2:
                    if deltaX < -opt.margin:
                        keys.append(Buttons.NP_6)
                    else:
                        keys.append(Buttons.NP_4)

                    if deltaY < -opt.margin:
                        keys.append(Buttons.NP_2)
                    else:
                        keys.append(Buttons.NP_8)
            else:
                if point_position == 1:
                    if deltaX < -opt.margin:
                        keys.append(Buttons.NP_4)
                    else:
                        keys.append(Buttons.NP_6)

                    if deltaY < -opt.margin:
                        keys.append(Buttons.NP_8)
                    else:
                        keys.append(Buttons.NP_2)

                elif point_position == 2:
                    if deltaX < -opt.margin:
                        keys.append(Buttons.NP_4)
                    elif deltaX > opt.margin:
                        keys.append(Buttons.NP_6)

                    if deltaY < -opt.margin:
                        keys.append(Buttons.NP_8)
                    elif deltaY > opt.margin:
                        keys.append(Buttons.NP_2)

            click_keys(keys, opt.move_time)

    return len(keys) == 0, debug_img


def is_refueling(debug, opt):
    frame = get_frame()
    crop = frame[opt.need_refuel_crop_y1:opt.need_refuel_crop_y2, opt.need_refuel_crop_x1:opt.need_refuel_crop_x2]

    lower_mask = np.array([240, 240, 240])
    upper_mask = np.array([255, 255, 255])
    mask = cv2.inRange(crop, lower_mask, upper_mask)

    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    debug_image = None
    if debug:
        debug_image = join_images(crop, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB))

    return len(contours) > 0, debug_image


def need_refuel(debug, opt):
    frame = get_frame()
    crop = frame[opt.need_refuel_crop_y1:opt.need_refuel_crop_y2, opt.need_refuel_crop_x1:opt.need_refuel_crop_x2]

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

    debug_image = None
    if debug:
        debug_image = join_images(crop, cv2.cvtColor(erosion, cv2.COLOR_GRAY2RGB))

    return opt.min_refuel > w, debug_image


def select_first_star(debug, opt):
    result = False

    click_keys([Buttons.BUTTON_1], 0.1)
    time.sleep(1)

    click_keys([Buttons.D], 0.1)

    click_keys([Buttons.S], 0.1)
    click_keys([Buttons.W], 1)

    click_keys([Buttons.SPACE], 0.1)
    time.sleep(1)

    frame = get_frame()
    crop = frame[opt.select_menu_y1:opt.select_menu_y2, opt.select_menu_x1:opt.select_menu_x2]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    if match_template(gray, 'images/unlock.png', 0.8):
        click_keys([Buttons.W], 0.1)
        click_keys([Buttons.SPACE], 0.1)
        result = True
    elif match_template(gray, 'images/lock.png', 0.85):
        click_keys([Buttons.SPACE], 0.1)
        result = True

    # pytesseract (todo: remove it later)
    #text = None
    #try:
    #    text = pytesseract.image_to_string(gray, config='tessedit_char_whitelist=CKLNOU')
    #    try:
    #        print 'SELECTED STAR TEXT: ' + text
    #    except:
    #        print 'WARNING: PROBLEM WITH TEXT PRINT'
    #except:
    #    print 'CAN\' FIND TEXT ON STAR SELECT...'

    #if text is not None:
    #    text = text.upper()
    #    if "UN" in text:
    #        click_keys([Buttons.W], 0.1)
    #        click_keys([Buttons.SPACE], 0.1)
    #        result = True
    #    elif "LOCK" in text:
    #        click_keys([Buttons.SPACE], 0.1)
    #        result = True

    debug_image = None
    if debug:
        debug_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    click_keys([Buttons.BUTTON_1], 0.1)
    return result, debug_image


def avoid(debug, opt, last_keys=None, speed=1):
    frame = get_frame()
    crop = frame[opt.danger_zone_crop_y1:opt.danger_zone_crop_y2, opt.danger_zone_crop_x1:opt.danger_zone_crop_x2]

    debug_image = None
    if debug:
        debug_image = crop

    lower_mask = np.array([60, 60, 60])
    upper_mask = np.array([255, 255, 255])
    mask = cv2.inRange(crop, lower_mask, upper_mask)

    kernel = np.ones((8, 8), np.uint8)
    erosion = cv2.erode(mask, kernel, iterations=4)
    dilation = cv2.dilate(erosion, kernel, iterations=20)

    mask = dilation

    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    M = None
    deltaX = 0
    deltaY = 0
    if len(contours) > 0:
        contour = max(contours, key=cv2.contourArea)

        if debug_image is not None:
            cv2.drawContours(debug_image, [contour], 0, (255, 255, 0), 1)

        M = cv2.moments(contour)
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        cv2.circle(crop, (cX, cY), 7, (0, 0, 0), -1)
        deltaX = opt.avoid_center_x - cX
        deltaY = opt.avoid_center_y - cY

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

    if debug_image is not None:
        debug_image = cv2.resize(join_images(crop, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), True), (0, 0), fx=0.5, fy=0.5)

    return M is not None, keys, debug_image


def is_jumping(debug, opt):
    frame = get_frame()
    crop = frame[opt.radar_crop_y1:opt.radar_crop_y2, opt.radar_crop_x1:opt.radar_crop_x2]

    lower_mask = np.array([200, 200, 200])
    upper_mask = np.array([255, 255, 255])
    mask = cv2.inRange(crop, lower_mask, upper_mask)

    kernel = np.ones((4, 4), np.uint8)
    dilation = cv2.dilate(mask, kernel, iterations=1)

    rows = dilation.shape[0]
    circles = cv2.HoughCircles(dilation, cv2.HOUGH_GRADIENT, 2, rows / 8, param1=20, param2=50, minRadius=26, maxRadius=29)

    center = None
    radius = None
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for c in circles:
            circle = c[0]
            center = (circle[0], circle[1])
            radius = circle[2]

    debug_image = None
    if debug:
        debug_image = crop
        if center is not None and radius is not None:
            cv2.circle(debug_image, center, radius, (0, 0, 255), 5)
        debug_image = join_images(crop, cv2.cvtColor(dilation, cv2.COLOR_GRAY2RGB))

    return circles is not None and len(circles) > 0, debug_image


def can_refuel(debug, opt, scan_surface_time):
    result = False

    frame = get_frame()
    crop = frame[opt.can_refuel_crop_y1:opt.can_refuel_crop_y2, opt.can_refuel_crop_x1:opt.can_refuel_crop_x2]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    gray = cv2.resize(gray, (0, 0), fx=2, fy=2)
    gray = cv2.bitwise_not(gray)

    star_type = None
    ignore_print = False
    if match_template(gray, 'images/sc.png', 0.85):
        print 'STAR IS SCANNED'
        star_type = 'S'
        time.sleep(scan_surface_time)
        ignore_print = True
    elif match_template(gray, 'images/m.png', 0.85):
        star_type = 'M'
        result = True
    elif match_template(gray, 'images/k.png', 0.85):
        star_type = 'K'
        result = True
    elif match_template(gray, 'images/g.png', 0.85):
        star_type = 'G'
        result = True
    elif match_template(gray, 'images/f.png', 0.85):
        star_type = 'F'
        result = True
    elif match_template(gray, 'images/a.png', 0.85):
        star_type = 'A'
        result = True
    elif match_template(gray, 'images/b.png', 0.85):
        star_type = 'B'
        result = True
    elif match_template(gray, 'images/0.png', 0.85):
        star_type = '0'
        result = True
    elif match_template(gray, 'images/un.png', 0.85):
        print 'STAR IS UNEXPLORED, WHY?'
        ignore_print = True

    if not ignore_print:
        if star_type is not None:
            print 'STAR TYPE IS ' + star_type
        else:
            print 'STAR TYPE IS UNKNOWN'


    ## pytesseract (todo: remove it later)
    #text = None
    #try:
    #    text = pytesseract.image_to_string(gray, config='tessedit_char_whitelist=ABFGKNOSU')
    #except:
    #    print 'CAN\'T FIND STAR TEXT...'

    #star_type = None
    #if text is not None:
    #    text = text[:1].upper()
    #    try:
    #        if "O" in text or "B" in text or "A" in text or "F" in text or "G" in text or "K" in text or "M" in text:
    #            star_type = text
    #            print 'STAR TYPE IS: ' + text
    #            result = True
    #        elif "S" in text:
    #            print 'STAR SCAN, FOUNDED: ' + text
    #            time.sleep(scan_surface_time)
    #        elif "U" in text:
    #            print 'STAR IS UNKNOWN, WHY?'
    #        else:
    #            if not text:
    #                print 'WARNING, STAR TYPE NOT FOUNDED: ' + text
    #            else:
    #                print 'STAR TYPE NOT FOUNDED: ' + text
    #    except:
    #        print 'WARNING: PROBLEM WITH TEXT IN STAR FINDING'

    debug_image = None
    if debug:
        debug_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    return result, star_type, debug_image


def is_in_jump(debug, opt):
    frame = get_frame()
    crop = frame[opt.in_jump_crop_y1:opt.in_jump_crop_y2, opt.in_jump_crop_x1:opt.in_jump_crop_x2]

    lower_mask = np.array([250, 250, 250])
    upper_mask = np.array([255, 255, 255])
    mask = cv2.inRange(crop, lower_mask, upper_mask)

    kernel = np.ones((4, 4), np.uint8)
    dilation = cv2.dilate(mask, kernel, iterations=1)

    _, contours, _ = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    debug_image = None
    if debug:
        debug_image = cv2.cvtColor(dilation, cv2.COLOR_GRAY2RGB)

    return len(contours) > 0, debug_image


def end_scan():
    print('END SCAN')
    release_key(Buttons.NP_P)


def start_scan(scan_system_time):
    print 'START SCAN'
    press_key(Buttons.NP_P)
    r = Timer(scan_system_time, end_scan)
    r.start()


def jump_fail():
    global state
    global count
    global jump_started

    print 'ERROR: JUMP FAILURE!!!'

    click_keys([Buttons.M], 0.1)
    click_keys([Buttons.V], 0.1)

    jump_started = False
    count = 0
    state = State.JUMP


start = True
is_star_centered = False
last_back_keys = None
count = 0
refueling_count = 0
avoid_speed = 0.5
star_type = None
jump_started = False
fail_jumps = 0
jump_timer = None
state = State.INIT


def reset():
    global start
    global is_star_centered
    global last_back_keys
    global count
    global refueling_count
    global avoid_speed
    global star_type
    global jump_started
    global fail_jumps
    global jump_timer
    global state

    start = True
    is_star_centered = False
    last_back_keys = None
    count = 0
    refueling_count = 0
    avoid_speed = 0.5
    star_type = None
    jump_started = False
    fail_jumps = 0
    jump_timer = None
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
        state = State.TURN_FORWARD
    elif key == button_startstop:
        reset()
        print 'Pause'
    elif key == button_debug:
        debug = not debug
        print "Debug is: ", debug
    elif key == button_jump:
        reset()
        state = State.GO
    elif key == button_end:
        state = State.END
        SystemExit("Stopped")


listener = Listener(on_press=on_press)
listener.start()


while(True):
    if test and state.value > 0:
    # for tests:
        # select_first_star
        if False:
            selected, debug_image = select_first_star(True, ship.Menu)
            cv2.imshow('Debug', debug_image)
            if selected:
                print "select_first_star works"
            else:
                print "problem with select_first_star"
            cv2.waitKey(1000)

        if False:
            can, s_type, debug_image = can_refuel(debug, ship.Refuel, ship.Scanner.scan_surface_time)
            cv2.imshow('Debug', debug_image)
            if s_type is not None:
                print "can_refuel works"
            else:
                print "problem with can_refuel or you can't refuel from this star"
            cv2.waitKey(1000)
            
        #cv2.imwrite('0.png', debug_image)

    if not test and state.value > 0:
    # ---------------------------
        debug_images = []
        if start:
            print 'STARTED: version 0.0.3'
            start = False
            start_scan(ship.Scanner.scan_system_time)
            _, debug_image = select_first_star(debug, ship.Menu)
            debug_images.append(debug_image)
            time.sleep(1)

        # turn forward
        if state == State.TURN_FORWARD:
            print 'TURN FORWARD: ' + str(count)
            centered, debug_image = center_ship(debug, ship.Radar)
            debug_images.append(debug_image)
            if centered:
                count += 1
            else:
                count = 0

            if count > 10:
                print 'TURNING FINISHED'
                count = 0
                is_star_centered = True
                state = State.CHECK_REFUEL

        # check refuel
        elif state == State.CHECK_REFUEL:
            print 'CHECK REFUEL: ' + str(count)

            if star_type is None:
                can, s_type, debug_image = can_refuel(debug, ship.Refuel, ship.Scanner.scan_surface_time)
                debug_images.append(debug_image)
                if s_type is not None:
                    star_type = s_type

            need, debug_image = need_refuel(debug, ship.Refuel)
            debug_images.append(debug_image)
            if can and need:
                count += 1
            else:
                count -= 1

            if star_type is not None and "S" in star_type:
                count = 0

            if count > 5:
                print 'START REFUEL'
                count = 0
                state = State.REFUELING
                avoid_speed = ship.Avoid.avoid_speed_fast
            elif count < -5:
                print 'NO NEED REFUEL'
                count = 0
                state = State.AVOID
                avoid_speed = ship.Avoid.avoid_speed_slow

        # refueling
        elif state == State.REFUELING:
            refueling, debug_image = is_refueling(debug, ship.Refuel)
            debug_images.append(debug_image)
            if refueling:
                print 'REFUELING: ' + str(refueling_count)
                refueling_count = 0
                check_refuel_count = 0
                click_keys([Buttons.V], 0.1)
            else:
                refueling_count += 1

            if refueling_count > 50:
                refueling_count = 50
                print 'CAN I GO TO STAR? ' + str(count)

                need, debug_image = need_refuel(debug, ship.Refuel)
                debug_images.append(debug_image)

                if need:
                    count += 1
                else:
                    count -= 1

                if count > 10:
                    print 'YES, GO TO STAR'
                    count = 0
                    click_keys([Buttons.C], 0.1)
                    _, debug_image = center_ship(debug, ship.Radar)
                    debug_images.append(debug_image)

                elif count < -10:
                    print 'NO, NO NEED REFUEL'
                    count = 0
                    refueling_count = 0
                    state = State.AVOID

        # avoid
        elif state == State.AVOID:
            print 'AVOID: ' + str(count)
            runned, last_back_keys, debug_image = avoid(debug, ship.Avoid, last_back_keys, avoid_speed)
            debug_images.append(debug_image)

            if runned:
                is_star_centered = False
                count = 0
            else:
                count += 1
                last_back_keys = None

            if count > 10:
                print 'AVOIDED'
                count = 0

                if is_star_centered or star_type is None:
                    print 'WARNING: TRY GO AWAY...'
                    state = state.TURN_AROUND
                else:
                    state = State.AUTO_REFUEL

                star_type = None

        # turn around
        elif state == state.TURN_AROUND:
            print 'TURN AROUND: ' + str(count)
            centered, debug_image = center_ship(debug, ship.Radar, True)
            debug_images.append(debug_image)
            if centered:
                count += 1
            else:
                count = 0

            if count > 5:
                print 'TURNING BACK FINISHED'
                count = 0
                is_star_centered = True
                state = State.AUTO_REFUEL
        
        # auto refuel
        elif state == State.AUTO_REFUEL:
            print 'AUTO REFUEL?'
            click_keys([Buttons.C], 0.1)
            state = State.AUTO_REFUELING

        # auto refueling
        elif state == State.AUTO_REFUELING:
            print 'AUTO REFUELING: ' + str(count)
            refueling, debug_image = is_refueling(debug, ship.Refuel)
            debug_images.append(debug_image)
            if refueling:
                print 'AUTO REFUELING DETECTED'
                count = 5
            else:
                count += 1
                time.sleep(1)

            if count > 10:
                print 'AUTO REFUELING FINISHED'
                count = 0
                click_keys([Buttons.W], 10)
                click_keys([Buttons.V], 0.1)
                state = State.GO

        # go to jump
        elif state == State.GO:
            print 'GO GO GO!'
            click_keys([Buttons.T], 0.1)
            state = State.JUMP

        # jump
        elif state == State.JUMP:
            print 'JUMP: ' + str(count)

            centered, debug_image = center_ship(debug, ship.Radar)
            debug_images.append(debug_image)

            if not centered:
                count = 0
            else:
                count += 1

            if count > 5:
                print 'JUMPING!'
                count = 0
                jump_started = False
                click_keys([Buttons.M], 0.1)
                state = State.JUMPING

        # jumping
        elif state == State.JUMPING:
            print 'JUMPING: ' + str(count)
            jumping, debug_image = is_jumping(debug, ship.Radar)
            debug_images.append(debug_image)
            if jumping:
                if not jump_started:
                    jump_started = True
                    time.sleep(ship.Jump.jump_load_time)
                    click_keys([Buttons.W], 2)
                    jump_timer = Timer(60, jump_fail)
                    jump_timer.start()

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
                    jump_timer.cancel()
                    fail_jumps = 0
                    state = State.JUMPED

        # jumped
        elif state == State.JUMPED:
            print 'JUMPED: ' + str(count)
            click_keys([Buttons.V], 0.1)
            in_jump, debug_image = is_in_jump(debug, ship.Jump)
            debug_images.append(debug_image)
            if in_jump:
                count = 0
            else:
                count += 1

            if count > 10:
                print 'JUMP FINISHED!'
                count = 0
                start_scan(ship.Scanner.scan_system_time)
                _, debug_image = select_first_star(debug, ship.Menu)
                debug_images.append(debug_image)
                time.sleep(1)
                state = State.TURN_FORWARD

        # draw debug images
        if debug:
            show_images(debug_images)
    else:
        cv2.destroyWindow('Debug')

    if state == State.END:
        cv2.destroyAllWindows()
        if jump_timer is not None:
            jump_timer.cancel()
        break

    cv2.waitKey(25)
