#!/usr/bin/env python
# -*- coding: utf-8 -*-
import hashlib
import os
import sqlite3

from flask import (Flask, abort, g, redirect, render_template, request,
                   send_from_directory, url_for)
from flask_babel import Babel
from ihih import IHIH
from middleware import PrefixMiddleware
from sendmail import (sendConfirmation, sendProposition,
                      sendValidatedProposition)

app = Flask(__name__)
app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix='/molename')
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
app.config['SUPPORTED_LANGUAGES'] = {
    'en': u'English',
    'pl': u'Polskie',
    'fr': u'Francais',
    'no': u'Norsk',
    'it': u'Italiano',
    'de': u'Deutsch',
    'es': u'Español',
    'id': u'Indonesian',
    'sq': u'shqiptar',
    'sc': u'Čeština',
}

babel = Babel(app)

NAMES = None
DATABASE = './database/database.db'


def get_config():
    return IHIH(
        (
            os.path.join(os.path.dirname(__file__), '../config/custom.conf')
        )
    )


@babel.localeselector
def get_locale():
    locale = g.get('lang_code')
    if locale not in app.config['SUPPORTED_LANGUAGES'].keys():
        locale = request.accept_languages.best_match(app.config['SUPPORTED_LANGUAGES'].keys())
    return locale


@babel.timezoneselector
def get_timezone():
    user = g.get('user', None)
    if user is not None:
        return user.timezone


@app.url_defaults
def set_language_code(endpoint, values):
    if 'lang_code' in values or not g.get('lang_code', None):
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'lang_code'):
        values['lang_code'] = g.lang_code


@app.url_value_preprocessor
def get_lang_code(endpoint, values):
    if values is not None:
        g.lang_code = values.pop('lang_code', None)


@app.before_request
def ensure_lang_support():
    lang_code = g.get('lang_code', None)
    if lang_code and lang_code not in app.config['SUPPORTED_LANGUAGES'].keys():
        return abort(404)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.context_processor
def inject_user():
    config = get_config()
    return dict(vote_step=config.get('VOTE_STEP', 1))


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def insert_db(table, fields=(), values=()):
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        query = 'INSERT INTO %s (%s) VALUES (%s)' % (
            table,
            ', '.join(fields),
            ', '.join(['?'] * len(values))
        )
        cur.execute(query, values)
        db.commit()
        id = cur.lastrowid
        cur.close()
        return id


def update_db(table, fields=(), values=(), condition='1 = 1'):
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        query = 'UPDATE %s SET %s WHERE %s' % (
            table,
            ', '.join(fields),
            condition
        )
        count = cur.execute(query, values)
        db.commit()
        cur.close()
        return count


def delete_db(table, condition):
    with app.app_context():
        db = get_db()
        query = 'DELETE FROM proposed_names WHERE id = ?'
        count = db.execute(query, condition)
        db.commit()
        return count


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def update_averages():
    names = query_db('SELECT name FROM names', [])
    if not names:
        return

    total = query_db('SELECT count(*) as total FROM votes WHERE validate_datetime IS NOT NULL', [], one=True)
    if not total:
        return

    for name in names:
        count = query_db(
            'SELECT count(*) as avg FROM votes WHERE validate_datetime IS NOT NULL AND name = ?', [name[0]], one=True)
        avg = 1.0 * count[0] / total['total'] * 100
        result = update_db('names', ["rate = ?"], [avg, name[0]], 'name = ?')
        if not result:
            return


@app.route('/skeleton/<path:path>')
def send_skeleton(path):
    return send_from_directory('Skeleton-2.0.4', path)


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


@app.route("/")
@app.route("/<lang_code>/")
def index():
    with app.app_context():
        sql = 'SELECT * FROM names ORDER BY name'
        if get_config().get('VOTE_STEP') == '3':
            sql = 'SELECT * FROM names ORDER BY random()'
        NAMES = query_db(sql)
    return render_template('index.html', names=NAMES)


@app.route("/vote/<name>", methods=['GET', 'POST'])
@app.route("/<lang_code>/vote/<name>", methods=['GET', 'POST'])
def vote(name):
    if get_config().get('VOTE_STEP') != '3':
        return redirect(url_for('index'))

    # Check name validity
    with app.app_context():
        result = query_db('SELECT * FROM names WHERE name = ?', [name], one=True)
    if not result:
        # return render_template('invalid-name.html', name=name)
        return redirect(url_for('propose_name', name=name))

    # Save user vote
    if request.method == 'POST':
        email = request.form['email']
        change_vote = 'change_vote' in request.form
        # Already voted?
        with app.app_context():
            vote = query_db('SELECT * FROM votes WHERE email = ?', [email], one=True)
        if vote and not change_vote:
            return render_template('already-voted.html', new_name=name, name=vote['name'], email=vote['email'], vote_datetime=vote['vote_datetime'], validate_datetime=vote['validate_datetime'])

        # has never voted
        token = hashlib.sha224(os.urandom(64)).hexdigest()
        if not change_vote:
            result = insert_db('votes', ('name', 'email', 'token'), (name, email, token))
        else:
            result = update_db('votes', ["new_name = ?, token = ?"], [name, token, email], 'email = ?')
            # result = insert_db('votes', ('name', 'email', 'token'), (name, email, token))
        if not result:
            return render_template('saving-vote-error.html')

        # Send confirmation mail
        sendConfirmation().send(email, token, name)
        return render_template('check-your-mails.html')

    return render_template('vote.html', name=name)


