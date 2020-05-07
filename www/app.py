# -*- coding: UTF-8 -*-
import os
import base64
import json
import datetime
import time
import subprocess
from flask import Flask, request, render_template, flash, redirect, url_for
from shotgun_api3 import shotgun
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
FORGE_AUTH_URL = "https://developer.api.autodesk.com/authentication/v1/authenticate"
ALLOWED_EXTENSIONS = set(['obj', 'rvt', 'png', 'jpg', 'jpeg', 'gif', 'csv','zip'])
UPLOAD_FOLDER = 'upload_dir/'


# ---- FORGE URLs

################################################################################
# demo-specific values

# must be of the form  [-_.a-z0-9]{3,128}
FORGE_BUCKET_NAME = "sg_forge_demo"

################################################################################
# Forge endpoints

# base url
FORGE_DEV_SITE = "https://developer.api.autodesk.com"

client_id = 'dwpRPnV14An6mHOi7GEmRmfmSiVC8xbs'      # TODO
client_secret = 'Fd9fbf388c21a4e3'  # TODO

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

################################################################################

@app.route("/sg_version", methods = ['GET', 'POST'])
def ami_endpoint():
  return process_versions()

def process_versions():
  return request.form

@app.route("/", methods = ['GET', 'POST'])
def home():
  return render_template('%s.html' % 'index')

@app.route("/<string:page_name>", methods = ['GET', 'POST'])
def no_urn_1(page_name):
  return render_template('%s.html' % 'index')

@app.route("/<string:page_name>/", methods = ['GET', 'POST'])
def no_urn_2(page_name):
  return render_template('%s.html' % 'index')

@app.route("/forge_viewer/<string:forge_urn>", methods = ['GET', 'POST'])
def forge_viewer(forge_urn):
  return render_template('%s.html' % 'forge_viewer', forge_urn=forge_urn)


def CreateNewDir():
    global UPLOAD_FOLDER 
    UPLOAD_FOLDER = UPLOAD_FOLDER+datetime.datetime.now().strftime("%d%m%y%H")
    cmd="mkdir -p %s && ls -lrt %s"%(UPLOAD_FOLDER,UPLOAD_FOLDER)
    output = subprocess.Popen([cmd], shell=True,  stdout = subprocess.PIPE).communicate()[0]

    if "total 0" in str(output):
        print("Success: Created Directory %s"%(UPLOAD_FOLDER) )
    else:
        print("Failure: Failed to Create a Directory (or) Directory already Exists",UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
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
            urn = submit_to_forge(file_saved, filename)
            if os.path.isfile(file_saved):
              os.remove(file_saved)
            if os.path.isdir(UPLOAD_FOLDER):
              os.rmdir(UPLOAD_FOLDER)
            return redirect(url_for('uploaded_file',
                                    filename=filename, forge_urn=urn))
    return render_template('%s.html' % 'upload')


@app.route('/uploaded', methods=['GET', 'POST'])
def uploaded_file():
  filename = request.args.get("filename")
  forge_urn = request.args.get("forge_urn")
  return render_template('%s.html' % 'uploaded', filename=filename, forge_urn=forge_urn)

def submit_to_forge(model_path, object_name):

    # TODO: this is executing in the main thread. A better solution would
    # be to run this upload as a separate process that updates SG once the
    # upload/conversion is complete (time depends on file size, forge server
    # load, etc.). This code should be used for reference only.

    forge_token = get_forge_access_token()
    if not ensure_forge_bucket_exists(forge_token):
        # raise sgtk.TankError("Failed to create Forge bucket.")
        print("Failed to create Forge bucket.")

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
        print("Upload content: %s" % result.content)
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
    print("Model URN (base 64): %s" % (model_urn_base64,))

    print("Starting conversion to SVF...")

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
    print(result.content)

    # result.raise_for_status()

    # TODO: You could wait for the proper status before updating SG. Again,
    # this is not ideal for the main publish thread. You might consider a
    # separate service to handle checking for upload status and updating SG.
    # Leaving this here for reference.

    # poll for completion...
    print("Conversion submitted. Polling for completion...")

    status = None
    while status not in ["success", "failed", "timeout"]:
        result = requests.get(
            FORGE_DESIGNDATA_MANIFEST.format(base64_urn=model_urn_base64),
            headers={
                "Authorization": "Bearer {access_token}".format(
                    access_token=forge_token
                )
            }
        )
        result.raise_for_status()
        result_data = result.json()
        status = result_data["status"]
        print("Conversion status: %s" % (status,))

        time.sleep(2)

    # the last result is the one with all the info
    print(json.dumps(result.json(), indent=4, sort_keys=True))
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
        print("Failed to create forge bucket: %s" % (FORGE_BUCKET_NAME,))
        print("ERROR: " + result.text)
        return False

    return True

def download_converted_file(access_token, model_urn_base64):
    # see if the converted file already exists...
    result = requests.get(
        FORGE_DESIGNDATA_MODELDATA.format(base64_urn=model_urn_base64,format='stl'),
        headers={
            "Authorization": "Bearer {access_token}".format(
                access_token=access_token
            )
        }
    )
    if result.status_code == requests.codes.ok:
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
  return _get_forge_token(), 200

def _get_forge_token():
  # TODO: You will first need to register your app with Forge. Once you've
  # done that, you can test your code by including the id/secret here. For
  # production though, you'll want to externalize these values.
  result = requests.post(
    FORGE_AUTH_URL,
      data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "viewables:read"
      },
      headers={
        "Content-Type": "application/x-www-form-urlencoded"
      }
    )
  result.raise_for_status()
  return result.json()["access_token"]

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug = True)