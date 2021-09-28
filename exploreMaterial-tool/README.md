# Dataset Explorer Tool (DEx)
The DMD annotations come in [Video Content Description (VCD)](https://vcd.vicomtech.org/) format, which is compatible with the ASAM OpenLABEL annotation standard.
This language is defined with JSON schemas and supports different types of annotations, being ideal for describing any kind of scenes.
The DMD has spatial and temporal annotations (e.g. Bounding boxes and time intervals), also context and static annotations (e.g. Driver’s and environmental info); with VCD, it is possible to have all these annotations in one file. VCD is also an API, you can use the library to create and update VCD files.

We have developed DEx tool to help access those annotations in the VCD easily. The main functionality of DEx at the moment is to access the VCD’s, read annotations and prepare DMD material for training.

## Content
- [Dataset Explorer Tool (DEx)](#dataset-explorer-tool-dex)
  - [Content](#content)
  - [DEx characteristics](#dex-characteristics)
  - [Usage Instructions](#usage-instructions)
    - [DEx initialization](#dex-initialization)
    - [DEx export configuration](#dex-export-configuration)
  - [Changelog](#changelog)

## Setup and Launching
DEx tool has been tested using the following system configuration:

**OS:**           Ubuntu 18.04, Windows 10 <br>
**Dependencies:** Python 3.8, OpenCV-Python 4.2.0, VCD 4.3.0, FFMPEG and [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)                     

For a detailed description on how to configure the environment and launch the tool, check: [Linux](../docs/setup_linux.md) / [Windows](../docs/setup_windows.md)

## DEx characteristics
TaTo is a python-based tool to access VCD annotations more easily. You can prepare the DMD material for training by using DEx. The main functionalities of DEx are: exporting material in images or videos by frame intervals from the annotations, group the resulting material into folders organized by classes (only available for DMD) and after the material is organized by classes, the tool can generate a training and a testing split.

- Get a **list of frame intervals** of a specific activity (or label) from VCD.
- Take a list of frame intervals and **divide** them into **subintervals** of desired size. This can be done starting from the first frame of from the last frame and back.
- **Export** those frame intervals as **video clips** or **images**. The material can be exported from the 3 camera perspectives videos (only available for DMD).
- **Export** intervals from **IR**, **RGB** or **DEPTH** material. Each material type will be in a different folder: dmd-ir, dmd-rgb, dmd-depth. 
- You can choose what material to export: a group's material, a session material or just the material from a specific VCD annotation.
- If you are working with the DMD, the exported material will be organized in a similar way as the DMD structure: by groups, sessions and subjects. With DEx, you can **group** this material by **classes**. This is only possible with DMD material.
- After you have the data organized by classes, you can **split** the material into a **training** and a **testing** split. You must provide the testing **ratio or proportion** (e.g: 0.20, 0.25). If the testing ratio is 0.20, the result is a folder named “train” with 80% of the data and a folder named “test” with the 20% of the data.
- Get **statistics** of data. This means, get the number of frames per class and the total number of frames.

## Usage Instructions
### DEx initialization 
You can initialize the tool by executing the python script [DExTool.py](./DExTool.py). This script will guide you to prepare the DMD material. 

If you need something more specific, you can direclty implement functions from [accessDMDAnn.py](./accessDMDAnn.py), [vcd4reader.py](./vcd4reader.py), [group_split_material.py](./group_split_material.py).

### DEx export configuration
There are some export settings you can change at the __init()__ function of file [accessDMDAnn.py](./accessDMDAnn.py) under “-- CONTROL VARIABLES --“ comment.
- To define the **data format** you wish to export, add “image” and/or “video” to **@material** variable as a list.
- The list of **camera perspectives** to export material from can be defined in **@streams** variable, these are: "face", "body" or "hands" camera. If is a video from other dataset, it must be "general"
- To choose the channel of information, **RGB**, **IR** or **DEPTH**, you must specify it with the **@channels** variable. You can define a list of channesl: ["ir","rgb","depth"]. For videos from other datasets, it must be only ["rgb"].
- You can make a list of the **classes** you want to get the frame intervals of (e.g. [“safe_drive”,"drinking"]) and assing it to the **@annotations** variable. Objects (cellphone, hair comb and bottle) have to be with the 'object_in_scene/__' label before. The var @self.actionList will get all the classes available in VCD
- If you want to export and create/write material in a **destination folder**, you must set **@write** variable to True.
- If you wish to **cut** the frame intervals to subintervals, the **size** of the final subintervals can be set in **@intervalChunk** variable. 
- Sometimes not all frame intervals can be cutted because they are smaller than the @intervalChunk. To **ignore** and not export these **smaller frame intervals**, set **@ignoreSmall** to True
- To decide where to start cutting the frame intervals, change the **@asc** variable. True to start from the **first frame** and False to start from the **last frame** and go backwards.

You can read more details about depth data and how to export it on the [DMD-Depth-Material](https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki/DMD-Depth-Material) page of the wiki.

## Changelog
For a complete list of changes check the [CHANGELOG.md](../CHANGELOG.md) file

:warning: If you find any bug with the tool or have ideas of new features please open a new issue using the [bug report template](../docs/issue_bug_template.md) or the [feature request template](../docs/issue_feature_template.md) :warning:
