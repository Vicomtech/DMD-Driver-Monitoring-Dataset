import random
import shutil
import os
import glob
import sys
from pathlib import Path
# Written by Paola Cañas with <3

# groupClass(): group dataset by classes ("radio", "drinking"...)
# Dataset in folder must be organized by sessions. (s1,s2,s3...)

class groupClass():

    def __init__(self,materialPath):

        self.materialPath = materialPath
        if not Path(self.materialPath).exists():
            raise RuntimeError("Material path does not exist")

        #list all sessions folders
        session_paths = glob.glob(self.materialPath + '/*')
        session_paths.sort()

        for session in session_paths:
            #For each session folder, list all classes folders
            class_paths = glob.glob(session + '/*')
            class_paths.sort()

            for classF in class_paths:
                subClass = glob.glob(classF + '/*')
                subClass.sort()
                dir = Path(subClass[0]).is_dir()
                print("dir",dir)
                #If theres a level more of folers
                if dir:
                    for subClassF in subClass:
                        class_name  = Path(classF).name
                        name  = Path(subClassF).name
                        dest = Path(self.materialPath+"/"+class_name+"/"+name)

                        os.makedirs(str(dest), exist_ok=True)
                        shutil.copytree(subClassF, str(dest),dirs_exist_ok=True)
                        print("Moving",name)
                
                else:
                    #For each class folder, get the name and make a folder in destination
                    name  = Path(classF).name
                    dest = Path(self.materialPath+"/"+name)

                    os.makedirs(str(dest), exist_ok=True)
                    shutil.copytree(classF, str(dest),dirs_exist_ok=True)
                    print("Moving",name)
                
            #Delete session folder
            shutil.rmtree(session)
        


# splitClass(): split dataset into train and test splits.
# Dataset must be organized by classes. A folder containing each class material. ("radio","drinking"...)


class splitClass():

    def __init__(self,materialPath,destination,testPercent):

        #@self.materialPath: Path of dmd dataset. (inside must be classes folders)
        #@self.destination: Path of where the dataset will be splitted in train and test folders.
        #@self.testPercent: Portion of desired material for test split. (e.g. 0.20)
        self.materialPath = materialPath
        self.destination = destination
        self.testPercent = float(testPercent)
        if not Path(self.materialPath).exists():
            raise RuntimeError("Material path does not exist")
        
        if self.testPercent>1.0 or self.testPercent<=0:
            raise RuntimeError("Invalid percent for test split. Must be a number 0.0> and <1.0")
        
        #Create train and test folders in destination
        os.makedirs( self.destination + "/train", exist_ok=True)
        os.makedirs( self.destination + "/test", exist_ok=True)
        
        #List all classes folders
        label_paths = glob.glob(self.materialPath + '/*')
        label_paths.sort()
        print("folders: ",label_paths)
        for count,cl in enumerate(label_paths):
            #For each class folder, list all files
            files =  glob.glob(str(cl) + '/*')
            #split file list in two by @testPercent
            train, test = self.partitionFiles(files)
            print("Moving ", len(files), " files: ",len(train)," for training and ",len(test)," for testing.")

            #Create class folder in train and test folders
            os.makedirs( self.destination + "/train/"+ str(count)+"/", exist_ok=True)
            os.makedirs(self.destination + "/test/" + str(count) + "/", exist_ok=True)
            
            #Move files from each partition to their correspondant folder
            for f in train:
                shutil.move(f,  self.destination + "/train/" + str(count)+"/")
            for f in test:
                shutil.move(f,  self.destination + "/test/" + str(count)+"/")

    def partitionFiles(self,files_list):
        #Calculate number of files for test partition
        howManyNumbers = int(round(self.testPercent * len(files_list)))
        shuffled = files_list[:]
        random.seed(123)
        #shuffle list of files
        random.shuffle(shuffled)
        #return partitions
        return shuffled[howManyNumbers:], shuffled[:howManyNumbers]


