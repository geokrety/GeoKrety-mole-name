from flask import Flask, render_template, send_from_directory
app = Flask(__name__)
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

NAMES = {
    'GraKi': 24,
    'GoKou': 24,
    'GeyKee': 24,
    'GeoKey': 24,
    'GieneK': 24,
    'GeeKay': 24,
}

@app.route('/skeleton/<path:path>')
def send_skeleton(path):
    return send_from_directory('Skeleton-2.0.4', path)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route("/")
def index():
    return render_template('index.html', names=NAMES)

@app.route("/vote/<name>")
def vote(name):
    if name not in NAMES:
        return render_template('invalid-name.html', name=name)

    return render_template('vote.html', name=name)

@app.route("/validate/<token>")
def validate(token):
    return render_template('validate.html')
