# -*- coding: UTF-8 -*-
import os
import base64
import json
import datetime
from datetime import timedelta
import time
import subprocess
import flask
from flask import Flask, request, render_template, flash, redirect, url_for,session
from shotgun_api3 import Shotgun
import requests
from werkzeug.utils import secure_filename
from datetime import timedelta
import logging
import logging.config
from logging import StreamHandler
from flask_socketio import SocketIO, emit
from random import random
from threading import Thread, Event

app = Flask(__name__)
socketio = SocketIO(app, async_mode=None, logger=True, engineio_logger=True)
ALLOWED_EXTENSIONS = set(['obj', 'rvt'])
UPLOAD_FOLDER = 'upload_dir/'


# ---- Shotgun API

SERVER_PATH = "YOUR_SHOTGUN_SITE"
SCRIPT_NAME = 'YOUR_SHOTGUN_SCRIPT_NAME'     
SCRIPT_KEY = "YOUR_SHOTGUN_SCRIPT_KEY"

sg = Shotgun(SERVER_PATH, SCRIPT_NAME, SCRIPT_KEY)

# ---- FORGE URLs

################################################################################
# demo-specific values

# must be of the form  [-_.a-z0-9]{3,128}
FORGE_BUCKET_NAME = "YOUR_FORGE_BUCKET"

################################################################################
# Forge endpoints

# base url
FORGE_SITE = "YOUR_WEB_SITE"
FORGE_DEV_SITE = "https://developer.api.autodesk.com"

client_id = 'YOUR_FORGE_ID'      # TODO
client_secret = 'YOUR_FORGE_KEY'  # TODO

# functional endpoints
FORGE_AUTHENTICATION = FORGE_DEV_SITE + "/authentication/v1/authenticate"

FORGE_BUCKETS = FORGE_DEV_SITE + "/oss/v2/buckets"
FORGE_DEMO_BUCKET = FORGE_BUCKETS + "/{bucket}".format(bucket=FORGE_BUCKET_NAME)
FORGE_BUCKET_DETAILS = FORGE_DEMO_BUCKET + "/details"

FORGE_OBJECT_UPLOAD = FORGE_DEMO_BUCKET + "/objects/{object_name}"

# FORGE_DESIGNDATA = FORGE_DEV_SITE + "/modelderivative/v2/designdata"
FORGE_DESIGNDATA = FORGE_DEV_SITE + "/modelderivative/v2/designdata"
FORGE_DESIGNDATA_JOB = FORGE_DESIGNDATA + "/job"
FORGE_DESIGNDATA_MANIFEST = FORGE_DESIGNDATA + "/{base64_urn}/manifest"
FORGE_DESIGNDATA_MODELDATA = FORGE_DESIGNDATA + "/{base64_urn}/manifest/urn:adsk.viewing:fs.file:{base64_urn}.{format}"
FORGE_DESIGNDATA_METADATA = FORGE_DESIGNDATA + "/{base64_urn}/metadata"
FORGE_DESIGNDATA_METADATA_OBJ_TREE = FORGE_DESIGNDATA + "/{base64_urn}/metadata/{guid}"
FORGE_DESIGNDATA_METADATA_OBJ_PROPERTY = FORGE_DESIGNDATA + "/{base64_urn}/metadata/{guid}/properties"

################################################################################

#random number Generator Thread
# thread = Thread()
# thread_stop_event = Event()

# def randomNumberGenerator():
#     """
#     Generate a random number every 1 second and emit to a socketio instance (broadcast)
#     Ideally to be run in a separate thread?
#     """
#     #infinite loop of magical random numbers
#     print("Making random numbers")
#     while not thread_stop_event.isSet():
#         number = round(random()*10, 3)
#         print(number, flush=True)
#         socketio.emit('newnumber', {'number': number, 'time': time.strftime("%Y-%b-%d %H:%M:%S", time.localtime((time.time())))}, namespace='/update_forge_status')
#         socketio.sleep(5)

################################################################################
@app.route("/sg_version", methods = ['GET', 'POST'])
def ami_endpoint():
    '''
    AMI TEST in version entity
    '''
    return process_versions()

def process_versions():
    '''
    AMI TEST in version entity
    '''
    return request.form

