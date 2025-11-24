# Installation instructions 24 Nov 2025

## Install Blender (4.5+)
Go to www.blender.org and download and install  Blender (4.5+)

## Install DataPrepTulips3D in Blender
Clone or download our repositatory: https://github.com/bldevries/DataPrepTulips3D

The Blender Python executable can be found in the Blender install. For example on Mac it could be found here, depending on where you installed Blender:
```/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11```

Now you can install DataPrepTulips3D for Blender using:
```/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11 -m pip install -e <..>/DataPrepTulips3D/.```

## Install mesaPlot for Blender:
This is a bit quicker, you can just run:
```/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11 -m pip install mesaPlot```

## Start Blender from the command-line (optional and Mac only):
Now start Blender in a terminal:
```/Applications/Blender.app/Contents/MacOS/Blender```

## Install the Tulips3D addon
Download the zipped addon: https://github.com/bldevries/tulips3d/blob/main/addon/tulips3d.zip
Go into Blender
Navigate the menus: Edit > Preferences > Add-ons
Find the downward arrow in the top right of the window, click it and choose "Install from Disk..."
Search for the downloaded zip file and choose it.
Now Tulips3D is shown in the list and check if it is selected properly

## Where to find Tulips3D in the Blender UI
The data loading UI can be found in the "Scene" tab in the "Properties" window. This window is usually found in the right part of the UI and it has many small tabs of which one is the Scene tab. There you can find a "Tulips3D" dropdown menu.

To manipulate the selected star object, there is a sidebar UI. You can make this appear through menus by going to View > Sidebar. You will see a sidebar appear in the 3D Viewport that has some tabs of which the last is named "Tulips3D". If you have created an object and selected it, here you can set some data properties and things.


## Load a DataPrepTulips3D file
Here is an example file I made:
https://www.dropbox.com/scl/fi/lqpgvdv587pxqd5ug7wyk/binary.pkl?rlkey=yxz9xvhdke126ab9lgd3ci49a&st=o1h3sa3g&dl=0

Now you can go into Blender, go to the Properties window and the Scene tab and find the Tulips3D section of the UI. Press the file Icon to find and select the "binary.pkl" you just downloaded. The click "Create Tulips3D Object" to make an object. It should appear in your 3D View. To see some colors you might need to set Viewport Shading to Rendered. You typically do this by selecting this render mode in the top right of the 3D Viewport. It is one of the small icons of a ball. 

Now you can play with some of the data using the sidebar. If the object is selected you can choose between different MESA Profiles. You can also set the time index to select different times. 

The frames in the animation are linked to the time index of the mesa profiles. So when you select a different frame in the Timeline (often visible below the 3D Viewport), the model should update to a different time index. This is all still very slow and might occasionally crash Blender, so take care :) In the sidebar you can choose how the frame number is mapped to the time index.

## Creating your own DataPrepTulips3D file
You probably want to install DataPrepTulips3D in a virtual env. You can then run the following commands to generate a pickly file based on your own mesa files:

```python
import DataPrepTulips3D as DP
d = DP.loadMesaData(mesa_LOGS_directory = "<..>/Profiles/LOGS1", \
                    filename_history = "history1.data",\
                   profiles=['logT', 'mass', 'logRho', 'he4'])
d.print_summary()
d.reduceResolutionRadialData(max_nr_points=100)
DP.save_Data1D_to_pickle(d, "<..>/binary.pkl")
```

Now you can try this out in Blender :)




