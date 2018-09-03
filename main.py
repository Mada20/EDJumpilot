import time
import json
from pynput.keyboard import Key, Listener
from runner import Runner, StateType


### button options ###
button_startstop = Key.f5
button_debug = Key.f6
button_jump = Key.f7
button_end = Key.f8
### ------- ###

config = None
with open('config.json', 'r') as f:
    config = json.load(f)


runner = Runner(config)


def on_press(key):
    # listener keyboards
    global runner

    if key == button_startstop and runner.state.type == StateType.INIT:
        runner.reset()
        runner.state.type = StateType.START
    elif key == button_startstop:
        print 'PAUSED'
        runner.state.type = StateType.INIT
    elif key == button_debug:
        runner.set_debug(not runner.debug)
        print "DEBUG IS: ", runner.debug
    elif key == button_jump:
        runner.reset()
        runner.state.start = False
        runner.state.type = StateType.GO_AHEAD
    elif key == button_end:
        runner.state.type = StateType.END
        print 'STOPPED. BYE COMMANDER!'
        SystemExit("Stopped")


listener = Listener(on_press=on_press)
listener.start()

print 'WELCOME COMMANDER IN EDJUMPILOT v.0.0.5'

run = True
while(run):
    run = runner.run()
