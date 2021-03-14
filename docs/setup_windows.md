# Setting up the Temporal Annotation Tool (TaTo) - Windows

## Dependencies
The TaTo tool has been tested using the following system configuration:

**OS:**           Windows 10 <br>
**Dependencies:** Python 3.8, OpenCV-Python 4.2.0, VCD 4.3.0. Add: FFMPEG and ffmpeg-python for DExTool.                       

## Environment in Windows

- Verify pip is installed, if not install:

- (Optional) It is recommended to create a virtual environment in Python 3 (more info [here](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)):

- Install dependencies
  -opencv-python, numpy, vcd
  -FFMPEG and ffmpeg-python for DExTool.
  
- Go to [directory](../annotation-tool) that contains the tool scripts.

## Launching TaTo
In a terminal window, within the folder [annotation_tool](../annotation-tool) run 

```python
TaTo.py
```

The tool will ask you to input the **path** of the mosaic video you want to annotate. Please insert the path following the [DMD file structure](../docs/dmd_file_struct.md). 

The annotation tool TaTo opens with three windows.

## Launching DEx
In a terminal window, within the folder [exploreMaterial-tool](../exploreMaterial-tool) run 

```python
DExTool.py
```

The tool will ask you to input the **task** you wish to perform.
