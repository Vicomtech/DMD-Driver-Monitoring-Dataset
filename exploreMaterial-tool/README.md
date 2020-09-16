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

**OS:**           Ubuntu 18.04 (on windows use WSL) <br>
**Dependencies:** Python 3, OpenCV-Python 4.2.0, VCD 4.2.0                        

For a detailed description on how to configure the environment and launch the tool, check: [Linux](../docs/setup_linux.md) / [Windows](../docs/setup_windows.md)

## DEx characteristics
DEx was initially developed to prepare DMD distraction-related material for training. This means that for now,  it is only meant to manage frame intervals of the distraction-related activities. 

- Get a list of frame intervals of a specific activity from VCD.
- Take a list of frame intervals and divide them into subintervals of desired size. This can be done starting from the first frame of from the last frame and back.
- Export those frame intervals as video clips or images. The material can be exported from the 3 camera perspectives videos. You can choose what material to export: a group's material, a session material or just the material from a specific VCD.

## Usage Instructions
### DEx initialization 
It is recommended to initialize the tool by executing the bash file [exportLabeledData.sh](./exportLabeledData.sh). This script will guide you to prepare the DMD material. 

If you need something more specific, you can direclty implement functions from [accessDMDAnn.py](./accessDMDAnn.py) or [vcd4reader.py](./vcd4Reader.py).

### DEx export configuration
There are some export settings you can change at the end of file [accessDMDAnn.py](./accessDMDAnn.py) under “-- CONTROL VARIABLES --“ comment.
- To define the data format you wish to export, add “image” and/or “video” to @material variable as a list.
- The list of camera perspectives to export material from can be defined in @streams variable.
- You can make a list of the classes you want to get the frame intervals of (e.g. [“safe_drive”,"drinking"]) and assing it to the @annotations variable.
- If you want to export and create/write material in a destination folder, you must set @write variable to True.
- If you wish to cut the frame intervals to subintervals, the size of the final subintervals can be set in @intervalChunk variable. 
- Sometimes not all frame intervals can be cutted because they are smaller than the @intervalChunk. To ignore and not export these smaller frame intervals, set @ignoreSmall to True
- To decide where to start cutting the frame intervals, change the @asc variable. True to start from the first frame and False to start from the last frame and go backwards.

## Changelog
For a complete list of changes check the [CHANGELOG.md](../CHANGELOG.md) file

:warning: If you find any bug with the tool or have ideas of new features please open a new issue using the [bug report template](../docs/issue_bug_template.md) or the [feature request template](../docs/issue_feature_template.md) :warning:
