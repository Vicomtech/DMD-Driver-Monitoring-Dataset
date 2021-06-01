# Setting up the Temporal Annotation Tool (TaTo) - Linux

## Dependencies
The TaTo tool has been tested using the following system configuration:

**OS:**           Ubuntu 18.04, Windows 10 <br>
**Dependencies:** Python 3.8, OpenCV-Python 4.2.0, VCD 4.3.0. Add: FFMPEG and ffmpeg-python for DExTool.                        

## Environment for Ubuntu
- Please make sure you have **Python 3** installed in your system
- Verify pip is installed, if not install:
  ```bash
  sudo apt-get install python3 python3-pip
  ```
  ```bash
  pip3 install --upgrade pip
  ```
- (Optional) It is recommended to create a virtual environment in Python 3 (more info [here](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)):
  - Configure a new virtual environment:
    ```bash
    mkdir anntool_py
    ```
    ```bash
    python3 -m venv anntool_py
    ```
  - Activate the virtual environment:
    ```bash
    source anntool_py/bin/activate
    ```
- Install the dependencies
  ``` bash
  pip3 install opencv-python numpy vcd
  ```
- For DExTool, install the dependecies:
  ``` bash
  pip3 install --upgrade setuptools
  sudo apt update
  sudo apt install ffmpeg
  pip3 install ffmpeg-python
  ```
- Go to [directory](../annotation-tool) that contains the tool scripts.

## Launching TaTo
In a terminal window within the folder [annotation_tool](../annotation-tool) run:

```python
python TaTo.py
```

The tool will ask you to input the **path** of the video you want to annotate. Please insert the path following the [DMD file structure](../docs/dmd_file_struct.md).

The annotation tool TaTo opens with three windows.

## Launching DEx
In a terminal window, within the folder [exploreMaterial-tool](../exploreMaterial-tool) run 

```python
python DExTool.py
```
The tool will ask you to input the **task** you wish to perform.