@app.route("/view_parts", methods = ['GET', 'POST'])
def view_parts():
    '''
    AMI for view parts in Shotgun Task entity
    '''
    data = request.form
    ids = data["selected_ids"]
    id_array = ids.split(',')
    forge_urn = ""
    obj_ids = ""
    for i in id_array:
        result = sg.find_one("Task", [["id", "is", int(i)]], ["content","entity.Asset.sg_forge_urn","sg_forge_object_tree"])
        objectid = result["content"]
        forge_urn = result["entity.Asset.sg_forge_urn"]
        leaf_object = result["sg_forge_object_tree"]
        leaf_json=eval(leaf_object)
        leaf_ids = get_leaf_objects(leaf_json)
        print(leaf_ids, flush=True)
        if leaf_ids == "" and obj_ids == "":
            obj_ids = objectid 
        if leaf_ids == "" and obj_ids != "":
            obj_ids = objectid + "," +  obj_ids
        if leaf_ids != "" and obj_ids != "":
            obj_ids = objectid +  "," + leaf_ids + "," +  obj_ids
        if leaf_ids != "" and obj_ids == "":
            obj_ids = objectid +  "," + leaf_ids

    return redirect(url_for('forge_viewer_ids', forge_urn=forge_urn, ids=obj_ids, _external=True, _scheme='https'))

def get_leaf_objects(objs):
    print(objs, flush=True)
    print(len(objs))
    ids = ""
    if len(objs) == 1:
        if "objects" in objs[0]:
            if ids == "":
                ids = str(objs[0]["objectid"]) + ","+ get_leaf_objects(objs[0]["objects"])
            else:
                ids = str(objs[0]["objectid"]) + ","+ get_leaf_objects(objs[0]["objects"])+"," + ids
            return ids
        else:
            return str(objs[0]["objectid"])
    else:
        for obs in objs:
            print(obs, flush=True)
            if ids == "":
                if "objects" in obs:
                    ids = str(obs["objectid"]) + ","+ get_leaf_objects(obs["objects"]) 
                else:
                    ids = str(obs["objectid"]) 
            else:
                if "objects" in obs:
                    ids = str(obs["objectid"]) + ","+ get_leaf_objects(obs["objects"]) + "," + ids
                else:
                    ids = str(obs["objectid"]) + "," + ids
        return ids
       
@app.route("/sg_asset", methods = ['GET', 'POST'])
def ami_asset_endpoint():
    '''
    AMI for Shotgun Asset entity, get forge urn and query objectid from Forge and update task entity.
    '''
    data = request.form
    id = data["selected_ids"]
    if id.isnumeric():
        objects = get_objects(int(id))
        html = objects
    else:
        html = render_template('%s.html' % 'message', message = "Please select just one asset")
    return html

def get_asset_forge_urn(id):
    '''
    Query objectid from Forge
    '''
    result = sg.find_one("Asset", [["id", "is", id]], ["id","sg_forge_urn","project"])
    asset_id = result["id"]
    forge_urn = result["sg_forge_urn"]
    print("%s" % str(forge_urn), flush=True)
    return redirect(url_for('forge_viewer_snap',forge_urn=forge_urn, asset_id=asset_id, _external=True, _scheme='https'))

def update_asset_note(image_base64, asset_id):
    asset_info = sg.find_one("Asset", [["id", "is", int(asset_id)]],["id", "project.Project.id"])
    
    data = {
        "note_links": [{"type": "Asset", "id": int(asset_id)}],
        "project": {"type": "Project", "id": asset_info['project.Project.id']},
        "subject": "Forge Review",
        "content": image_base64
    }
    result = sg.create("Note", data)
    # print(last_notes, flush=True)
    return ("Saved snapshot: %s " % str(result))

def get_asset_review_snapshot(asset_id):
    order = [{"field_name": "created_at", "direction": "desc"}]
    asset_notes = sg.find("Note", [["note_links.Asset.id", "is", int(asset_id)]],["id", "content",'created_at'],order)
    if len(asset_notes) <=0 :
        return "No review notes"
    snapshots = []
    for note in asset_notes:
        snapshot = '<div><p>{created_time}</p><p><img src="{image}"></p></div>'.format(created_time=str(note["created_at"]), image=note["content"])
        snapshots.append(snapshot)
    html = '<html><head></head><body>%s</body></html>' % "".join(snapshots)
    return (" %s " % str(html))

