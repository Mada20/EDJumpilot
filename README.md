# EDjumpilot v.0.0.1

EDjumpilot is a python script to jump on a plotted route in the game Elite Dangerous. I wrote this script to facilitate the most stupid activity in the game what is jumps. Jumping is the most boring activity in the game, so I didn't want to spoil the game and never back. Suggestions welcome.

Features
----
 - scanning a star
 - refueling
 - avoiding / leaving a star
 - jumping if next destination exist

Requirements
----
 - Python 2.7.15
 - OpenCV 3.4.1 <https://opencv.org/>
   You must have the cv2.pyd library in the folder in which the script is located or in ../Python27/lib/site-packages.
   Instructions for Windows: <https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_setup/py_setup_in_windows/py_setup_in_windows.html>
 - Google Tesseract OCR 3.05.01 <https://github.com/tesseract-ocr/tesseract> (for pytesseract - text recognized)
   You must be able to invoke the tesseract command as *tesseract*.

Installation / configuration
----
 1. Download jumpilot.py.
 2. Install the required libraries used by script if you do not have them (ctypes, pynput, pytesseract, numpy, PIL)
 3. Edit jumpilot.py and configure options in your own way (lines: 14 - 71). 
    (For now all settings are for Anaconda and screen resolution FullHD)
 4. If you want, edit jumpilot.py and change options for buttons in lines: 153 -168 or change buttons settings in the game:

| Button | Description |
| ------ | ------ |
| W | increase throttle / ui panel up |
| S | ui panel down |
| D | ui panel right |
| C | throttle 25% |
| V | throttle 0% |
| T | target next system in route |
| B | throttle 75% |
| M | hyperspace jump |
| 1 | target panel |
| SPACE | ui panel select |
| NumberPad 2 | pitch down |
| NumberPad 8 | pitch up |
| NumberPad 4 | yaw left |
| NumberPad 6 | yaw right |
| NumberPad plus | primary fire (discovery scanner) |

Instructions
----
 1. Run the jumpilot.py script. <https://www.pythoncentral.io/execute-python-script-file-shell/>
 2. Run the game and calculate the route (plot route). 
 3. Check if the navigation tab is selected in target panel.
 4. Engage Supercruise.
 5. Click F5 to run the script. (F5, if you have not changed it)
 6. Click F8 to finish the script. (F8, if you have not changed it)

Warnings
----
 - The rules of this game prohibit such a thing, so you use the script at your own risk
 - The script is not perfect, do not leave the unattended script enabled

Todos
----
 - configure more ships
 - code improvements
 - delete the pytesseract library (I want use only OpenCV)
 - add a screen resolution configuration

License
----
**Free, free and free! Good luck Commanders!**

[![paypal](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=MA6HTH23PKJBG)
