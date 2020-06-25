# Driver Monitoring Dataset (DMD)
The [Driver Monitoring Dataset](http://dmd.vicomtech.org/) is the largest visual dataset for real driving actions, with footage from synchronized multiple cameras (body, face, hands) and multiple streams (RGB, Depth, IR) recorded in two scenarios (real car, driving simulator). Different annotated labels related to distraction, fatigue and gaze-head pose can be used to train Deep Learning models for Driver Monitor Systems.

This project include a tool to annotate the dataset, inspect the annotated data and export training sets (in progress). Output annotations are formatted using [VCD (Video Content Description)](https://vcd.vicomtech.org/) language.

## Dataset details
More details of the recording and video material of DMD can be found at the [official website](http://dmd.vicomtech.org/)

## Available tools:
- Temporal Annotation Tool (TaTo)

## Temporal Annotation Tool (TaTo)
We have acquired a good amount of high quality and friendly driver’s material in the DMD (Driver Monitoring Dataset) with the purpose of developing computer vision algorithms for driver monitoring. But what would be a dataset without its corresponding annotations? 

We developed the TaTo tool to annotate temporal events and actions performed by the drivers in the video sequences. The tool was used to annotate a first round of distraction-related actions. However, through configuration, other labels can be annotated.   

### Dependencies:
The TaTo tool has been tested using the following system configuration:

**OS:**           Ubuntu 18.04 (on windows use WSL) <br>
**Dependencies:** Python 3, OpenCV-Python 4.2.0, VCD 4.2.0                        

For a detailed description on how to configure the running environment check [this instructions]()

### Launching TaTo
In a terminal window within the folder [annotation_tool](https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/annotation-tool) run 

    ./annotate.sh

The tool will ask you to input the **path** of the mosaic video you want to annotate. Please insert the path following the [DMD file structure]().  

### Annotation Instructions
We have detailed descriptions of how the action annotations should be done:

- [Distraction-related actions]()

## Credits
Development of DMD was supported and funded by the European Commission (EC) Horizon 2020 programme (project [VI-DAS](http://www.vi-das.eu/), grant agreement 690772) 

Developed with :blue_heart: by:

* Paola Cañas (pncanas@vicomtech.org)
* Juan Diego Ortega (jdortega@vicomtech.org)

Contributions of ideas and comments: Marcos Nieto, Mikel Garcia, Gonzalo Pierola, Itziar Sagastiberri, Itziar Urbieta, Eneritz Etxaniz, Orti Senderos. 

## License 
Copyright (c) 2020 Vicomtech

All datasets on this page are copyright by Vicomtech and published under the Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 License. This means that you must attribute the work in the manner specified by the authors, you may not use this work for commercial purposes and if you remix, transform, or build upon the material, you may not distribute the modified material.
