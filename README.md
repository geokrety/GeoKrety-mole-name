# The mole without name

This side project from GeoKrety aimed to help us choose name for our mascot.

# Install

We distribute a `Dockerfile` and `docker-compose.yml` to help you start.

1. You need to have [`docker`](https://docs.docker.com/engine/installation/) installed.
1. You need to have [`docker-compose`](https://docs.docker.com/compose/install/) installed.
1. Clone the project `git clone https://github.com/geokrety/GeoKrety-mole-name.git`.
1. Copy `config/custom.example.conf` to `config/custom.conf`, and adjust to your needs.
1. Build the docker image `docker-compose build`.
1. Launch the container `docker-compose up -d`.

# Contribute

* Open a pull request, rebased on current master
* If you add dependencies to other project, please add them to `ATTRIBUTIONS.md`

# Manage translations

* Extract translatable strings: `docker exec -it geokretymascottname_geokrety-mole-name_1 pybabel extract -F babel.cfg -o app/translations/messages.pot app`
* Connect to crowdin and upload file
* Import Translate files into code source tree
* Compile new translations `docker exec -it geokretymascottname_geokrety-mole-name_1 pybabel compile -d app/translations/`

To initialize a new language, declare it in `app/main.py`, and launch `docker exec -it geokretymascottname_geokrety-mole-name_1 pybabel init -i app/translations/messages.pot -d app/translations -l <lang_code>`

Note: Norwegian have a problem, locale is recognized as `nb`. See https://github.com/python-babel/flask-babel/issues/61
