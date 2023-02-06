import os
import env
import shutil

ROOT = ['TEST','MET', 'CTRL'][1]
aria_database = env.ARIA_DATABASE[ROOT]
patient_file_path = env.PATIENTS_DATABASE[ROOT]

if not os.path.exists(patient_file_path):
    os.makedirs(patient_file_path)

local_patients = os.listdir(patient_file_path)
aria_patients = os.listdir(aria_database)

N = len(aria_patients)
n = 0
for patient_file in aria_patients:
    n +=  1 
    print ("%s: %s/%s"%(patient_file,n,N))
    if patient_file  in local_patients:
        shutil.rmtree(os.path.join(patient_file_path, patient_file)) 
    os.makedirs(os.path.join(patient_file_path, patient_file))
    os.makedirs(os.path.join(patient_file_path, patient_file, 'XY'))
    ct_files = [f  for f in os.listdir(os.path.join(aria_database,patient_file)) if 'CT' in f]
    for f in ct_files:
        src = os.path.join(aria_database,patient_file, f)
        dist = os.path.join(patient_file_path, patient_file, 'XY', f)
        shutil.copyfile(src, dist)
        # print(f)


