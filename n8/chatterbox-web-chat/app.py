from flask import Flask, request, session, redirect, url_for, render_template, flash, jsonify
import os
from models import db, User, chatRoom, messageLog
from sqlalchemy import or_, and_

app = Flask(__name__)

app.config.update(dict(
    DEBUG=True,
    # hardcoded owner login
    # USERNAME='owner',
    # PASSWORD='pass',
    SECRET_KEY='development key',
    SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.root_path, 'chat.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False 
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

db.init_app(app)


@app.cli.command('initdb')
def initdb_command():
    db.create_all()
    print('Initialized the database.')


# Chat messages get appended here
items = []


@app.route("/new_item", methods=["POST"])
def add():
    userPosted = session['username']
    message = request.form["one"]
    newLine = userPosted + ": " + message

    db.session.add(messageLog(session['username'], session['chatroom'], message))
    db.session.commit()

    items.append([newLine])
    return jsonify(items)


@app.route("/items")
def get_items():
    return jsonify(items)


# By default, redirect to login
@app.route("/")
def default():
    return redirect(url_for("login"))


@app.route("/login/", methods=["GET", "POST"])
def login():
    error = None
    # Reset after each login

    if request.method == "POST":
        username = request.form["user"]
        password = request.form["pass"]

        if not username:
            error = 'Please enter a username.'
        elif not password:
            error = 'Please enter a password.'

        if error is None:
            # If staff account
            checkUser = User.query.filter_by(username=username).first()
            # NOT a staff account
            if checkUser is None:
                error = 'Please enter a valid username.'

            if error is None:
                if not checkUser.password == password:
                    error = 'Incorrect password.'

            if error is None:
                session['username'] = username  # Set session username
                flash("Login Success!")
                return redirect(url_for("homePage"))

            flash(error)
            return redirect(url_for("login"))

        flash(error)

    return render_template('login.html')


@app.route('/delete_room/<room_name>')
def deleteEvent(room_name):
    chatRoom.query.filter_by(roomName=room_name).delete()
    messageLog.query.filter_by(roomName=room_name).delete()
    db.session.commit()
    items.clear()
    flash('Room and associated messages successfully deleted.')
    return redirect(url_for("homePage"))


@app.route('/chat/<room_name>', methods=["GET", "POST"])
def room(room_name):
    # Remake table for a new chatroom
    items.clear()

    session['chatroom'] = room_name

    chatLog = messageLog.query.filter_by(roomName=room_name).order_by(messageLog.id.asc()).all()

    for item in chatLog:
        user = item.userSent
        message = item.message
        completeString = user + ": " + message
        items.append([completeString])
    return render_template('rooms.html', username=session['username'], roomName=room_name, messages=chatLog)


@app.route("/home/", methods=["GET", "POST"])
def homePage():
    error = None
    if request.method == "POST":  # Create a new chatroom
        name = request.form["roomName"]

        if not name:
            error = 'Please enter a valid room name.'

        checkConflict = chatRoom.query.filter_by(roomName=name).first()

        if checkConflict:
            error = 'Naming conflict: chatroom with this name already exists. Please rename and try again.'

        if error is None:
            db.session.add(chatRoom(name, session['username']))
            db.session.commit()
            flash("New room created.")
            return redirect(url_for("homePage"))

        flash(error)

    # Query all chatrooms
    chatRooms = chatRoom.query.order_by(chatRoom.id.asc()).all()
    return render_template('homechat.html', username=session['username'], rooms=chatRooms)


@app.route("/new/", methods=["GET", "POST"])
def registerUser():
    if request.method == "POST":
        error = None
        username = request.form["newcustomer"]
        password = request.form["newpass"]

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        # If we return a customer by matching username, already exists in the database
        user = User.query.filter_by(username=username).first()

        if user:
            error = 'This username already exists.'

        if error is None:
            # No customer exists yet, create a new one
            flash("New user account created.")
            db.session.add(User(username, password))
            db.session.commit()
            return redirect(url_for("login"))

        flash(error)
        return redirect(url_for("registerUser"))  # Customer already exists

    return render_template('register.html')


# Logout page
@app.route("/logout/")
def logout():
    # If logged in, log out, otherwise offer to log in
    session.clear()
    flash('User logged out.')
    return redirect(url_for("login"))


if __name__ == "__main__":
    # Create the database tables
    with app.app_context():
        db.create_all()

    # Run the Flask application
    app.run()