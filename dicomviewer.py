import os
import io
from flask import Flask, flash, jsonify, render_template, request, send_file, url_for, send_from_directory
import numpy as np
from dicom_utils import get_cts
from PIL import Image, ImageEnhance, ImageOps
import env
import json
import csv

output_path = env.OUTPUTDATA
db = env.PATIENTS_DATABASE
# images_url = 'http://127.0.0.1:5000/images'

SERVER_IP = env.SERVER_IP
SERVER_PORT = env.SERVER_PORT

images_url = 'http://%s:%s/images'%(SERVER_IP,SERVER_PORT)
KEYS = env.VALID_KEYS


def load_dicoms(patient_file_path, patient_file):
    patient_metadata = {}
    # for patient_file in patient_filenames:
    if not os.path.exists(os.path.join(patient_file_path, patient_file, 'XY')):
        os.makedirs(os.path.join(patient_file_path, patient_file, 'XY'))
        print ('ERROR: NO CT IMAGES FOR PATIENT %s' %patient_file)
    if not os.path.exists(os.path.join(patient_file_path, patient_file, 'XZ')):
        os.makedirs(os.path.join(patient_file_path, patient_file, 'XZ'))
    if not os.path.exists(os.path.join(patient_file_path, patient_file, 'YZ')):
        os.makedirs(os.path.join(patient_file_path, patient_file, 'YZ'))
    patient_metadata[patient_file] = {}
    ct_file = [os.path.join(patient_file_path, patient_file, 'XY', f) for f in os.listdir(os.path.join(patient_file_path, patient_file, 'XY'))]
    patient_metadata[patient_file]['xz_path'] = os.path.join(patient_file_path, patient_file, 'XZ')
    patient_metadata[patient_file]['yz_path'] = os.path.join(patient_file_path, patient_file, 'YZ')
    patient_metadata[patient_file]['xy_path'] =  os.path.join(patient_file_path, patient_file, 'XY') 
    patient_metadata[patient_file]['ct_array'], \
    patient_metadata[patient_file]['ct_array_hu'], \
    patient_metadata[patient_file]['ct_x'], \
    patient_metadata[patient_file]['ct_y'], \
    patient_metadata[patient_file]['ct_z'], \
    patient_metadata[patient_file]['ct_spacing'], \
    patient_metadata[patient_file]['ct_index'], = get_cts(ct_file)
    X = ['wadouri:%s/%s/XY/%s'%(images_url,patient_file,f) for f in os.listdir(os.path.join(patient_file_path, patient_file, 'XY'))]        
    Y = patient_metadata[patient_file]['ct_index']
    # print (patient_file, patient_metadata[patient_file]['ct_array'].shape, patient_metadata[patient_file]['ct_spacing'])
    Z = [x for _,x in sorted(zip(Y,X))]
    Z.reverse()
    patient_metadata[patient_file]['xy_file'] = Z

    return patient_metadata

def window_image(image, window_center, window_width):
    img_min = window_center - window_width // 2
    img_max = window_center + window_width // 2
    window_image = image.copy()
    window_image[window_image < img_min] = img_min
    window_image[window_image > img_max] = img_max    
    return window_image

def savePoints(pid, points):
    np.savetxt('%s_points.out'%(pid), x, delimiter=',')

def load_pngs(patient_file_path, patient_metadata):
    for patient in patient_metadata:
        patient_metadata[patient]['xz_file'] = ['%s/%s/XZ/%s'%(images_url,patient,f) for f in sorted(os.listdir(os.path.join(patient_file_path, patient, 'XZ')))]
        patient_metadata[patient]['yz_file'] = ['%s/%s/YZ/%s'%(images_url,patient,f) for f in sorted(os.listdir(os.path.join(patient_file_path, patient, 'YZ')))]
        # patient_metadata[patient]['xz_file'] = os.listdir(os.path.join(patient_file_path, patient, 'XZ'))
        # patient_metadata[patient]['yz_file'] = os.listdir(os.path.join(patient_file_path, patient, 'YZ'))
    return patient_metadata


