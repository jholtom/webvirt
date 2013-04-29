import hashlib
import web
import sqlite3

def checkpw(username, password):
    authdb = sqlite3.connect('webvirt/users.db')
    cur = authdb.cursor()
    pwdhash = hashlib.sha512(password).hexdigest()
    cur.execute('select * from users where username=? and password=?', (username, pwdhash))
    if cur.fetchone(): 
        return True
    else:
        return False

def authuser(username, password):
    if checkpw(username, password):
        web.setcookie("session", username)
        return True
    return False

def destroy_session():
    web.setcookie('session', '', expires=-1)

def verify_auth(redir=None):
    cookies = web.cookies()
    if cookies.get("session") == None:
        if redir == None:
            return False
        web.seeother(redir)
    else:
        return True
