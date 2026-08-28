# Driver Monitoring Dataset (DMD)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Website](https://img.shields.io/badge/Official-Website-blue)](http://dmd.vicomtech.org/)
[![Wiki](https://img.shields.io/badge/Project-Wiki-green)](https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki)

The **Driver Monitoring Dataset (DMD)** is a comprehensive visual dataset designed for real-world driving action recognition. It features synchronized footage from multiple camera angles to support the development of Deep Learning models for Driver Monitoring Systems (DMS).

> [!IMPORTANT]
> **Dataset Revision (2026):** Due to license updates and hosting constraints, the dataset has been streamlined. Simulator recordings, IR, and Depth streams have been removed. **Only RGB material from the real-car scenario is currently available.**
> 
> To comply with revised privacy and licensing agreements, only material from the following subjects is unrestricted for use:
> ### 👥 **Subject IDs:** 1, 5, 6, 7, 9, 10, 13, 14, 23, 28, 29, 33, 36, 37

---

## 📊 Dataset Highlights
The DMD provides rich annotations for distraction, fatigue, and gaze-head pose estimation.

| Feature | Description |
| :--- | :--- |
| **Scenarios** | Real-car driving (Simulator data deprecated) |
| **Streams** | RGB (Body, Face, and Hands views) |
| **Format** | [OpenLABEL](https://www.asam.net/standards/detail/openlabel/) / [VCD (Video Content Description)](https://vcd.vicomtech.org/) |
| **Labels** | Distraction actions, fatigue levels, gaze, and head pose |



---

## 🛠 Available Tools
This repository provides the essential ecosystem for interacting with DMD data:

* **[TaTo (Temporal Annotation Tool)](annotation-tool/README.md):** A specialized tool for annotating temporal actions and events.
* **[DEx (Dataset Explorer)](exploreMaterial-tool/README.md):** A tool to inspect annotated data and export customized training sets.

### Annotation Standards
To ensure consistency across annotators, we follow strict criteria:
* **[Distraction-related Action Criteria](https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset/wiki/DMD-distraction-related-action-annotation-criteria):** Detailed definitions for consistent labeling.

---

## ⚠️ Known Issues
* **OpenLABEL Compatibility:** The tools and annotation files now use **VCD >= 5.0**. Make sure you download the latest annotation files and update the tools.
* **Video Formats:** All video assets are now in `.mp4` format. If you have older `.avi` versions of IR videos, please replace them with the current versions.

---

## 🎓 Research & Citation
If you use DMD in your research, please refer to the [Official Website](http://dmd.vicomtech.org/) for the preferred citation format.

## 🚀 Community & Research
The following projects and research works utilize the DMD:

* **[dmd-to-3pdd-builder](https://github.com/azizoglu/dmd-to-3pdd-builder):** A tool for building the 3 Perspective Driver Dataset (3PDD) from the Driver Monitoring Dataset (DMD).
(Please, take into consideration tha data availability update from 2026.)

### Acknowledgments
DMD was funded by the European Commission (EC) Horizon 2020 programme via the [VI-DAS project](http://www.vi-das.eu/) (Grant 690772).

**Developed with 💙 by:**
* **Paola Cañas** (pncanas@vicomtech.org)
* **Juan Diego Ortega** (jdortega@vicomtech.org)
* *Contributors:* Marcos Nieto, Mikel Garcia, Gonzalo Pierola, Itziar Sagastiberri, Itziar Urbieta, Eneritz Etxaniz, Orti Senderos.

---

## 📄 License
Copyright © 2026 Vicomtech. Published under the **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 License** (CC BY-NC-ND 4.0).

<details>
<summary><b>View License Details</b></summary>

All datasets on this page are copyright by Vicomtech and published under the Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 License. 

This means that:
* **Attribution:** You must attribute the work in the manner specified by the authors.
* **NonCommercial:** You may not use this work for commercial purposes.
* **NoDerivatives:** If you remix, transform, or build upon the material, you may not distribute the modified material.
</details>