def load_stored_data(directory):
    stored_points = {}
    processed_files = os.listdir(directory)
    for processed_file in processed_files:
        patientId = os.path.splitext(os.path.basename(processed_file))[0]
        points = []
        comments = []
        stored_points[patientId] = {'points':[], 'comments':[]}
        with open(os.path.join(directory, processed_file), 'r') as stored_file:
            csvreader = csv.reader(stored_file)
            for row in csvreader:
                point = eval(row[2])
                if len(row) < 4:
                    comment = 'no good' 
                else:
                    comment = row[3]
                stored_points[patientId]['points'].append(point)
                stored_points[patientId]['comments'].append(comment)

    return stored_points



app = Flask(__name__)



app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# patient_metadata = {}



@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.cache_control.max_age = 3
    return response


@app.route("/images/<patient>/XY/<image_name>")
def get_patient_xy_image(patient, image_name):
    try:
        return send_from_directory(app.config["PATIENTS_DATA"][patient]['xy_path'], filename=image_name, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route("/images/<patient>/YZ/<image_name>")
def get_patient_yz_image(patient, image_name):
    try:
        return send_from_directory(app.config["PATIENTS_DATA"][patient]['yz_path'], filename=image_name, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route("/images/<patient>/XZ/<image_name>")
def get_patient_xz_image(patient, image_name):
    try:
        return send_from_directory(app.config["PATIENTS_DATA"][patient]['xz_path'], filename=image_name, as_attachment=True)
    except FileNotFoundError:
        abort(404)


@app.route('/_load_patients')
def load_patients():
    access_key = request.args.get('key', 0, type=str)
    if access_key in KEYS: 
        directory = '%s/%s_%s/%s'%(output_path, access_key,KEYS[access_key][0],KEYS[access_key][1])
        if not os.path.exists(directory):
            os.makedirs(directory)

        patient_file_path = db[KEYS[access_key][1]]
        patients = os.listdir(patient_file_path)
        stored_points = load_stored_data(directory)
        if len(patients) == 0:
            patients = ['DONE']
    else:
        patients = []
        stored_points = {}

    return jsonify(patients = patients, stored_points = stored_points)

# print ('>>>> ', patient_metadata)
@app.route('/_load_patient_data')
def load_patient_data():
    access_key = request.args.get('key', 0, type=str)
    patientId = request.args.get('patientId', 0, type=str)

    patient_file_path = db[KEYS[access_key][1]]

    patient_metadata = load_dicoms(patient_file_path, patientId)
    patient_metadata = load_pngs(patient_file_path, patient_metadata)
    app.config["PATIENTS_DATA"] = patient_metadata
    xy_files = patient_metadata[patientId]['xy_file']
    xz_files = patient_metadata[patientId]['xz_file']
    yz_files = patient_metadata[patientId]['yz_file']
    ct_spacings = list(patient_metadata[patientId]['ct_spacing'])
    # print (xy_files)
    # print('ct_spacings')
    # print(ct_spacings)
    return jsonify(xy_files = xy_files, 
                    xz_files = xz_files,
                    yz_files = yz_files,
                    ct_spacings = ct_spacings)



@app.route('/_post_patient_dic', methods=['POST', 'GET'])
def post_patient_dic():
    if request.method == 'POST':
        patient_dic = request.json['patient_dic']
        access_key = request.json['key']
        # print patient_dic
        for patient_id in patient_dic:
            patient_array = []
            for i in range(len(patient_dic[patient_id]['points'])):
                patient_array.append([
                                patient_dic[patient_id]['id'],
                                patient_dic[patient_id]['file_name'], 
                                patient_dic[patient_id]['points'][i],
                                patient_dic[patient_id]['comments'][i],
                                ])
            # print (scores[key]['file_name'], scores[key]['score'])
            directory = '%s/%s_%s/%s/'%(output_path, access_key,KEYS[access_key][0],KEYS[access_key][1])    
            with open('%s/%s.csv'%(directory, patient_dic[patient_id]['file_name']), 'wb') as csvfile:
                csvwriter = csv.writer(csvfile, delimiter=',')
                csvwriter.writerows(patient_array)
        return jsonify(status='stored!')



@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')



if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host=SERVER_IP, port=SERVER_PORT)
    