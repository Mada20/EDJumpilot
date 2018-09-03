# EDjumpilot v.0.0.5

EDjumpilot is a python script to jump on a plotted route in the game Elite Dangerous. I wrote this script to facilitate the most stupid activity in the game what is jumps. Jumping is the most boring activity in the game, so I did not want to spoil the game and never back. Suggestions welcome.

Features
----
 - scanning a star (optional)
 - refueling
 - avoiding / leaving a star
 - jumping if next destination exist

Example
----
<https://youtu.be/OfYKQbecI6k>

Requirements
----
 - Python 2.7.15
 - OpenCV 3.4.1 <https://opencv.org/>
   You must have the cv2.pyd library in the folder in which the script is located or in ../Python27/lib/site-packages.
   Instructions for Windows: <https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_setup/py_setup_in_windows/py_setup_in_windows.html>

Installation / configuration
----
 1. Download the repository.
 2. Install the required libraries by pip used by script if you do not have them. (ctypes, pynput, numpy, PIL)
 3. Edit config.json and configure options in your own way.
    (For now all settings are for Anaconda and screen resolution FullHD)

    | Option | Description | Possible values |
    | ------ | ------ | ------ |
    | debug | For checking images from OpenCV | boolean: false / true |
    | disable_star_scan | For disabling star scan | boolean: false / true |
    | shutdown | Active it if you want turn off you computer after route finish | boolean: false / true |
    | jumps_number | Set numbers of stars to route finish faster | number: -1 - inactive, > 0 - active |
    | ship_config_dir | Directory for ship configuration | string |
    | test | For tests | boolean: false / true |
    | tests | For tests | object with booleans |

 4. Use default HUD colour and set interface brightness to full. (System panels (default:4) -> Functions -> INTERFACE BRIGHTNESS)
 5. If you want, edit controls.py and change settings for buttons in lines: 6 - 22 or change buttons settings in the game:

    | Button | Description |
    | ------ | ------ |
    | W | increase throttle / ui panel up |
    | S | ui panel down |
    | A | yaw left |
    | D | ui panel right / yaw right |
    | B | throttle 75% |
    | C | throttle 25% |
    | V | throttle 0% |
    | T | target next system in route |
    | M | hyperspace jump |
    | 1 | target panel |
    | SPACE | ui panel select |
    | NumberPad 2 | pitch down |
    | NumberPad 8 | pitch up |
    | NumberPad 4 | roll left |
    | NumberPad 6 | roll right |
    | NumberPad plus | primary fire (discovery scanner) |

6. Set up your graphics settings in game (\AppData\Local\Frontier Developments\Elite Dangerous\Options\Graphics\Settings.xml). It is my file:
    ```sh
    <?xml version="1.0" encoding="UTF-8" ?>
    <GraphicsOptions>
    	<Version>1</Version>
    	<PresetName>Low</PresetName>
    	<StereoscopicMode>0</StereoscopicMode>
    	<IPDAmount>0.001000</IPDAmount>
    	<AMDCrashFix>false</AMDCrashFix>
    	<FOV>57.160000</FOV>
    	<HighResScreenCapAntiAlias>3</HighResScreenCapAntiAlias>
    	<HighResScreenCapScale>4</HighResScreenCapScale>
    	<GammaOffset>0.360000</GammaOffset>
    	<DisableGuiEffects>false</DisableGuiEffects>
    	<StereoFocalDistance>25.000000</StereoFocalDistance>
    	<StencilDump>false</StencilDump>
    	<ShaderWarming>true</ShaderWarming>
    	<VehicleMotionBlackout>true</VehicleMotionBlackout>
    	<VehicleMaintainHorizonCamera>false</VehicleMaintainHorizonCamera>
    	<DisableCameraShake>false</DisableCameraShake>
    </GraphicsOptions>
    ```

Instructions
----
 1. Run the main.py script. <https://www.pythoncentral.io/execute-python-script-file-shell/>
 2. Run the game and calculate the route (plot route). 
 3. Check if the navigation tab is selected in target panel.
 4. Check if DISCOVERY SCANNER is set as primary weapon and chosen.
 5. Engage Supercruise.
 6. Click F5 to run the script, click F5 again to pause script. (F5, if you have not changed it)
 7. Click F8 to finish the script. (F8, if you have not changed it)
- Tip 1. Click F6 for toggle debug.
- Tip 2. Click F7 if ship is ready to jump :)

Warnings
----
 - The rules of this game prohibit such a thing, so you use the script at your own risk
 - The script is not perfect, do not leave the unattended script enabled
 - For now only an Anaconda works ... I tried to add Cutter and ASP Explorer but I do not have time and I do not need other ships ... Donate me (button below) if you want more ships and maybe I will add others ships. :P

Todos
----
 - configure more ships
 - code improvements
 - add a screen resolution configuration
 - add option for HUD colour

License
----
**Free, free and free! Good luck Commanders!**

[![paypal](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=MA6HTH23PKJBG)