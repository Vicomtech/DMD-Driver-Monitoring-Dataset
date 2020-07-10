# Temporal Annotation Tool (TaTo)
We have acquired a good amount of high quality and friendly driver’s material in the DMD (Driver Monitoring Dataset) with the purpose of developing computer vision algorithms for driver monitoring. But what would be a dataset without its corresponding annotations? 

We developed the TaTo tool to annotate temporal events and actions performed by the drivers in the video sequences. The tool was used to annotate distraction-related actions. However, through configuration, other labels can be annotated.   

## Content
- [Temporal Annotation Tool (TaTo)](#temporal-annotation-tool-tato)
  - [Content](#content)
  - [Setup and Launching](#setup-and-launching)
  - [TaTo characteristics](#tato-characteristics)
  - [Usage Instructions](#usage-instructions)
    - [TaTo Window description](#tato-window-description)
    - [Annotating with TaTo](#annotating-with-tato)
      - [Select the annotation level](#select-the-annotation-level)
      - [Annotation Modes](#annotation-modes)
        - [Frame-by-frame annotation](#frame-by-frame-annotation)
        - [Block annotation](#block-annotation)
      - [Keyboard Interaction](#keyboard-interaction)
        - [General keys](#general-keys)
        - [Video Navigation](#video-navigation)
        - [Playback keys](#playback-keys)
        - [Annotation keys](#annotation-keys)
  - [Saving annotations](#saving-annotations)
  - [Annotation criteria](#annotation-criteria)
  - [Changelog](#changelog)
  - [FAQs](#faqs)
  - [Known Issues](#known-issues)
  - [License](#license)

## Setup and Launching
The TaTo tool has been tested using the following system configuration:

**OS:**           Ubuntu 18.04 (on windows use WSL) <br>
**Dependencies:** Python 3, OpenCV-Python 4.2.0, VCD 4.2.0                        

For a detailed description on how to configure the environment and launch the tool, check: [Linux](../docs/setup_linux.md) / [Windows](../docs/setup_windows.md)

## TaTo characteristics
Although TaTo was originally developed to tackle the temporal action annotation of the [DMD dataset](http://dmd.vicomtech.org/), we have included functions which can be applied to other action annotation problems, such as:

- Allows the annotation of temporal events in videos. 
- The annotations could be divided in up to 7 different annotation levels(group of labels). Within each group the labels are **mutually exclusive.**
- The labels could be input either frame-by-frame or by frame-block interval.  
- The output annotations are saved in a JSON file in [VCD format](https://vcd.vicomtech.org/). 

## Usage Instructions
### TaTo Window description 
The annotation tool TaTo opens with three windows: 

![Annotation Tool](../docs/imgs/annotation_tool_info.png)

The main window will display:
- The **mosaic video** consisting of three camera streams (these streams were previously synchronized).
- Frame information (current frame). The **current frame** is the mosaic frame. 
- The last time you saved your annotation (It is recommended to save your progress frequently).
- The [**annotation info**](#select-the-annotation-level) panel shows a list of levels (annotation groups) and the current label for each level at the current frame. **The level you are currently annotating is indicated with the “->” sign and is written in bold in the “Annotation info” Panel.**   

A second window (with dark background) will show:
- The **frame offsets** between video streams
- The **video path** you are annotating. 
- A list of the available **labels** within the current selected annotation level. Each label will have a colored box and the key to press for annotation in brackets [ ]. Check [annotation instructions](#annotating-with-tato) to know how to input annotation for each level. 
- An informative list of the frame validation state. 

In the third window there are **two timelines** which show all the video annotations in colors, depending on the level:
- The first is a full timeline from frame 0 to the total length of the video.
- The second is a zoomed timeline around the current frame always keeping the actual frame in the center of the window. This timeline helps the visualization of individual frame label.

The colors in the timeline representation are the same as the colors in the label description panel. The colors and labels depend on the selected annotation level.

When there are 5 frames left, there will appear a “last frames” text and a “LAST FRAME!” text at the last frame. 

### Annotating with TaTo
The interaction with the tool is meant to be done using the keyboard.  We have a thorough list of keys available for interaction and annotation.

#### Select the annotation level
An annotation level is a group of labels which are mutually exclusive (two or more labels of the same level cannot be assigned to the same frame). The definition of these levels and the corresponding labels is taken from a [config file](../annotation-tool/config.json).  

There are some annotation levels which require all frames to have a label. However, other levels can admit frames with empty labels. This depends on the nature of the annotation level. Annotation levels with empty labels will include this option in the config file. 

The first step to start annotating a video is to **select the annotation level**. You can see the current selected level in the main window's levels panel (see figure below). The current selected level will display an arrow "->" symbol and the current label will be highlighted in bold text. To change between levels use the <kbd>Tab</kbd> key.

![Levels Panel](../docs/imgs/level_panel.png)

#### Annotation Modes
The annotation tool has two modes of annotation: **frame-by-frame** and **block** annotation.

##### Frame-by-frame annotation
This is the basic annotation mode. To annotate frame-by-frame you should first [select the annotation level](#select-the-annotation-level) you would want to annotate. Then, press the corresponding [label key](#annotation-keys) according to the list of available labels located in the window with dark background. The key to press will be in brackets [ ] on the left of each label. 

##### Block annotation
This is a handy way to annotate a frame interval. For this, you should first select the frame interval to be annotated. To do so, press the <kbd>Z</kbd> key to select the starting frame. Then, move forward or backward with the [navigation keys](#video-navigation). You will see in the timeline window your selection of the frame interval in green. After selecting the desired frame interval, press the corresponding [label key](#annotation-keys) to annotate all frames in the interval.      

To unselect a frame interval press two times the <kbd>Z</kbd> key. 

![block_annotation](../docs/imgs/block_annotation.png)

#### Keyboard Interaction
##### General keys
|       Keys       |                    Function                      |
| :--------------: | :----------------------------------------------- |
| <kbd>Esc</kbd>   | **Close** the tool, saving the current progress  |
| <kbd>Enter</kbd> | **Save** the current annotation progress         |
| <kbd>P</kbd>     | Open a help window showing the available keys    |

##### Video Navigation
|        Keys        |                        Function                          |
| :----------------: | :------------------------------------------------------- |
| <kbd>Any Key</kbd> | Besides function specific keys, move forward **1 frame** |
| <kbd>E</kbd>       | Move **forward 50 frames**                               |
| <kbd>R</kbd>       | Move **forward 300 frames**                              |
| <kbd>W</kbd>       | Move **backwards 50 frames**                             |
| <kbd>Q</kbd>       | Move **backwards 300 frames**                            |
| <kbd>Space</kbd>   | Move **backwards 1 frame**                               |
| <kbd>S</kbd>       | **Jump forward** to nearest label change                 |
| <kbd>A</kbd>       | **Jump backwards** to nearest label change               |

##### Playback keys
|         Keys         |                                                 Function                                                      |
| :------------------: | :------------------------------------------------------------------------------------------------------------ |
| <kbd>Backspace</kbd> | Opens the **playback of the video** in a new window.                                                          |
| <kbd>Enter</kbd>     | In the playback window, closes the playback window returning to the main window at the **last frame played**  |
| <kbd>Esc</kbd>       | In the playback window, closes the playback window returning to the main window at the **first frame played** |

##### Annotation keys
|       Keys       |                    Function                                               |
| :--------------: | :------------------------------------------------------------------------ |
| <kbd>Tab</kbd>   | **Switch** between annotation levels                                      |
| <kbd>Z</kbd>     | **Select/Unselect** the starting frame for block annotation (key-frame)   |  
| <kbd>0</kbd>...<kbd>9</kbd>, <kbd>/</kbd>, <kbd>*</kbd>, <kbd>-</kbd>, <kbd>+</kbd> | **Annotate** the frame or frame interval with the corresponding label.                         |
| <kbd>.</kbd> | **Remove** the current label of the frame of frame interval                   |
| <kbd>X</kbd>     | Apply **automatic annotations** to other levels                           |

## Saving annotations
You can save the progress by pressing the <kbd>Enter</kbd> key. The tool also saves the progress when you exit the tool using the <kbd>Esc</kbd> key.

**The tool saves the annotations in VCD 4 format in a JSON file.**

The tool has an autosave functionality that creates two TXT files with the annotation information. The name of these files are:
 - [video_name]_autoSaveAnn-A.txt
 - [video_name]_autoSaveAnn-B.txt

**In case something occurs and the tool exits without you manually saving the progress, you can recover your progress with these temporal TXT files.**

If there was a failure in saving the VCD, you will have **both** JSON and TXT files in the video directory. If you try to run again the tool, you should receive an error telling you to keep the most recent file. If that is the case, **delete** the VCD (JSON) file and start TaTo again. 

You could know which file is taken by TaTo during start-up time, depending on the file the tool is reading the annotations from, it should print:

- *"Loading VCD ..."* if the annotations are taken from a VCD json file.
- *"Loading provisional txt annotation files ..."* if the autoSave txt files are loaded.  

## Annotation criteria 
Depending the annotation problem, different annotation criteria should be defined to guarantee all the annotators produce the same output annotations.  

We have defined the following criteria to be used with tool to produce consistent annotations:

- [DMD Distraction-related actions]() annotation

## Changelog
For a complete list of changes check the [CHANGELOG.md]() file

## FAQs
[TBA]

## Known Issues

|        Issue        |                        Solution                          |
| ------------------- | :------------------------------------------------------- |
| When pressed <kbd>Alt Gr</kbd> the tool exists abruptly  | This is caused due to a bug in the capture system dependency used in the tool. Please **Don't press** <kbd>Alt Gr</kbd> |


## License 
Copyright (c) 2020 Vicomtech

All datasets on this page are copyright by Vicomtech and published under the Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 License. This means that you must attribute the work in the manner specified by the authors, you may not use this work for commercial purposes and if you remix, transform, or build upon the material, you may not distribute the modified material.
