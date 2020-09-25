# Driver Monitoring Dataset (DMD)
The [Driver Monitoring Dataset](http://dmd.vicomtech.org/) is the largest visual dataset for real driving actions, with footage from synchronized multiple cameras (body, face, hands) and multiple streams (RGB, Depth, IR) recorded in two scenarios (real car, driving simulator). Different annotated labels related to distraction, fatigue and gaze-head pose can be used to train Deep Learning models for Driver Monitor Systems.

This project include a tool to annotate the dataset, inspect the annotated data and export training sets (in progress). Output annotations are formatted using [VCD (Video Content Description)](https://vcd.vicomtech.org/) language.

## Dataset details
More details of the recording and video material of DMD can be found at the [official website](http://dmd.vicomtech.org/)

In addition, this repository [wiki](https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki) has useful information about the DMD dataset and the annotation process.

## Available tools:
- Temporal Annotation Tool (TaTo) - (more info [here](annotation-tool/README.md)) 
- Dataset Explorer Tool (DEx) - (more info [here](exploreMaterial-tool/README.md))
### Annotation Instructions
Depending the annotation problem, different annotation criteria should be defined to guarantee all the annotators produce the same output annotations.  

We have defined the following criteria to be used with tool to produce consistent annotations:

- [DMD Distraction-related actions](https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki/DMD-distraction-related-action-annotation-criteria) annotation


## Credits
Development of DMD was supported and funded by the European Commission (EC) Horizon 2020 programme (project [VI-DAS](http://www.vi-das.eu/), grant agreement 690772) 

Developed with :blue_heart: by:

* Paola Cañas (pncanas@vicomtech.org)
* Juan Diego Ortega (jdortega@vicomtech.org)

Contributions of ideas and comments: Marcos Nieto, Mikel Garcia, Gonzalo Pierola, Itziar Sagastiberri, Itziar Urbieta, Eneritz Etxaniz, Orti Senderos. 

## License 
Copyright :copyright: 2020 Vicomtech

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
