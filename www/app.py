import os
from flask import Flask, request, render_template
from shotgun_api3 import shotgun
import requests

app = Flask(__name__)
FORGE_AUTH_URL = "https://developer.api.autodesk.com/authentication/v1/authenticate"

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