def get_objects (id):
    '''
    Query objectid from Forge
    '''
    result = sg.find_one("Asset", [["id", "is", id]], ["id","sg_forge_urn","project"])
    forge_urn = result["sg_forge_urn"]
    asset_id = result["id"]
    project = result["project"]

    forge_token = get_forge_access_token()
    meta_result = requests.get(
        FORGE_DESIGNDATA_METADATA.format(base64_urn=forge_urn),
        headers={
            "Authorization": "Bearer {access_token}".format(
                access_token=forge_token
            )
        }
    )

    metadata = meta_result.json()
    # print(metadata, flush=True)
    guid = metadata["data"]["metadata"][0]["guid"]
    obj_result = requests.get(
        FORGE_DESIGNDATA_METADATA_OBJ_TREE.format(base64_urn=forge_urn, guid = guid),
        headers={
            "Authorization": "Bearer {access_token}".format(
                access_token=forge_token
            )
        }
    )
    obj_tree = obj_result.json()
    # print(obj_tree, flush=True)

    property_result = requests.get(
    FORGE_DESIGNDATA_METADATA_OBJ_PROPERTY.format(base64_urn=forge_urn, guid = guid),
        headers={
            "Authorization": "Bearer {access_token}".format(
                access_token=forge_token
            )
        }
    )
    property_json = property_result.json()

    data = {
        'sg_forge_property_json': str(property_json),
        'sg_forge_tree_json': str(obj_tree),
    }
    sg.update("Asset", id, data)

    objects = obj_tree["data"]["objects"][0]["objects"]
    return update_asset_tasks(asset_id, objects, project)

def update_asset_tasks(asset_id, objects, project):
    '''
    Update Task
    '''
    batch_data = []

    print(objects, flush=True)
    for o in objects:
        objectid = str(o["objectid"])
        objectname = o["name"]
        link_entity = {"type": "Asset", "id": asset_id}

        if "objects" in o:
            obj_tree = o["objects"]
        else:
            obj_tree = []
        data = {
            "request_type": "create", 
            "entity_type": "Task", 
            "data": {
                "content": objectid, 
                "sg_description": objectname, 
                "sg_forge_object_tree": str(obj_tree), 
                "entity":link_entity, 
                "project": project
                }
            }
        batch_data.append(data)
    sg.batch(batch_data)
    html = render_template('%s.html' % 'message', message = "Asset objects are created. Please refresh Tasks to show objectids.")
    return html

@app.route("/", methods = ['GET', 'POST'])
def home():
    '''
    Show introduction
    '''
    this_site = 'https://%s' % request.host
    homehtml = render_template('%s.html' % 'index', this_site_url = this_site)
    return homehtml

@app.route("/<string:page_name>", methods = ['GET', 'POST'])
def no_urn_1(page_name):
    '''
    If the page isn't find. Show introduction
    '''
    this_site = 'https://%s' % request.host
    homehtml = render_template('%s.html' % 'index', this_site_url = this_site)
    return homehtml

@app.route("/<string:page_name>/", methods = ['GET', 'POST'])
def no_urn_2(page_name):
    '''
    If the page isn't find. Show introduction
    '''
    this_site = 'https://%s' % request.host
    homehtml = render_template('%s.html' % 'index', this_site_url = this_site)
    return homehtml

@app.route("/forge_viewer/<string:forge_urn>", methods = ['GET', 'POST'])
def forge_viewer(forge_urn):
    '''
    Show model in forge viewer
    '''
    ids = ""
    return render_template('%s.html' % 'forge_viewer', sg_site = SERVER_PATH, sg_script=SCRIPT_NAME, sg_key = SCRIPT_KEY, forge_site= FORGE_SITE, forge_urn=forge_urn, ids=ids)

@app.route("/forge_viewer/<string:forge_urn>/<string:ids>", methods = ['GET', 'POST'])
def forge_viewer_ids(forge_urn, ids):
    '''
    Show selected objectids in forge viewer
    '''
    ids = ids
    return render_template('%s.html' % 'forge_viewer',sg_site = SERVER_PATH, sg_script=SCRIPT_NAME, sg_key = SCRIPT_KEY, forge_site= FORGE_SITE,  forge_urn=forge_urn, ids=ids)


@app.route("/review_notes", methods = ['GET', 'POST'])
def ami_asset_review_notes_endpoint():
    '''
    AMI for Shotgun Asset entity, show review snapshot
    '''
    data = request.form
    print("%s" % str(data), flush=True)
    id = data["selected_ids"]
    print("%s" % str(id), flush=True)
    if id.isnumeric():
        objects = get_asset_review_snapshot(int(id))
        print("%s" % str(objects), flush=True)
        html = objects
    else:
        html = render_template('%s.html' % 'message', message = "Please select just one asset")
    return html


