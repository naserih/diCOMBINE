import numpy as np
import pydicom

def convert_to_hu(dicom_file):
    bias = dicom_file.RescaleIntercept
    slope = dicom_file.RescaleSlope
    pixel_values = dicom_file.pixel_array
    new_pixel_values = (pixel_values * slope) + bias
    return new_pixel_values

def get_cts(CT_files):
    '''
    CT_files: path to the folder containing all CT slices.
    '''
    slices = {}
    slices_hu = {}
    slices_position = []
    for ct_file in CT_files:
        ds = pydicom.read_file(ct_file)
        pixel_array_hu = convert_to_hu(ds)


        # Check to see if it is an image file.
        # print ds.SOPClassUID
        if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2':
            #
            # Add the image to the slices dictionary based on its z coordinate position.
            #
            slices[ds.ImagePositionPatient[2]] = ds.pixel_array
            slices_position.append(float(ds.ImagePositionPatient[2]))
            slices_hu[ds.ImagePositionPatient[2]] = pixel_array_hu
        else:
            pass

    # The ImagePositionPatient tag gives you the x,y,z coordinates of the center of
    # the first pixel. The slices are randomly accessed so we don't know which one
    # we have after looping through the CT slice so we will set the z position after
    # sorting the z coordinates below.
    image_position = ds.ImagePositionPatient
    # print 'CT', image_position
    # Construct the z coordinate array from the image index.
    z = sorted(slices.keys())
    # z.sort()
    ct_z = np.array(z)

    image_position[2] = ct_z[0]

    # The pixel spacing or planar resolution in the x and y directions.
    ct_pixel_spacing = ds.PixelSpacing

    # Verify z dimension spacing
    b = ct_z[1:] - ct_z[0:-1]
    # z_spacing = 2.5 # Typical spacing for our institution
    if b.min() == b.max():
         z_spacing = b.max()
    else:
        print ('Error z spacing in not uniform')
        z_spacing = 0

    # print z_spacing

    # Append z spacing so you have x,y,z spacing for the array.
    ct_pixel_spacing.append(z_spacing)

    # Build the z ordered 3D CT dataset array.
    ct_array = np.array([slices[i] for i in z])
    ct_array_hu = np.array([slices_hu[i] for i in z])

    # Now construct the coordinate arrays
    # print ct_pixel_spacing, image_position
    x = np.arange(ct_array.shape[2])*ct_pixel_spacing[0] + image_position[0]
    y = np.arange(ct_array.shape[1])*ct_pixel_spacing[1] + image_position[1]
    z = np.arange(ct_array.shape[0])*z_spacing + image_position[2]
    # print x
    # print image_position[0], image_position[1], image_position[2]
    # print ct_pixel_spacing[0], ct_pixel_spacing[1], ct_pixel_spacing[2]
    # print x, y
    # print (len(x), len(y))
    # # The coordinate of the first pixel in the numpy array for the ct is then  (x[0], y[0], z[0])
    # print(slices_position)
    return ct_array, ct_array_hu, x,y,z, ct_pixel_spacing, slices_position
