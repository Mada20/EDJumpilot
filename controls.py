import ctypes
import time


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