@app.route("/review", methods = ['GET', 'POST'])
def ami_asset_review_endpoint():
    '''
    AMI for Shotgun Asset entity, start review page.
    '''
    data = request.form
    print("%s" % str(data), flush=True)
    id = data["selected_ids"]
    print("%s" % str(id), flush=True)
    if id.isnumeric():
        objects = get_asset_forge_urn(int(id))
        print("%s" % str(objects), flush=True)
        html = objects
    else:
        html = render_template('%s.html' % 'message', message = "Please select just one asset")
    return html

@app.route("/forge_review_notes", methods = ['POST'])
def forge_review_notes():
    '''
    Submit review notes and snapshot to shotgun
    '''
    image_dir="images/"
    if request.method == 'POST':
        # asset_id = request.form["asset_id"]
        # image_data = request.form["image_base64"].split(";")[1]
        # image_base64 = request.form["image_base64"].split(",")[1]
        # filename = os.path.join(image_dir, ("%s.txt" % asset_id))
        # print(filename, flush=True)
        # print(type(image_data.encode()), flush=True)
        # print(type(image_data), flush=True)
        # with open(filename, "w") as fh:
        #     print("filename: %s" % filename, flush=True)
        #     result = fh.write(image_data)
        #     print("result: %s" % result, flush=True)
        html = update_asset_note(request.form["image_base64"], request.form["asset_id"])
        return str(html)
        #html = render_template('%s.html' % 'message', message = request.form["image_base64"] + " " + request.form["notes"]+ " " + request.form["asset_id"])
        # return ('<html><head></head><body><img src="%s"></body></html>' % request.form["image_base64"])

@app.route("/forge_viewer_snap/<string:forge_urn>/<string:asset_id>", methods = ['GET', 'POST'])
def forge_viewer_snap(forge_urn, asset_id):
    '''
    Forge viewer with snap shot
    '''
    return render_template('%s.html' % 'forge_viewer_snap', forge_site= FORGE_SITE, forge_urn=forge_urn, asset_id = asset_id)

def CreateNewDir():
    '''
    Create tempary folder for uploaded model
    '''
    global UPLOAD_FOLDER 
    UPLOAD_FOLDER = UPLOAD_FOLDER+datetime.datetime.now().strftime("%d%m%y%H")
    cmd="mkdir -p %s && ls -lrt %s"%(UPLOAD_FOLDER,UPLOAD_FOLDER)
    output = subprocess.Popen([cmd], shell=True,  stdout = subprocess.PIPE).communicate()[0]

    if "total 0" in str(output):
        print("Success: Created Directory %s"%(UPLOAD_FOLDER), flush=True)
    else:
        print("Failure: Failed to Create a Directory (or) Directory already Exists",UPLOAD_FOLDER, flush=True)

def allowed_file(filename):
    '''
    Only accept obj and revit file
    '''
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    '''
    Upload to forge and trigger convert to svf
    '''
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            CreateNewDir()
            global UPLOAD_FOLDER 
            file_saved = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_saved)
            print(filename)
            if filename.rsplit('.', 1)[1].lower() == 'obj':
                urn = submit_to_forge_obj(file_saved, filename)
            elif filename.rsplit('.', 1)[1].lower() == 'rvt':
                urn = submit_to_forge_revit(file_saved, filename)
            if os.path.isfile(file_saved):
              os.remove(file_saved)
            if os.path.isdir(UPLOAD_FOLDER):
              os.rmdir(UPLOAD_FOLDER)
            
            # return ('<p>File: {filename} </p><br/><p>Forge URN: {forge_urn}</p>'.format(filename=filename, forge_urn=urn))
            return redirect(url_for('uploaded_file', filename=filename, forge_urn=urn))
    return render_template('%s.html' % 'upload')

@app.route('/uploaded', methods=['GET', 'POST'])
def uploaded_file():
    '''
    Upload finished.
    '''
    filename = request.args.get("filename")
    forge_urn = request.args.get("forge_urn")
    return render_template('%s.html' % 'uploaded', filename=filename, forge_urn=forge_urn)

# @socketio.on('connect', namespace='/update_forge_urn')
# def test_connect():
#     # need visibility of the global thread object
#     global thread
#     print('Client connected')

#     #Start the random number generator thread only if the thread has not been started before.
#     if not thread.isAlive():
#         print("Starting Thread", flush=True)
#         thread = socketio.start_background_task(randomNumberGenerator)

