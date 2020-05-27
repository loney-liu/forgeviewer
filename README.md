# Demo for Forge Viewer + Shotgun

## How to use:

### Supported formates
- obj
- revit

### Upload a model to Forge to get Forge URN
https://{ your site }/upload

### Create Fields

#### Asset
- Create text field "Forge URN"
- Create text field "Forge Tree JSON"
- Create text field "Forge Property JSON"

#### Task
- Create text field "Forge Object Tree"
- Create URL Page

##### Asset
- https://desolate-beach-90284.herokuapp.com/forge_viewer/{sg_forge_urn}

##### Anotation
- https://desolate-beach-90284.herokuapp.com/forge_viewer_snap/{sg_forge_urn}/{id}

#### Create AMI for Asset and Task

##### Asset
- https://desolate-beach-90284.herokuapp.com/sg_asset
- https://desolate-beach-90284.herokuapp.com/forge_viewer_snap
- https://desolate-beach-90284.herokuapp.com/review_notes

##### Task
- https://desolate-beach-90284.herokuapp.com/view_parts

# Flask Docker Forge Viewer （Python 3）

- Install docker, docker-compose

- git clone https://github.com/loney-liu/forge_viewer
