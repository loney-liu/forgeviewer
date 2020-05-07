import os
import datetime
import subprocess
from flask import Flask, request, render_template, flash, redirect, url_for
from shotgun_api3 import shotgun
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
FORGE_AUTH_URL = "https://developer.api.autodesk.com/authentication/v1/authenticate"
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv','zip'])
UPLOAD_FOLDER = 'upload_dir/'

@app.route("/sg_version", methods = ['GET', 'POST'])
def ami_endpoint():
  return process_versions()

def process_versions():
  return request.form

@app.route("/<string:page_name>", methods = ['GET', 'POST'])
def no_urn_1(page_name):
  return "Please input Forge URN"

@app.route("/<string:page_name>/", methods = ['GET', 'POST'])
def no_urn_2(page_name):
  return "Please input Forge URN"

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
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


@app.route('/uploaded', methods=['GET', 'POST'])
def uploaded_file():
	return '''
	<!doctype html>
	<title>Uploaded the file</title>
	<h1> File has been Successfully Uploaded </h1>
	'''


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
  client_id = 'dwpRPnV14An6mHOi7GEmRmfmSiVC8xbs'      # TODO
  client_secret = 'Fd9fbf388c21a4e3'  # TODO

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