@app.route("/validate/<token>")
@app.route("/<lang_code>/validate/<token>")
def validate(token):
    if get_config().get('VOTE_STEP') != '3':
        return redirect(url_for('index'))

    with app.app_context():
        vote = query_db('SELECT * FROM votes WHERE token = ?', [token], one=True)
    if vote:
        if vote['new_name'] is None and vote['validate_datetime'] is not None:
            return render_template('already-voted.html', name=vote['name'], email=vote['email'], vote_datetime=vote['vote_datetime'], validate_datetime=vote['validate_datetime'])
        elif vote['new_name'] is None:
            result = update_db('votes', ["validate_datetime=datetime('now'), new_name=NULL"], [token], 'token = ?')
            if not result:
                return render_template('saving-vote-error.html')
        else:
            result = update_db('votes', ["name=?, vote_datetime=datetime('now'), validate_datetime=datetime('now'), new_name=NULL"], [
                               vote['new_name'], token], 'token = ?')
            if not result:
                return render_template('saving-vote-error.html')
    else:
        return render_template('no-such-token.html')
    update_averages()
    return render_template('validate.html')


@app.route("/check-your-mails")
@app.route("/<lang_code>/check-your-mails")
def check_your_mails():
    return render_template('check-your-mails.html')


@app.route("/suggest-name/<name>", methods=['GET', 'POST'])
@app.route("/<lang_code>/suggest-name/<name>", methods=['GET', 'POST'])
@app.route("/suggest-name", defaults={'name': ''}, methods=['GET', 'POST'])
@app.route("/<lang_code>/suggest-name", defaults={'name': ''}, methods=['GET', 'POST'])
def propose_name(name):
    if get_config().get('VOTE_STEP') != '1':
        return redirect(url_for('index'))

    email = ''
    username = ''
    if request.method == 'POST':
        name = request.form['name'].lower()
        username = request.form['username']
        email = request.form['email']

        if not (name and username and email):
            return render_template('propose-name.html', username=username, name=name, email=email, msg="FILL_ALL_FIELDS")
        if not ('g' in name and 'k' in name):
            return render_template('propose-name.html', username=username, name=name, email=email, msg="MUST_CONTAIN_G_K")

        name = name.replace('g', 'G', 1).replace('k', 'K', 1)

        with app.app_context():
            result = query_db('SELECT * FROM names WHERE name = ?', [name])
            if result:
                return render_template('already-proposed-error.html')
            result = query_db('SELECT * FROM proposed_names WHERE name = ?', [name])
            if result:
                return render_template('already-proposed-error.html')

        result = insert_db('proposed_names', ('username', 'name', 'email'), (username, name, email))
        if not result:
            return render_template('saving-propose-error.html')
        sendProposition().send(username, name)
        return render_template('saving-for-review.html')

    return render_template('propose-name.html', username=username, name=name, email=email)


@app.route("/send-mail-again/<email>")
@app.route("/<lang_code>/send-mail-again/<email>")
def mail_again(email):
    if get_config().get('VOTE_STEP') != '3':
        return redirect(url_for('index'))

    with app.app_context():
        vote = query_db('SELECT * FROM votes WHERE email = ?', [email], one=True)
    if vote and vote['validate_datetime']:
        return render_template('already-voted.html', name=vote['name'], email=vote['email'], vote_datetime=vote['vote_datetime'], validate_datetime=vote['validate_datetime'])
    if vote:
        s = sendConfirmation().send(email, vote['token'], vote['name'])
        return render_template('check-your-mails.html')

    return redirect(url_for('index'))


@app.route("/moderate/<password>")
@app.route("/<lang_code>/moderate/<password>")
def moderation_list(password):
    config = get_config()
    if password != config.get('ADMIN_PASSWORD'):
        return redirect(url_for('index'))

    with app.app_context():
        propositions = query_db('SELECT * FROM proposed_names', [])
    return render_template('moderate-list.html', password=password, propositions=propositions)


@app.route("/moderate/<password>/<id>/validate")
@app.route("/<lang_code>/moderate/<password>/<id>/validate")
def modaration_validate(password, id):
    config = get_config()
    if password != config.get('ADMIN_PASSWORD'):
        return redirect(url_for('index'))

    with app.app_context():
        proposition = query_db('SELECT * FROM proposed_names WHERE id = ?', [id], one=True)
        if proposition:
            result = insert_db('names', ('name', 'username'), (proposition['name'], proposition['username']))
            if not result:
                return render_template('saving-propose-error.html')
            delete_db('proposed_names', [id])
            s = sendValidatedProposition().send(proposition['username'], proposition['email'], proposition['name'])

    return redirect(url_for('moderation_list', password=password))


@app.route("/moderate/<password>/<id>/refuse")
@app.route("/<lang_code>/moderate/<password>/<id>/refuse")
def modaration_refuse(password, id):
    config = get_config()
    if password != config.get('ADMIN_PASSWORD'):
        return redirect(url_for('index'))

    delete_db('proposed_names', [id])

    return redirect(url_for('moderation_list', password=password))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
