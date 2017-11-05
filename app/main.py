#!/usr/bin/env python
import hashlib
import os
import sqlite3

from flask import (Flask, g, redirect, render_template, request,
                   send_from_directory, url_for)
from ihih import IHIH
from sendmail import sendConfirmation

app = Flask(__name__)
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

NAMES = None
DATABASE = './database/database.db'

def get_config():
    return IHIH(
        (
            os.path.join(os.path.dirname(__file__), '../config/custom.conf')
        )
    )


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

    total = query_db('SELECT count(*) as total FROM votes', [], one=True)
    if not total:
        return

    for name in names:
        count = query_db('SELECT count(*) as avg FROM votes WHERE validate_datetime IS NOT NULL AND name = ?', [name[0]], one=True)
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
def index():
    with app.app_context():
        NAMES = query_db('SELECT * FROM names ORDER BY random()')
    return render_template('index.html', names=NAMES)


@app.route("/vote/<name>", methods=['GET', 'POST'])
def vote(name):
    # Check name validity
    with app.app_context():
        result = query_db('SELECT * FROM names WHERE name = ?', [name], one=True)
    if not result:
        # return render_template('invalid-name.html', name=name)
        return redirect('/propose-name/%s' % name)

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
def validate(token):
    with app.app_context():
        vote = query_db('SELECT * FROM votes WHERE token = ? AND validate_datetime IS NOT NULL', [token], one=True)
    if vote:
        if vote['new_name'] is None:
            return render_template('already-voted.html', name=vote['name'], email=vote['email'], vote_datetime=vote['vote_datetime'], validate_datetime=vote['validate_datetime'])
        else:
            result = update_db('votes', ["name=new_name, validate_datetime=datetime('now'), new_name=NULL"])
        if not result:
            return render_template('saving-vote-error.html')
    else:
        return render_template('no-such-token.html')
    update_averages()
    return render_template('validate.html')


@app.route("/check-your-mails")
def check_your_mails():
    return render_template('check-your-mails.html')


@app.route("/propose-name/<name>", methods=['GET', 'POST'])
@app.route("/propose-name", defaults={'name': ''}, methods=['GET', 'POST'])
def propose_name(name):
    email = ''
    username = ''
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        result = insert_db('proposed_names', ('username', 'name', 'email'), (username, name, email))
        if not result:
            return render_template('saving-propose-error.html')
        return render_template('saving-for-review.html')

    return render_template('propose-name.html', username=username, name=name, email=email)


@app.route("/send-mail-again/<email>")
def mail_again(email):
    with app.app_context():
        vote = query_db('SELECT * FROM votes WHERE email = ?', [email], one=True)
    if vote and vote['validate_datetime']:
        return render_template('already-voted.html', name=vote['name'], email=vote['email'], vote_datetime=vote['vote_datetime'], validate_datetime=vote['validate_datetime'])
    if vote:
        s = sendConfirmation().send(email, vote['token'], vote['name'])
        return render_template('check-your-mails.html')

    return redirect('/')


@app.route("/moderate/<password>")
def modaration_list(password):
    config = get_config()
    if password !=  config.get('ADMIN_PASSWORD'):
        return redirect('/')

    with app.app_context():
        propositions = query_db('SELECT * FROM proposed_names', [])
    return render_template('moderate-list.html', propositions=propositions)



    # if vote and vote['validate_datetime']:
    #     return render_template('already-voted.html', name=vote['name'], email=vote['email'], vote_datetime=vote['vote_datetime'], validate_datetime=vote['validate_datetime'])
    # if vote:
    #     s = sendConfirmation().send(email, vote['token'], vote['name'])
    #     return render_template('check-your-mails.html')

    return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
