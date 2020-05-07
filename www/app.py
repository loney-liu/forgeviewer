import os
from flask import Flask, request
from shotgun_api3 import shotgun

app = Flask(__name__)

@app.route("/", methods = ['GET', 'POST'])
def ami_endpoint():
  return process_versions()

def process_versions():
    return request.form

if __name__ == "__main__":
    app.run(host="0.0.0.0")