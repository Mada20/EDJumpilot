import os
from enum import Enum
import time
from threading import Timer
import cv2
import numpy as np

from utils import get_frame, join_images, show_images, match_template
from controls import Buttons, press_key, release_key, click_keys


class StateType(Enum):
    INIT = 0
    START = 1
    TURN_FORWARD = 2
    TURN_AROUND = 3
    CHECK_REFUEL_AND_SCAN_STAR = 4
    REFUELING = 5
    AVOID = 6
    AUTO_REFUEL = 7
    AUTO_REFUELING = 8
    GO_AHEAD = 9
    JUMP = 10
    JUMPING = 11
    JUMPED = 12
    END = -1
    STOP = -2


class State():
    start = True
    last_back_keys = None
    count = 0
    refueling_count = 0
    refueled = False
    avoid_speed = 0.5
    star_type = None
    jump_started = False
    fail_jumps = 0
    jump_timer = None
    jump_start_time = None
    type = StateType.INIT


class Tests:
    center_ship = False
    select_first_star = False
    can_refuel = False
    need_refuel = False
    is_in_route = False
    avoid = False


class Runner:
    def __init__(self, ship, debug, test, shutdown):
        self.ship = ship
        self.debug = debug
        self.test = None
        self.shutdown = shutdown

        self.state = State()

        if test:
            self.debug = True
            self.test = Tests()

    def center_ship(self, back=False):
        debug = self.debug
        opt = self.ship.Radar

        frame = get_frame()
        frame = frame[opt.radar_crop_y1:opt.radar_crop_y2, opt.radar_crop_x1:opt.radar_crop_x2]
        frame = cv2.resize(frame, (0, 0), fx=2, fy=2.12)

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
        mask = cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=1)
        mask = cv2.bitwise_not(mask)

        # get circle
        circles = cv2.HoughCircles(mask, cv2.HOUGH_GRADIENT, 4, 50, param1=100, param2=30, minRadius=54, maxRadius=54)

        center = None
        radius = None
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for c in circles:
                circle = c[0]
                center = (circle[0], circle[1])
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

        error = False

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
                thresh = cv2.threshold(mask, 127, 255, 0)[1]
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.erode(thresh.copy(), kernel, iterations=3)
                contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]
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
                        thresh = cv2.threshold(mask, 0, 255, 0)[1]
                        mask = cv2.dilate(thresh, kernel, iterations=4)

                        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]
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
                error = True
        else:
            print 'ERROR: CIRCLE NOT FOUND'
            error = True

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
                            keys.append(Buttons.D)
                        elif deltaX > opt.margin:
                            keys.append(Buttons.A)

                        if deltaY < -opt.margin:
                            keys.append(Buttons.NP_2)
                        elif deltaY > opt.margin:
                            keys.append(Buttons.NP_8)

                    elif point_position == 2:
                        if deltaX < -opt.margin:
                            keys.append(Buttons.D)
                        else:
                            keys.append(Buttons.A)

                        if deltaY < -opt.margin:
                            keys.append(Buttons.NP_2)
                        else:
                            keys.append(Buttons.NP_8)
                else:
                    if point_position == 1:
                        if deltaX < -opt.margin:
                            keys.append(Buttons.A)
                        else:
                            keys.append(Buttons.D)

                        if deltaY < -opt.margin:
                            keys.append(Buttons.NP_8)
                        else:
                            keys.append(Buttons.NP_2)

                    elif point_position == 2:
                        if deltaX < -opt.margin:
                            keys.append(Buttons.A)
                        elif deltaX > opt.margin:
                            keys.append(Buttons.D)

                        if deltaY < -opt.margin:
                            keys.append(Buttons.NP_8)
                        elif deltaY > opt.margin:
                            keys.append(Buttons.NP_2)

                click_keys(keys, opt.move_time)

        return len(keys) > 0, error, debug_img

    def is_refueling(self):
        debug = self.debug
        opt = self.ship.Refuel

        frame = get_frame()
        crop = frame[opt.need_refuel_crop_y1:opt.need_refuel_crop_y2, opt.need_refuel_crop_x1:opt.need_refuel_crop_x2]

        lower_mask = np.array([240, 240, 240])
        upper_mask = np.array([255, 255, 255])
        mask = cv2.inRange(crop, lower_mask, upper_mask)

        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]

        debug_image = None
        if debug:
            debug_image = join_images(crop, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB))

        return len(contours) > 0, debug_image

    def need_refuel(self):
        debug = self.debug
        opt = self.ship.Refuel

        frame = get_frame()
        crop = frame[opt.need_refuel_crop_y1:opt.need_refuel_crop_y2, opt.need_refuel_crop_x1:opt.need_refuel_crop_x2]

        red = crop.copy()
        red[:, :, 0] = 0
        red[:, :, 1] = 0
        lower_mask = np.array([0, 0, 252])
        upper_mask = np.array([0, 0, 255])
        gray = cv2.inRange(red, lower_mask, upper_mask)

        # gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        # gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        kernel = np.ones((4, 4), np.uint8)
        #dilation = cv2.dilate(gray, kernel, iterations=1)
        erosion = cv2.erode(gray, kernel, iterations=1)

        contours = cv2.findContours(erosion, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]

        w = 0
        contour = None
        if len(contours) > 0:
            contour = max(contours, key=cv2.contourArea)
            cv2.drawContours(crop, [contour], 0, (255, 255, 0), 1)
            w = cv2.boundingRect(contour)[2]

        debug_image = None
        if debug:
            debug_image = join_images(crop, cv2.cvtColor(erosion, cv2.COLOR_GRAY2RGB))

        return opt.min_refuel > w, debug_image, w

    def select_first_star(self, use_template=False):
        debug = self.debug

        result = False

        click_keys([Buttons.BUTTON_1], 0.1)
        time.sleep(1)

        click_keys([Buttons.D], 0.1)

        click_keys([Buttons.S], 0.1)
        click_keys([Buttons.W], 1)

        click_keys([Buttons.SPACE], 0.1)

        debug_image = None

        if use_template:
            opt = self.ship.Menu

            time.sleep(1)

            frame = get_frame()
            crop = frame[opt.select_menu_y1:opt.select_menu_y2, opt.select_menu_x1:opt.select_menu_x2]

            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

            if match_template(gray, 'images/unlock.png', 0.75)[0]:
                click_keys([Buttons.W], 0.1)
                click_keys([Buttons.SPACE], 0.1)
                result = True
            elif match_template(gray, 'images/lock.png', 0.75)[0]:
                click_keys([Buttons.SPACE], 0.1)
                result = True

            if debug:
                debug_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        else:
            time.sleep(0.1)
            click_keys([Buttons.SPACE], 0.1)
            result = True

        click_keys([Buttons.BUTTON_1], 0.1)
        return result, debug_image

    def avoid(self, last_keys=None, speed=1):
        debug = self.debug
        opt = self.ship.Avoid

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

        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]

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
                keys.append(Buttons.A)

            elif deltaX > 0:
                keys.append(Buttons.D)

            if deltaY >= 0:
                keys.append(Buttons.NP_2)

            if deltaY < 0:
                keys.append(Buttons.NP_8)

        if len(keys) > 0:
            click_keys(keys, speed)

        if debug_image is not None:
            debug_image = cv2.resize(join_images(crop, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), True), (0, 0), fx=0.5, fy=0.5)

        return M is not None, keys, debug_image

    def is_jumping(self):
        debug = self.debug
        opt = self.ship.Radar

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

    def can_refuel(self):
        debug = self.debug
        opt = self.ship.Refuel

        result = False

        frame = get_frame()
        crop = frame[opt.can_refuel_crop_y1:opt.can_refuel_crop_y2, opt.can_refuel_crop_x1:opt.can_refuel_crop_x2]

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        gray = cv2.resize(gray, (0, 0), fx=2, fy=2)
        gray = cv2.bitwise_not(gray)

        star_type = None
        ignore_print = False

        is_white_dwarf = match_template(gray, 'images/da.png', opt.threshold)[0]
        is_black_hole = match_template(gray, 'images/black.png', opt.threshold)[0]

        if not is_white_dwarf and not is_black_hole:
            if match_template(gray, 'images/sc.png', opt.threshold)[0]:
                print 'STAR IS SCANNED'
                star_type = 'S'
                ignore_print = True
            elif match_template(gray, 'images/m.png', opt.threshold)[0]:
                star_type = 'M'
                result = True
            elif match_template(gray, 'images/k.png', opt.threshold)[0]:
                star_type = 'K'
                result = True
            elif match_template(gray, 'images/g.png', opt.threshold)[0]:
                star_type = 'G'
                result = True
            elif match_template(gray, 'images/f.png', opt.threshold)[0]:
                star_type = 'F'
                result = True
            elif match_template(gray, 'images/a.png', opt.threshold)[0]:
                star_type = 'A'
                result = True
            elif match_template(gray, 'images/b.png', opt.threshold)[0]:
                star_type = 'B'
                result = True
            elif match_template(gray, 'images/0.png', opt.threshold)[0]:
                star_type = '0'
                result = True
            elif match_template(gray, 'images/un.png', opt.threshold)[0]:
                print 'STAR IS UNEXPLORED, WHY?'
                ignore_print = True
        elif is_white_dwarf:
            print 'STAR IS WHITE DWARF'
            ignore_print = True
        elif is_black_hole:
            print 'STAR IS BLACK HOLE'
            ignore_print = True

        if not ignore_print:
            if star_type is not None:
                print 'STAR TYPE IS ' + star_type
            else:
                print 'STAR TYPE IS UNKNOWN'

        debug_image = None
        if debug:
            debug_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

        return result, star_type, debug_image

    def is_in_jump(self):
        debug = self.debug
        opt = self.ship.Jump

        frame = get_frame()
        crop = frame[opt.in_jump_crop_y1:opt.in_jump_crop_y2, opt.in_jump_crop_x1:opt.in_jump_crop_x2]

        lower_mask = np.array([250, 250, 250])
        upper_mask = np.array([255, 255, 255])
        mask = cv2.inRange(crop, lower_mask, upper_mask)

        kernel = np.ones((4, 4), np.uint8)
        dilation = cv2.dilate(mask, kernel, iterations=1)

        contours = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]

        debug_image = None
        if debug:
            debug_image = cv2.cvtColor(dilation, cv2.COLOR_GRAY2RGB)

        return len(contours) > 0, debug_image

    def is_in_route(self):
        debug = self.debug

        click_keys([Buttons.BUTTON_1], 0.1)
        time.sleep(2)

        frame = get_frame()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        result, loc = match_template(gray, 'images/route.png', 0.8)

        click_keys([Buttons.BUTTON_1], 0.1)

        debug_image = None
        if debug:
            debug_image = frame
            for pt in zip(*loc[::-1]):
                cv2.rectangle(frame, (pt[0] - 1, pt[1] - 1), (pt[0] + 30, pt[1] + 28), (0, 0, 255), 1)
            debug_image = cv2.resize(debug_image, (0, 0), fx=0.5, fy=0.5)

        return result, debug_image

    def set_state_type(self, state_type):
        if self.state.type is not StateType.END and self.state.type is not StateType.INIT:
            self.state.type = state_type

    def reset(self):
        self.state = State()

    def start_scan(self):
        print 'START SCAN'
        press_key(Buttons.NP_P)
        r = Timer(self.ship.Scanner.scan_system_time, self.end_scan)
        r.start()

    def end_scan(self):
        print('END SCAN')
        release_key(Buttons.NP_P)

    def jump_fail(self):
        print 'ERROR: JUMP FAILURE!!!'

        click_keys([Buttons.M], 0.1)
        click_keys([Buttons.V], 0.1)

        self.state.jump_started = False
        self.state.jump_timer = None
        self.state.count = 0
        self.set_state_type(StateType.JUMP)

    def set_debug(self, debug):
        self.debug = debug
        if not debug:
            cv2.destroyWindow('Debug')

    def run(self):
        if self.state.type.value > 0:
            if self.test is not None:
                self.run_test()
            else:
                self.run_main()
        else:
            cv2.destroyWindow('Debug')

        if self.state.type == StateType.END:
            cv2.destroyAllWindows()
            if self.state.jump_timer is not None:
                self.state.jump_timer.cancel()
                self.state.jump_timer = None
            return False

        if self.debug:
            cv2.waitKey(25)
        else:
            time.sleep(0.025)

        return True

    def run_main(self):
        state = self.state
        debug_images = []
        if state.start:
            print 'STARTED'
            selected, debug_image = self.select_first_star(True)
            debug_images.append(debug_image)
            time.sleep(1)
            if not selected:
                print 'PROBLEM WITH STAR SELECT'
                return
            else:
                state.start = False
                self.start_scan()

        # start
        if state.type == StateType.START:
            state.jump_start_time = time.time()
            self.set_state_type(StateType.TURN_FORWARD)

        # turn forward
        elif state.type == StateType.TURN_FORWARD:
            print 'TURN FORWARD: ' + str(state.count)
            centered, error, debug_image = self.center_ship()
            debug_images.append(debug_image)
            if centered:
                state.count = 0
            elif error:
                click_keys([Buttons.NP_6], 1)
                state.count = 0
            else:
                state.count += 1

            if state.count > 10:
                print 'TURNING FINISHED'
                state.count = 0
                state.star_type = None
                state.refueled = False
                self.set_state_type(StateType.CHECK_REFUEL_AND_SCAN_STAR)
                time.sleep(1)

        # check refuel and scan star
        elif state.type == StateType.CHECK_REFUEL_AND_SCAN_STAR:
            print 'CHECK REFUEL: ' + str(state.count)

            if state.star_type is None:
                can, star_type, debug_image = self.can_refuel()
                debug_images.append(debug_image)
                if star_type is not None:
                    state.star_type = star_type
            else:
                can = True

            need, debug_image, _ = self.need_refuel()
            debug_images.append(debug_image)
            if can and need:
                state.count += 1
            elif state.star_type is not None and state.star_type is "S":
                state.count = 0
                state.star_type = None
                time.sleep(self.ship.Scanner.scan_surface_time)
            else:
                state.count -= 1
                if state.star_type is None:
                    time.sleep(1)

            if state.count > 5:
                print 'START REFUEL'
                state.count = 0
                self.set_state_type(StateType.REFUELING)
                state.avoid_speed = self.ship.Avoid.avoid_speed_fast
            # 2 attempts for determining the width of the fuel bar
            elif state.count < -2 and can:
                print 'NO NEED REFUEL'
                state.count = 0
                self.set_state_type(StateType.AVOID)
                state.avoid_speed = self.ship.Avoid.avoid_speed_slow
            # can be problem with detect star type that's why 10 attempts
            elif state.count < -10 and not can:
                print 'WARNING: TRYING TURN AROUND...'
                state.count = 0
                self.set_state_type(StateType.TURN_AROUND)

        # refueling
        elif state.type == StateType.REFUELING:
            print 'REFUELING: ' + str(state.refueling_count)

            refueling, debug_image = self.is_refueling()
            debug_images.append(debug_image)
            if refueling:
                state.refueling_count = 0
                click_keys([Buttons.V], 0.1)
            else:
                state.refueling_count += 1

            if state.refueling_count > 10:
                state.refueling_count = 10
                print 'CAN I GET CLOSER TO STAR? ' + str(state.count)

                need, debug_image, _ = self.need_refuel()
                debug_images.append(debug_image)

                if need:
                    state.count += 1
                else:
                    state.count -= 1

                if state.count > 10:
                    print 'YES, GO TO STAR CLOSER'
                    state.count = 0
                    click_keys([Buttons.C], 0.1)
                    debug_image = self.center_ship()[2]
                    debug_images.append(debug_image)

                elif state.count < -10:
                    print 'NO, NO NEED REFUEL'
                    state.count = 0
                    state.refueled = True
                    state.refueling_count = 0
                    self.set_state_type(StateType.AVOID)

        # avoid
        elif state.type == StateType.AVOID:
            print 'AVOID: ' + str(state.count)
            avoided, last_back_keys, debug_image = self.avoid(state.last_back_keys, state.avoid_speed)
            state.last_back_keys = last_back_keys
            debug_images.append(debug_image)

            if avoided:
                state.count = 0
            else:
                state.count += 1
                state.last_back_keys = None

            if state.count > 10:
                print 'AVOIDED'
                state.count = 0
                if state.refueled:
                    click_keys([Buttons.W], self.ship.go_ahead_time / 2)
                    self.set_state_type(StateType.GO_AHEAD)
                else:
                    self.set_state_type(StateType.AUTO_REFUEL)

        # turn around
        elif state.type == StateType.TURN_AROUND:
            print 'TURN AROUND: ' + str(state.count)
            centered, error, debug_image = self.center_ship(True)
            debug_images.append(debug_image)
            if centered:
                state.count = 0
            elif error:
                click_keys([Buttons.NP_4], 1)
                state.count = 0
            else:
                state.count += 1

            if state.count > 5:
                print 'TURNING AROUND FINISHED'
                state.count = 0
                self.set_state_type(StateType.GO_AHEAD)

        # auto refuel
        elif state.type == StateType.AUTO_REFUEL:
            print 'AUTO REFUEL?'
            click_keys([Buttons.C], 0.1)
            self.set_state_type(StateType.AUTO_REFUELING)

        # auto refueling
        elif state.type == StateType.AUTO_REFUELING:
            print 'AUTO REFUELING: ' + str(state.count)
            refueling, debug_image = self.is_refueling()
            debug_images.append(debug_image)
            if refueling:
                print 'AUTO REFUELING DETECTED'
                state.count = 50
            else:
                state.count += 1

            if state.count > 100:
                print 'AUTO REFUELING FINISHED'
                state.count = 0
                self.set_state_type(StateType.GO_AHEAD)

        # go to jump
        elif state.type == StateType.GO_AHEAD:
            print 'GO GO GO!'
            click_keys([Buttons.W], self.ship.go_ahead_time)
            click_keys([Buttons.V], 0.1)
            click_keys([Buttons.T], 0.1)
            self.set_state_type(StateType.JUMP)

        # jump
        elif state.type == StateType.JUMP:
            print 'JUMP: ' + str(state.count)

            centered, error, debug_image = self.center_ship()
            debug_images.append(debug_image)

            if centered:
                state.count = 0
            elif error:
                click_keys([Buttons.NP_6], 1)
                state.count = 0
            else:
                state.count += 1

            if state.count > 5:
                print 'JUMPING!'
                click_keys([Buttons.M], 0.1)
                state.count = 0
                state.jump_started = False
                self.set_state_type(StateType.JUMPING)

        # jumping
        elif state.type == StateType.JUMPING:
            print 'JUMPING: ' + str(state.count)
            jumping, debug_image = self.is_jumping()
            debug_images.append(debug_image)
            if jumping:
                if not state.jump_started:
                    print 'JUMP DETECTED, GET READY!'
                    time.sleep(self.ship.Jump.jump_load_time)
                    click_keys([Buttons.W], 2)
                    state.jump_started = True
                    state.jump_timer = Timer(60, self.jump_fail)
                    state.jump_timer.start()

                state.count = 0
            else:
                state.count += 1

            # if oval is not visible
            if state.count > 50 and not state.jump_started:
                click_keys([Buttons.NP_6], 0.2)

            if state.count > 100:
                state.count = 0
                if not state.jump_started:
                    print 'JUMP STOPPED!'
                    click_keys([Buttons.M], 0.1)

                    in_route, debug_image = self.is_in_route()
                    debug_images.append(debug_image)

                    if not in_route:
                        print 'NOT IN ROUTE, STOP!'
                        self.set_state_type(StateType.STOP)
                        if self.shutdown:
                            os.system('shutdown -s')
                    else:
                        state.fail_jumps += 1
                        if state.fail_jumps > 5:
                            print 'PROBLEM WITH JUMP!'
                            self.set_state_type(StateType.STOP)
                        elif state.star_type is None:
                            self.set_state_type(StateType.TURN_AROUND)
                        else:
                            self.set_state_type(StateType.AVOID)
                else:
                    print 'IN JUMP!'
                    state.fail_jumps = 0
                    self.set_state_type(StateType.JUMPED)

                if state.jump_timer is not None:
                    state.jump_timer.cancel()
                    state.jump_timer = None

        # jumped
        elif state.type == StateType.JUMPED:
            print 'JUMPED: ' + str(state.count)
            click_keys([Buttons.V], 0.1)
            in_jump, debug_image = self.is_in_jump()
            debug_images.append(debug_image)
            if in_jump:
                state.count = 0
            else:
                state.count += 1

            if state.count > 10:
                if state.jump_start_time is not None:
                    jump_end_time = time.time()
                    print('JUMP FINISHED IN %.2f!' % ((jump_end_time - state.jump_start_time) / 60))
                else:
                    print('JUMP FINISHED!')
                self.start_scan()
                debug_image = self.select_first_star()[1]
                debug_images.append(debug_image)
                time.sleep(1)
                state.count = 0
                self.set_state_type(StateType.START)

        # draw debug images
        if self.debug:
            show_images([image for image in debug_images if image is not None])

    def run_test(self):
        # center_ship
        if self.test.center_ship:
            centered, _, debug_image = self.center_ship()
            cv2.imshow('Debug', debug_image)
            if centered:
                print "center_ship works"
            else:
                print "problem with center_ship"
            cv2.waitKey(50)

        # select_first_star
        if self.test.select_first_star:
            selected, debug_image = self.select_first_star(True)
            if debug_image is not None:
                cv2.imshow('Debug', debug_image)
            if selected:
                print "select_first_star works"
            else:
                print "problem with select_first_star"
            cv2.waitKey(1000)

        # can_refuel
        if self.test.can_refuel:
            _, s_type, debug_image = self.can_refuel()
            cv2.imshow('Debug', debug_image)
            if s_type is not None:
                print "can_refuel works"
            else:
                print "problem with can_refuel or you can't refuel from this star"
            cv2.waitKey(1000)

        # need_refuel
        if self.test.need_refuel:
            need, debug_image, w = self.need_refuel()
            cv2.imshow('Debug', debug_image)
            if need is not None:
                print "need_refuel works " + str(need) + " " + str(w)
            else:
                print "problem with need_refuel or you don't need refuel" + str(w)
            cv2.waitKey(1000)

        # is_in_route
        if self.test.is_in_route:
            in_route, debug_image = self.is_in_route()
            cv2.imshow('Debug', debug_image)
            if in_route:
                print "Route is active"
            else:
                print "Route is not active"
            cv2.waitKey(1000)

        # avoid
        if self.test.avoid:
            avoided, _, debug_image = self.avoid(None, self.state.avoid_speed)
            cv2.imshow('Debug', debug_image)
            if avoided:
                print "avoid works"
            else:
                print "problem with avoid or avoid is not needed"
            cv2.waitKey(100)

        #cv2.imwrite('0.png', debug_image)