# @socketio.on('disconnect', namespace='/update_forge_urn')
# def test_disconnect():
#     print('Client disconnected', flush=True)

def submit_to_forge_obj(model_path, object_name):
    # TODO: this is executing in the main thread. A better solution would
    # be to run this upload as a separate process that updates SG once the
    # upload/conversion is complete (time depends on file size, forge server
    # load, etc.). This code should be used for reference only.

    forge_token = get_forge_access_token()
    if not ensure_forge_bucket_exists(forge_token):
        # raise sgtk.TankError("Failed to create Forge bucket.")
        print("Failed to create Forge bucket.", flush=True)

    # upload the model
    with open(model_path, 'rb') as f:
        result = requests.put(
            FORGE_OBJECT_UPLOAD.format(object_name=object_name),
            headers={
                "Authorization": "Bearer {access_token}".format(
                    access_token=forge_token
                ),
                "Content-Type": "application/octet-stream",
            },
            data=f
        )
        print("Upload content: %s" % result.content, flush=True)
        # result.raise_for_status()
        # result.status_code

    # if we're here, upload was successful. get the URN for the model
    result_data = result.json()
    model_urn = result_data["objectId"]

    print("Model uploaded: %s" % (model_urn,))

    #Python 3
    model_urn_base64 = base64.b64encode(model_urn.encode()).decode('utf-8').rstrip("=")
    
    #Python 2
    # model_urn_base64 = base64.b64encode(model_urn).decode('utf-8').rstrip("=")
    print("Model URN (base 64): %s" % (model_urn_base64,), flush=True)

    print("Starting conversion to SVF...", flush=True)

    # convert to SVF format on the server. this is required for viewing the
    # model using the forge viewer API
    result = requests.post(
        FORGE_DESIGNDATA_JOB,
        headers={
            "Authorization": "Bearer {access_token}".format(
                access_token=forge_token
            ),
            "Content-Type": "application/json",
            "x-ads-force": "true",
        },
        json={
            "input": {
                "urn": model_urn_base64
            },
            "output": {
                "formats": [
                    {
                        "type": "svf",
                        "views": ["2d", "3d"]
                    }
                ]
            }
        }
    )
    print(result.content, flush=True)

    # result.raise_for_status()

    # TODO: You could wait for the proper status before updating SG. Again,
    # this is not ideal for the main publish thread. You might consider a
    # separate service to handle checking for upload status and updating SG.
    # Leaving this here for reference.

    # poll for completion...
    # print("Conversion submitted. Polling for completion...", flush=True)

    # status = None
    # while status not in ["success", "failed", "timeout"]:
    #     result = requests.get(
    #         FORGE_DESIGNDATA_MANIFEST.format(base64_urn=model_urn_base64),
    #         headers={
    #             "Authorization": "Bearer {access_token}".format(
    #                 access_token=forge_token
    #             )
    #         }
    #     )
    #     # result.raise_for_status()
    #     result_data = result.json()
    #     status = result_data["status"]
    #     print("Conversion status: %s" % (status,), flush=True)

    #     time.sleep(10)

    # # the last result is the one with all the info
    # print(json.dumps(result.json(), indent=4, sort_keys=True), flush=True)
    return model_urn_base64

