class Anaconda:
    go_ahead_time = 10

    ### avoid options ###
    class Avoid:
        # visibility of the ship (danger zone)
        danger_zone_crop_x1 = 160
        danger_zone_crop_x2 = 1760
        danger_zone_crop_y1 = 0
        danger_zone_crop_y2 = 700
        # center of avoid #
        avoid_center_x = 800
        avoid_center_y = 350
        avoid_speed_slow = 0.5  # standard avoid speed - it's time of keys pressed
        avoid_speed_fast = 2  # avoid speed after refuel - it's time of keys pressed

    ### refuel options ###
    class Refuel:
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
    class Radar:
        margin = 10  # margin of error
        move_time = 0.2  # rotate click pause - it's time of keys pressed
        # crop options where radar #
        radar_crop_x1 = 660
        radar_crop_x2 = 810
        radar_crop_y1 = 760
        radar_crop_y2 = 960

    ### scanning options ###
    class Scanner:
        scan_surface_time = 10
        scan_system_time = 8

    ### jump options ###
    class Jump:
        jump_load_time = 14
        # crop options where is jump info #
        in_jump_crop_x1 = 1120
        in_jump_crop_x2 = 1160
        in_jump_crop_y1 = 870
        in_jump_crop_y2 = 910

    ### menu options ###
    class Menu:
        # crop options where is menu after star choose #
        select_menu_x1 = 410
        select_menu_x2 = 520
        select_menu_y1 = 535
        select_menu_y2 = 565
