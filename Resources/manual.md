# JV Characteristics Manual

## Introduction
___
This manual provides guidance for using the JV Characteristics Analyzer, a tool for analyzing JV characteristics of photovoltaic cells and other diodes.
## Installation
___
If using python:
1. Clone the latest version of the program from [gitlab](https://codebase.helmholtz.cloud/hyd/jv_char). (For more information follow this comprehensive [guide](https://docs.gitlab.com/ee/user/project/repository/#clone-and-open-in-visual-studio-code)).
2. Run the `main.py` file.

Alternatively, it is possible to directly install the application and use an `.exe` file by following the in-screen instructions.

## Getting Started
___
1. **Connect the hardware**: The program has been successfully used with the following:
- Keithley 2450
- 8-Channel USB relay card K8090
- Sciencetech SciSun-300 sun simulator

The minimum requirement for the program to function is a Keithley instrument. While the program can operate without a relay or a sun simulator, the absence of these devices may result in reduced functionality. Some features might not be available if specific devices are not connected or detected.
2. **Run the program**: Either by running the python code or the exe file. 

## Usage
___
### Basic Operations
1. **Basic information**: In the middle region of the GUI you will find relevant setting up fields:
- You can add the sample and username as well as the folder path. 
- The `calendar button` will automatically create a folder under a "User" folder with the current date.
- The `folder button` will allow you to choose a specific folder where to save the data. \
2. **Measurement setup**: Make sure to set the measurement values to your needs
- `Start Volgate (V)`, `End Voltage (V)`, and `Step Size (V)` refer to the initial voltage at which the measurement begins, the final voltage, and the icrement of voltage for each measurement point, respectively.
- It should be noted that if the _step size_ is not a multiple between _start voltage_ and _end voltage_, the measurement will finish after the _end voltage_ value, e.g. from 1 V to 2 V in 0.6 V steps, the program will measure 1.0, 1.6 and 2.2 V in forward and 2.0, 1.4 and 0.8 V in reverse.
- `Averaging Points` refers to the number of data points the program collects at each step of the measurement. These points are then averaged to obtain a more stable and accurate value for that specific measurement.
- This should not be confused with **nplc**, which is the averaging process used by the keithley, and which is hard-coded to 5.
- `Light soaking (s)` and `Pre-biasing (V)` will allow the sample to be illuminated for a certain amount of time at a certain bias. This will only be performed once, before the rest of the measurement continues. (Please notice that preconditioning all cells with illumination will depend on whether a mask is used, or not. Regarding bias, only the first cell will be preconditioned, due to the way the relays work.)
- Cells are always kept at open circuit conditions while measurements are not being carried out.
- `Settling time (s)` refers to the time a sample is set to a specific bias before the program reads the measured current.
- `Cell area (cm²)` refers to the area the program will use to calculate current density. This value will only be used if the **multiplexing** option is **off**. Otherwise, the program uses the areas set below.
- `Power Density (mW/cm²)` refers to the power that will be used to calculate PCE. By default, the value is set to 100, however, when setting the SuSi Intensity, this value will be updated to the calculated one. (see more below in point 3)
- `Current Limit (mA)` refers to the Keithley's current limit. It should be noted that, the higher this value is, the larger the noise is.
- `Forward` (arrow pointing right) and `Reverse` (arrow pointing left) scan directions can be selected for both light and dark conditions. Forward scan refers to the measurement where voltage increases from negative to positive, while Reverse scan refers to the measurement where voltage decreases from positive to negative.
- Measurements are always started in a forward direction and then reverse. Additionally, dark always goes before illumination. If a different process is needed, use the `Recipe` function.
- `4-wire` measurements can only be performed without multiplexing with our Keithley 2450 setup.
- `log Y-axis` will modify the plot to allow a log display
- The `SuSi Shutter` button will open or close the sun simulator shutter
- Multiplexing is only allowed if a relay is found. 
- The area values are necessary for the correct calculation of current density.
- Additional `Maximum Power Point Tracking` settings are found at the bottom.

3. **SuSi Intensity setup**
- Make sure that a (silicon) reference cell is connected for this process.
- When pressing the `Set` button next to _SuSi Intensity_, a popup will appear and the SuSi shutter will open.
- `Lamp Intensity (%)` refers to the intensity of the sun simulator for the plant. The manufacturer recommends staying within 75-105%.
- For the intensity to change, the `Set` button must be pressed.
- When opening this windows, _Current Limit_ will be automatically set to 300 mA and the measurement to 4-wire mode (make sure the cables are connected correctly).
- `Ref. cell area (cm²)` corresponds to the area size of the reference cell.
- `Ref. current (mA)` corresponds to the calibrated current value of the reference cell.
- By pressing `Test`, the reference cell will be measured and the value will be displayed, alongside the current power density.
- `Save` will save the current result on _C:/Data/susi_log.txt_, so that the lamp power value is saved and remembered for next session. Additionally, the `Power Density (mW/cm²)` value on the main window will be updated to the one just calculated.
- `Cancel` will just close the window. Nothing will be saved.
- `Status (CMD output)` will print the current status of the lamp in the console.
- It is important to note that there could be a __spectral mismatch__ that it is not accounted for in this menu.

4. **Performing a measurement**:
- After setting up the measurement conditions, simply press the green `Start` button to start a JV swipe.
- Similarly, press the blue `Start` button to start an MPP tracking.
- Additionally, the button `Recipe` will allow you to control the JV swipe process. In principle, a string of commands have to be added in sequence so that the program does it, e.g.
>FD,FD,FD,BD,FL,FL,FL,BL

will measure three times forward in the dark, once backward in the dark, three times forward illuminated and once backward illuminated in sequence. This has been tested with up to 200 commands.

5. **Metadata**:

The right panel on the GUI contains fields for metadata. These fields are not necessary to perform measurements, however, having a full set of data will not only help the user for later analysis, but it will also allow meta-analysis across time and users to study further aspects of our devices in the future.

This values contain information relevant to the samples: `Material`, `Additives`,`Concentration`,`Solvents`,`Solvents Ratio`,`Substrate`, as well as to the glovebox conditions: `Temperature (°C)`,`Water content (ppm)`,`Oxygen content (ppm)`, and general `comments`.

It should be noted that these values can later be used to do more meaningful data analysis with the help of the companion app **JV Analysis**.

Please, fill up these fields.

5. **Additional settings**:
- Metadata can be troublesome to type down. For that reason, you can `save` the metadata values and later on `load` them onto the gui. Furthermore, you can use an output JV file to fill these fields up automatically.
- The sun simulator intensity can be fixed and tuned by pressing the `Set` button.
- The sun simulator should turn on by itself when the program is started. If this does not happen, the `On` button will do it. Additionally, the lamp will be turned `Off` by pressing the button. The device will however stay on, since a fan must cool the susi controller (i.e. the lamp) before it is completely turned off. The minimum cooling time after the lamp was turned off is **10 min**. Don't forget to turn the whole device after 10-15 min.
- It should be noted that the manufacturer recommends that the lamp should warm up for 10 min before it is used for measurements.
- We strongly recommend that the light intensity is checked with a reference cell before measurements. 

## Troubleshooting
___
- At this point, there are no consistent errors to troubleshoot. 
- If a problem persists, always remember to restart the computer and the keithley (turn off and on).

## Contact
___
- For further assistance or to report issues, contact by [email](enandayapa@gmail.com) or [gitlab](https://codebase.helmholtz.cloud/hyd/jv_char).
