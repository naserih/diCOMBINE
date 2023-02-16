import os
import io
from flask import Flask, jsonify, abort, render_template, request, send_from_directory
import numpy as np
from util.dicom_utils import get_cts
from PIL import Image, ImageEnhance, ImageOps
import config as CONFIG
import json
import csv

SERVER_IP = CONFIG.SERVER_IP
SERVER_PORT = CONFIG.SERVER_PORT
db = CONFIG.IMAGES_DATABASE
output_path = CONFIG.OUTPUTDATA
images_url = 'http://%s:%s/images'%(SERVER_IP,SERVER_PORT)
KEYS = CONFIG.VALID_KEYS

class Image():
    def __init__(self, image_file_path, image_file):
        self.image_file_path = image_file_path
        self.image_file = image_file
        self.image_metadata = {}

    def load_dicoms(self):
        xy_path= os.path.join(self.image_file_path, self.image_file, 'XY')

        # for self.image_file in self.image_filenames:
        if not os.path.exists(xy_path):
                return jsonify(message=f"File is not valid: {xy_path}")
        self.image_metadata[self.image_file] = {}
        ct_file = [os.path.join(xy_path, f) for f in os.listdir(xy_path)]
        self.image_metadata[self.image_file]['xy_path'] = xy_path
        self.image_metadata[self.image_file]['ct_array'], \
        self.image_metadata[self.image_file]['ct_array_hu'], \
        self.image_metadata[self.image_file]['ct_x'], \
        self.image_metadata[self.image_file]['ct_y'], \
        self.image_metadata[self.image_file]['ct_z'], \
        self.image_metadata[self.image_file]['ct_spacing'], \
        self.image_metadata[self.image_file]['ct_index'], = get_cts(ct_file)
        X = ['wadouri:%s/%s/XY/%s'%(images_url,self.image_file,f) for f in os.listdir(xy_path)]        
        Y = self.image_metadata[self.image_file]['ct_index']
        Z = [x for _,x in sorted(zip(Y,X))]
        Z.reverse()
        self.image_metadata[self.image_file]['xy_file'] = Z

        return self.image_metadata

    def load_pngs(self):
        xz_path = os.path.join(self.image_file_path, self.image_file, 'XZ')
        yz_path = os.path.join(self.image_file_path, self.image_file, 'YZ')
        if not os.path.exists(xz_path):
            return jsonify(message=f"File is not valid: {xz_path}")
        if not os.path.exists(yz_path):
            return jsonify(message=f"File is not valid: {yz_path}")
        self.image_metadata[self.image_file]['xz_path'] = xz_path
        self.image_metadata[self.image_file]['yz_path'] = yz_path
        for image in self.image_metadata:
            self.image_metadata[image]['xz_file'] = ['%s/%s/XZ/%s'%(images_url,image,f) for f in sorted(os.listdir(xz_path))]
            self.image_metadata[image]['yz_file'] = ['%s/%s/YZ/%s'%(images_url,image,f) for f in sorted(os.listdir(yz_path))]
        return self.image_metadata

def window_image(image, window_center, window_width):
    img_min = window_center - window_width // 2
    img_max = window_center + window_width // 2
    window_image = image.copy()
    window_image[window_image < img_min] = img_min
    window_image[window_image > img_max] = img_max    
    return window_image

def savePoints(pid, points):
    np.savetxt('%s_points.out'%(pid), x, delimiter=',')

def load_stored_data(directory):
    stored_points = {}
    processed_files = os.listdir(directory)
    for processed_file in processed_files:
        imageId = os.path.splitext(os.path.basename(processed_file))[0]
        points = []
        comments = []
        met_types = []
        stored_points[imageId] = {'points':[], 'comments':[], 'met_types':[]}
        with open(os.path.join(directory, processed_file), 'r') as stored_file:
            csvreader = csv.reader(stored_file)
            for row in csvreader:
                point = eval(row[2])
                if len(row) < 4:
                    comment = '' 
                    met_type = ''
                elif len(row) == 4:
                    comment = row[3]
                    met_type = ''
                else:
                    comment = row[3]
                    met_type = row[4]

                print (met_type)
                # met_type = comment = row[4]
                stored_points[imageId]['points'].append(point)
                stored_points[imageId]['comments'].append(comment)
                stored_points[imageId]['met_types'].append(met_type)

    return stored_points