def submit_to_forge_revit(model_path, object_name):
    # TODO: this is executing in the main thread. A better solution would
    # be to run this upload as a separate process that updates SG once the
    # upload/conversion is complete (time depends on file size, forge server
    # load, etc.). This code should be used for reference only.

    forge_token = get_forge_access_token()
    if not ensure_forge_bucket_exists(forge_token):
        # raise sgtk.TankError("Failed to create Forge bucket.")
        print("Failed to create Forge bucket.", flush=True)

    # upload the model
    with open(model_path, 'rb') as f:
        result = requests.put(
            FORGE_OBJECT_UPLOAD.format(object_name=object_name),
            headers={
                "Authorization": "Bearer {access_token}".format(
                    access_token=forge_token
                ),
                "Content-Type": "application/octet-stream",
            },
            data=f
        )
        print("Upload content: %s" % result.content, flush=True)
        # result.raise_for_status()
        # result.status_code

    # if we're here, upload was successful. get the URN for the model
    result_data = result.json()
    model_urn = result_data["objectId"]

    print("Model uploaded: %s" % (model_urn,), flush=True)

    #Python 3
    model_urn_base64 = base64.b64encode(model_urn.encode()).decode('utf-8').rstrip("=")
    
    #Python 2
    # model_urn_base64 = base64.b64encode(model_urn).decode('utf-8').rstrip("=")
    print("Model URN (base 64): %s" % (model_urn_base64,), flush=True)

    print("Starting conversion to SVF...", flush=True)

    # convert to SVF format on the server. this is required for viewing the
    # model using the forge viewer API
    result = requests.post(
        FORGE_DESIGNDATA_JOB,
        headers={
            "Authorization": "Bearer {access_token}".format(
                access_token=forge_token
            ),
            "Content-Type": "application/json",
            "x-ads-force": "true",
        },
        json={
            "input": {
                "urn": model_urn_base64
            },
            "output": {
                "formats": [
                    {
                        "type": "svf",
                        "views": ["2d", "3d"],
                        "advanced": {
                            "generateMasterViews": True
                        }
                    }
                ]
            }
        }
    )
    print("request.post result: %s" % result.content, flush=True)

    # result.raise_for_status()

    # TODO: You could wait for the proper status before updating SG. Again,
    # this is not ideal for the main publish thread. You might consider a
    # separate service to handle checking for upload status and updating SG.
    # Leaving this here for reference.

    # poll for completion...
    # print("Conversion submitted. Polling for completion...", flush=True)
            
    # status = None
    # while status not in ["success", "failed", "timeout"]:
    #     # print("forge token: %s" % (forge_token,), flush=True)
    #     result = requests.get(
    #         FORGE_DESIGNDATA_MANIFEST.format(base64_urn=model_urn_base64),
    #         headers={
    #             "Authorization": "Bearer {access_token}".format(
    #                 access_token=forge_token
    #             )
    #         }
    #     )
    #     print("Conversion status: %s" % (result,), flush=True)
    #     # result.raise_for_status()
    #     result_data = result.json()
    #     status = result_data["status"]
    #     # print("Conversion status: %s" % (status,), flush=True)

    #     time.sleep(10)

    # the last result is the one with all the info
    # print(json.dumps(result.json(), indent=4, sort_keys=True), flush=True)
    return model_urn_base64

def ensure_forge_bucket_exists(access_token):
    # see if the bucket already exists...
    result = requests.get(
        FORGE_BUCKET_DETAILS.format(bucket_name=FORGE_BUCKET_NAME),
        headers={
            "Authorization": "Bearer {access_token}".format(
                access_token=access_token
            )
        }
    )
    if result.status_code == requests.codes.ok:
        return True

    # bucket doesn't exists. create it
    result = requests.post(
        FORGE_BUCKETS,
        json={
            "bucketKey": FORGE_BUCKET_NAME,
            "policyKey": "persistent"
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {access_token}".format(
                access_token=access_token
            )
        }
    )

    if result.status_code != requests.codes.ok:
        print("Failed to create forge bucket: %s" % (FORGE_BUCKET_NAME,), flush=True)
        print("ERROR: " + result.text, flush=True)
        return False

    return True

def get_forge_access_token():
    # TODO: You will first need to register your app with Forge. Once you've
    # done that, you can test your code by including the id/secret here. For
    # production though, you'll want to externalize these values and access them
    # here.

    result = requests.post(
        FORGE_AUTHENTICATION,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "data:read data:write bucket:create bucket:read"
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    result.raise_for_status()
    return result.json()["access_token"]

@app.route("/token", methods = ['GET', 'POST'])
def forge_token():
  # NOTE: there is a lack of proper authentication here. You'll need
  # to consider where and how you might run code like this. You should
  # never expose access tokens on a non secure connection or on a
  # non-private network. This is purely for demo purposes and should
  # not be considered ready for production
  # end_headers()
  return get_forge_access_token(), 200

if __name__ == "__main__":
    socketio.run(host="0.0.0.0", debug = True)
    # Setup logging
    # gunicorn_logger = logging.getLogger('gunicorn.error')
    # app.logger.handlers = gunicorn_logger.handlers
    # app.logger.handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - level=%(levelname)s - request_id=%(request_id)s - %(message)s"))
    # app.logger.handler.addFilter(RequestIDLogFilter())  # << Add request id contextual filter
    # logging.getLogger().addHandler(app.logger.handler)
    logging.basicConfig(level=logging.DEBUG)
    gunicorn_logger = logging.getLogger('gunicorn.error')
    # gunicorn_logger.setLevel(level=logging.DEBUG)
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)