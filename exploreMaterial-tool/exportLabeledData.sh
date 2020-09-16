#!/bin/bash
#Created by Paola Cañas - 06-07-2020 - with <3
#Bash script to navigate through DMD folder structure, then run python script to access 
#the annotations of DMD and export material for training into desired destination folder

declare -A sesiones
sesiones["1"]="s1"
sesiones["2"]="s2"
sesiones["3"]="s3"
sesiones["4"]="s4"
sesiones["0"]="all"

echo "Welcome :) "
echo "To change export settings go to accessDMDAnn.py and change control variables."

read -p "Enter destination path: " destPath

read -p "How do you want to read annotations, by: Group:[g]  Sessions:[f]  One VCD:[v] : " SELEC

case $SELEC in
    g)  
        read -p "Enter group's path (../dmd/g#): " folder1
        #e.g /home/VICOMTECH/pncanas/Desktop/consumption/dmd/gA
        read -p "Enter the session you wish to export in this group:  all:[0]  S1:[1]  S2:[2]  S3[3]  S4[4] : " selSession
        search="${sesiones[$selSession]}"

        for Subject in $folder1/*  #Per subject inside group

            do echo "$Subject" 
            
            for Session in $Subject/*   #Per session inside subject
                do
                if [[ $Session == *$search* ]] || [ $search == "all" ];
                    then
                    echo "$Session"
                    for Annotation in $Session/*.json  #Each annotation
                        do 
                        echo "$Annotation"
                        dmdFolder="${Annotation%/*/*/*/*.*}"
                        # e.g: /home/VICOMTECH/pncanas/Desktop/consumption/dmd
        
                        python3 accessDMDAnn.py $Annotation "$dmdFolder/" $destPath 

                        echo "Oki :)  -----------------------------------------------------------------"

                    done
                fi

            done

        done
        ;;
    f)  
        read -p "Enter the session you wish to export:  all:[0]  S1:[1]  S2:[2]  S3[3]  S4[4] : " selSession
        search="${sesiones[$selSession]}"
        
        read -p "Enter root dmd folder path(../dmd): " dmdFolder
        for Grupo in $dmdFolder/* #Per group inside dmd root folder
            do echo "$Grupo"
            for Subject in $Grupo/*  #Per subject inside group

                do echo "$Subject" 
                
                for Session in $Subject/*   #Per session inside subject
                    do
                    if [[ $Session == *$search* ]] || [ $search == "all" ];
                        then
                        echo "$Session"
                        for Annotation in $Session/*.json  #Each annotation
                            do 
                            echo "$Annotation"
                            dmdFolder="${Annotation%/*/*/*/*.*}"
                            # e.g: /home/VICOMTECH/pncanas/Desktop/consumption/dmd

                            python3 accessDMDAnn.py $Annotation "$dmdFolder/" $destPath 

                            echo "Oki :)  -----------------------------------------------------------------"

                        done
                    fi

                done

            done
        done
        ;;
    v)
        read -p "Paste the vcd file path: " vcdFile
        # e.g: /home/VICOMTECH/pncanas/Desktop/consumption/dmd/gA/1/s2/gA_1_s2_2019-03-08T09;21;03+01;00_rgb_ann.json
        dmdFolder="${vcdFile%/*/*/*/*.*}"
        # e.g: /home/VICOMTECH/pncanas/Desktop/consumption/dmd

        python3 accessDMDAnn.py $vcdFile "$dmdFolder/" $destPath 
        ;;
    *)
        echo "__Please, put a valid option: Group:[g]  Session:[f]  One VCD:[v]__"
        ;;
esac