app = Flask(__name__)



app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# image_metadata = {}

@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.cache_control.max_age = 3
    return response

@app.route("/help")
def help():
    return render_template("help.html")


@app.route("/images/<image>/XY/<image_name>")
def get_image_xy_image(image, image_name):
    try:
        return send_from_directory(app.config["images_DATA"][image]['xy_path'], image_name, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route("/images/<image>/YZ/<image_name>")
def get_image_yz_image(image, image_name):
    try:
        return send_from_directory(app.config["images_DATA"][image]['yz_path'], image_name, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route("/images/<image>/XZ/<image_name>")
def get_image_xz_image(image, image_name):
    try:
        return send_from_directory(app.config["images_DATA"][image]['xz_path'], image_name, as_attachment=True)
    except FileNotFoundError:
        abort(404)


@app.route('/_load_images')
def load_images():
    access_key = request.args.get('key', 0, type=str)
    if access_key in KEYS:
        directory = '%s/%s_%s/%s'%(output_path, access_key,KEYS[access_key][0],KEYS[access_key][1])
        if not os.path.exists(directory):
            os.makedirs(directory)      

        image_file_path = db[KEYS[access_key][1]]
        images = [f for f in os.listdir(image_file_path) 
            if os.path.isdir(os.path.join(image_file_path, f))]
        stored_points = load_stored_data(directory)
        if len(images) == 0:
            images = ['DONE']
    else:
        images = []
        stored_points = {}

    return jsonify(images = images, stored_points = stored_points)

# print ('>>>> ', image_metadata)
@app.route('/_load_image_data')
def load_image_data():
    access_key = request.args.get('key', 0, type=str)
    imageId = request.args.get('imageId', 0, type=str)

    image_file_path = db[KEYS[access_key][1]]
    img = Image(image_file_path, imageId)
    img.load_dicoms()
    image_metadata = img.load_pngs()
    app.config["images_DATA"] = image_metadata
    xy_files = image_metadata[imageId]['xy_file']
    xz_files = image_metadata[imageId]['xz_file']
    yz_files = image_metadata[imageId]['yz_file']
    ct_spacings = list(image_metadata[imageId]['ct_spacing'])
    # print (xy_files)
    # print('ct_spacings')
    # print(ct_spacings)
    return jsonify(xy_files = xy_files, 
                    xz_files = xz_files,
                    yz_files = yz_files,
                    ct_spacings = ct_spacings)



@app.route('/_post_image_dic', methods=['POST', 'GET'])
def post_image_dic():
    if request.method == 'POST':
        image_dic = request.json['image_dic']
        access_key = request.json['key']
        # print image_dic
        for image_id in image_dic:
            image_array = []
            for i in range(len(image_dic[image_id]['points'])):
                image_array.append([
                                image_dic[image_id]['id'],
                                image_dic[image_id]['file_name'], 
                                image_dic[image_id]['points'][i],
                                image_dic[image_id]['comments'][i],
                                image_dic[image_id]['met_types'][i],
                                ])
            # print (scores[key]['file_name'], scores[key]['score'])
            directory = '%s/%s_%s/%s/'%(output_path, access_key,KEYS[access_key][0],KEYS[access_key][1])    
            with open('%s/%s.csv'%(directory, image_dic[image_id]['file_name']), 'w', newline="") as csvfile:
                csvwriter = csv.writer(csvfile, delimiter=',')
                csvwriter.writerows(image_array)
        return jsonify(status='stored!')



@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host=SERVER_IP, port=SERVER_PORT)
    