# Demo for Forge Viewer + Shotgun

## How to use:

### Supported formates
- obj
- revit

### Upload a model to Forge to get Forge URN
https://your_website_url/upload

### Create Fields

#### Asset
- Create text field "Forge URN"
- Create text field "Forge Tree JSON"
- Create text field "Forge Property JSON"

#### Task
- Create text field "Forge Object Tree"
- Create URL Page

##### Asset
- https://your_website_url/forge_viewer/{sg_forge_urn}

##### Anotation
- https://your_website_url/forge_viewer_snap/{sg_forge_urn}/{id}

#### Create AMI for Asset and Task

##### Asset
- https://your_website_url/sg_asset
- https://your_website_url/forge_viewer_snap
- https://your_website_url/review_notes

##### Task
- https://your_website_url/view_parts

# Flask Docker Forge Viewer （Python 3）

- Install docker, docker-compose

- git clone https://github.com/loney-liu/forge_viewer

# References

- [Learn Autodesk Forge](https://learnforge.autodesk.io/#/)
- [Shotgun Python API](https://developer.shotgunsoftware.com/python-api/)
- [Shotgun REST API](https://developer.shotgunsoftware.com/rest-api/)