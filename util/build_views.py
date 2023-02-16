import os
import io
import numpy as np
from dicom_utils import get_cts
from PIL import Image, ImageEnhance, ImageOps
import json
import shutil
import config as CONFIG

'''
This scrip is to copy DICOM CT files from  a source folder to dicombine database
Source file should contain a folder per one DICOM CT file and each 
DICOM CT file should contain dicom (.dcm) images.
example:  source_image_path
Images
 ├── P1
 │   ├── ct1.dcm
 │   ├── ct2.dcm
 │   └── ...
 ├── P2
 │   ├── ct1.dcm
 │   ├── ct2.dcm
 │   └── ...

** NOTE: file nale should contain ct in the name
'''
source_image_path = CONFIG.SOURCE_IMAGE_REPOSITORY
imaging_db =  CONFIG.DICOMBINE_IMAGES_DB

def transfer_files():
    CT_tag = 'ct'
    if not os.path.exists(imaging_db):
        os.makedirs(imaging_db)

    transfered_images = os.listdir(imaging_db)
    source_images = [f for f in os.listdir(source_image_path) 
            if os.path.isdir(os.path.join(source_image_path, f))]
    N = len(source_images)
    n = 0
    for imaging_file in source_images[n:]:
        n +=  1 
        print ("%s: %s/%s"%(imaging_file,n,N))
        if imaging_file  in transfered_images:
            shutil.rmtree(os.path.join(imaging_db, imaging_file)) 
        os.makedirs(os.path.join(imaging_db, imaging_file))
        os.makedirs(os.path.join(imaging_db, imaging_file, 'XY'))
        ct_files = [f  for f in 
            os.listdir(os.path.join(source_image_path,imaging_file)) if CT_tag in f]
        for f in ct_files:
            src = os.path.join(source_image_path,imaging_file, f)
            dist = os.path.join(imaging_db, imaging_file, 'XY', f)
            shutil.copyfile(src, dist)

def load_dicoms(imaging_file):
    imaging_metadata = {}
    if not os.path.exists(os.path.join(imaging_db, imaging_file, 'XY')):
        os.makedirs(os.path.join(imaging_db, imaging_file, 'XY'))
        print ('ERROR: NO CT IMAGES FOR imaging %s' %imaging_file)
    imaging_metadata[imaging_file] = {}
    ct_file = [os.path.join(imaging_db, imaging_file, 'XY', f) for f in os.listdir(os.path.join(imaging_db, imaging_file, 'XY'))]
    imaging_metadata[imaging_file]['ct_array'], \
    imaging_metadata[imaging_file]['ct_array_hu'], \
    imaging_metadata[imaging_file]['ct_x'], \
    imaging_metadata[imaging_file]['ct_y'], \
    imaging_metadata[imaging_file]['ct_z'], \
    imaging_metadata[imaging_file]['ct_spacing'], \
    imaging_metadata[imaging_file]['ct_index'] = get_cts(ct_file)

    return imaging_metadata

def generate_XZ_YZ_views(imaging, imaging_metadata):
    if os.path.exists(os.path.join(imaging_db, imaging, 'XZ')):
        shutil.rmtree(os.path.join(imaging_db, imaging, 'XZ'))
    if os.path.exists(os.path.join(imaging_db, imaging, 'YZ')):
        shutil.rmtree(os.path.join(imaging_db, imaging, 'YZ'))
    
    os.makedirs(os.path.join(imaging_db, imaging, 'XZ'))
    os.makedirs(os.path.join(imaging_db, imaging, 'YZ'))

    ct_array = imaging_metadata[imaging]['ct_array_hu']
    ct_spacing = imaging_metadata[imaging]['ct_spacing']
    # print(imaging, ct_array.shape, ct_spacing)
    arr_min, arr_max = np.min(ct_array), np.max(ct_array)
    for y_val in range(ct_array.shape[1]):
        xz_arr = ct_array[:,y_val,:]
        xz_arr = 255*(xz_arr-arr_min)/(arr_max-arr_min)
        xz_img = Image.fromarray(xz_arr.astype('uint8'))
        xz_img = ImageOps.flip(xz_img)
        aspect_ratio = ct_spacing[0]/ct_spacing[2]
        if aspect_ratio < 1:
            newsize = ( xz_arr.shape[1], int(xz_arr.shape[0]/aspect_ratio))
            xz_img = xz_img.resize(newsize) 
        else:
            newsize = (int(xz_arr.shape[1]*aspect_ratio), xz_arr.shape[0],) 
            xz_img = xz_img.resize(newsize) 
        xz_imagePath = os.path.join(imaging_db, imaging, 'XZ', '%s.png'%(str(y_val).zfill(4)))
        xz_img.save(xz_imagePath)

    for x_val in range(ct_array.shape[2]):
        yz_arr = ct_array[:,:,x_val]
        yz_arr = 255*(yz_arr-arr_min)/(arr_max-arr_min)
        yz_img = Image.fromarray(yz_arr.astype('uint8'))
        yz_img = ImageOps.flip(yz_img)
        aspect_ratio = ct_spacing[1]/ct_spacing[2]
        if aspect_ratio < 1:
            newsize = ( yz_arr.shape[1], int(yz_arr.shape[0]/aspect_ratio))
            yz_img = yz_img.resize(newsize) 
        else:
            newsize = (int(yz_arr.shape[1]*aspect_ratio), yz_arr.shape[0],) 
            yz_img = yz_img.resize(newsize) 
        yz_imagePath = os.path.join(imaging_db, imaging, 'YZ', '%s.png'%(str(x_val).zfill(4)))
        yz_img.save(yz_imagePath)

def main():
    # print('YES')
    # 
    original_files = os.listdir(source_image_path)
    transfer_files()

    select_imaging = ''
    imaging_filenames = [f for f in os.listdir(imaging_db) if select_imaging in f
        and os.path.isdir(os.path.join(source_image_path, f))]

    N = len(imaging_filenames)
    n = 0
    print(imaging_filenames)
    for imaging in imaging_filenames[n:]:
        imaging_metadata = load_dicoms(imaging)
        n += 1
        print("%s: %s/%s"%(imaging,n,N))
        generate_XZ_YZ_views(imaging, imaging_metadata)


    for original_file in original_files:
        if original_file not in imaging_filenames:
            print ('imaging is missing')
        else:
            views = os.listdir(os.path.join(imaging_db,original_file))
            if 'XY' not in views:
                print ('XY is missing')
            elif len(os.listdir(os.path.join(imaging_db,original_file,'XY')))==0:
                print ('XY is empty')
            elif 'YZ' not in views:
                print ('YZ is missing')
            elif len(os.listdir(os.path.join(imaging_db,original_file,'YZ')))!=512:
                print ('YZ is not valid', original_file, len(os.listdir(os.path.join(imaging_db,original_file,'YZ'))))
            elif 'XZ' not in views:
                print ('XZ is missing')
            elif len(os.listdir(os.path.join(imaging_db,original_file,'XZ')))!=512:
                print ('XZ is not valid', original_file, len(os.listdir(os.path.join(imaging_db,original_file,'XZ'))))

if __name__ == "__main__":
    main()