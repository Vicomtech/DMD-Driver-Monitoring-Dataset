# -*- coding: utf-8 -*-
# Created by Paola Cañas with <3
import glob
import os
import re
from pathlib import Path
from accessDMDAnn import exportClass
from group_split_material import splitClass, groupClass

print("Welcome :)")
opt = int(input("What do you whish to do?:  export material for training:[0]  group exported material by classes:[1]  create train and test split:[2] : "))

if opt == 0:
    # export material for training
    print("To change export settings go to accessDMDAnn.py and change control variables.")
    destination_path = input("Enter destination path: ")
    selec = input("How do you want to read annotations, by: Group:[g]  Sessions:[f]  One VCD:[v] : ")

    if selec == "g":
        #By group
        folder_path = input("Enter DMD group's path (../dmd/g#): ")
        #e.g /home/pncanas/Desktop/consumption/dmd/gA
        selec_session = input("Enter the session you wish to export in this group:  all:[0]  S1:[1]  S2:[2]  S3[3]  S4[4] : ")

        subject_paths = glob.glob(folder_path + '/*')
        subject_paths.sort()

        for subject in subject_paths:
            print(subject)
            session_path = glob.glob(subject + '/*')
            session_path.sort()

            for session in session_path:
                if "s"+str(selec_session) in session or selec_session == "0":
                    print(session)
                    annotation_paths = glob.glob(session + '/*.json')
                    annotation_paths.sort()

                    for annotation in annotation_paths:
                        print(annotation)
                        dmd_folder=Path(annotation).parents[3]
                        
                        exportClass(annotation,str(dmd_folder),destination_path)

                        print("Oki :) ----------------------------------------")

    elif selec == "f":
        #By session
        folder_path = input("Enter root dmd folder path(../dmd): ")
        #e.g /home/pncanas/Desktop/dmd/
        selec_session = input("Enter the session you wish to export in this group:  all:[0]  S1:[1]  S2:[2]  S3[3]  S4[4] : ")

        group_paths = glob.glob(folder_path + '/*')
        group_paths.sort()

        for group in group_paths:
            print(group)
            subject_paths = glob.glob(group + '/*')
            subject_paths.sort()

            for subject in subject_paths:
                print(subject)
                session_path = glob.glob(subject + '/*')
                session_path.sort()

                for session in session_path:
                    if "s"+str(selec_session) in session or selec_session == "0":
                        print(session)
                        annotation_paths = glob.glob(session + '/*.json')
                        annotation_paths.sort()

                        for annotation in annotation_paths:
                            print(annotation)
                            dmd_folder=Path(annotation).parents[3]

                            exportClass(annotation,str(dmd_folder),destination_path)

                            print("Oki :) ----------------------------------------")

    elif selec == "v":

        vcd_path = input("Paste the vcd file path (..._ann.json): ")
        # e.g: /Desktop/consumption/dmd/gA/1/s2/gA_1_s2_2019-03-08T09;21;03+01;00_rgb_ann.json
        regex_internal = '(?P<subject>[1-9]|[1-2][0-9]|[3][0-7])_(?P<session>[a-z]{1,})_'\
                '(?P<date>(?P<month>0[1-9]|1[012])-(?P<day>0[1-9]|[12][0-9]|3[01]))'
        regex_external = '(?P<group>g[A-z]{1,})_(?P<subject>[1-9]|[1-2][0-9]|[3][0-7])_'\
            '(?P<session>s[1-9]{1,})_(?P<timestamp>(?P<date>(?P<year>\d{4})-(?P<month>0[1-9]|1[012])-'\
                '(?P<day>0[1-9]|[12][0-9]|3[01]))T(?P<time>(?P<hour>\d{1,2});(?P<minute>\d{1,2});'\
                    '(?P<second>\d{1,2}))\+\d{1,2};\d{1,2})_(?P<channel>rgb|depth|ir)_(?P<stream>ann)'
        regex_internal = re.compile(regex_internal)
        regex_external = re.compile(regex_external)
        match_internal = regex_internal.search(str(vcd_path))
        match_external = regex_external.search(str(vcd_path))

        if match_internal or match_external:
            #dmd annotation
            dmd_folder=Path(vcd_path).parents[3]
            datasetDMD = True
        else:
            #not a dmd annotation
            dmd_folder=Path(vcd_path).parents[1]
            datasetDMD = False

        exportClass(vcd_path,str(dmd_folder),destination_path, datasetDMD)

        print("Oki :) ----------------------------------------")       

    else:
        print("__Please, select a valid option__")


elif opt == 1:
    # group exported material by classes
    material_path = input("Enter exported DMD material path (inside must be sessions folders e.g:../dmd_rgb): ")
    groupClass(material_path)

    print("Oki :) ----------------------------------------")
     
elif opt == 2:
    # create train and test split
    print("This function only works with dmd material structure when exporting with DEx tool.")
    material_path = input("Enter exported material path (inside must be classes folders): ")
    destination_path = input("Enter destination path: ")
    test_proportion = input("Enter test proportion for split [0-1] (e.g. 0.20): ")  

    splitClass(material_path,destination_path,test_proportion)

    print("Oki :) ----------------------------------------")
else:
    print("__Please, put a valid option.__")
