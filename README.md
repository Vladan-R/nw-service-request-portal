# Example web app for staging NW equipment and documentation of standardized site

## Usage
### Step 1: Fill out form at Customer1 > Service Request Data Form
You will get YAML data file.
### Step 2: Upload the YAML data file at Customer1 > Engineering upload
You will be presented with a list of files including device configs, implementation plan and hw ordering list.
### Step 3: Render NW diagram based on the provided data.
You can render the diagram by using button below the above mentioned list of files
or by going to APP_URL/customer1/diagram-render/service_request_number


## Deployment information

This was deployed in production within two Docker containers:
* container1: NGINX
* container2: uWSGI + app

NGINX, uWSGI config files as well as docker-compose.yml are included in this repository.


Python version used: 3.8.1