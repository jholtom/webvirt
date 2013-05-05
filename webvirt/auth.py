import bcrypt
import config
import hashlib
import random
import sqlite3
import time
import web
import os

class Authenticator:
    def __init__(self):
        try:
            self.path = config.db_path
        except:
            self.path = "webvirt/webvirt.db"
        if os.path.isfile(self.path) == False:
            raise Exception("db does not exist. have you run setupdb.sh?")
        self.db = sqlite3.connect(self.path)
        self.cursor = self.db.cursor()

    def __del__(self):
        self.db.commit()
        self.db.close()

    def authenticate_user(self, username, password):
        if not self.check_password(username, password):
            return False
        sid = self.gen_sid()
        ip_addr = web.ctx.ip
        self.cursor.execute("INSERT INTO sessions VALUES (?, ?, ?)", (sid, username, ip_addr))
        self.db.commit()
        web.setcookie("session", sid)
        return True

    def verify_user(self):
        cookies =  web.cookies()
        sid = cookies.get("session")
        if sid == None:
            return False
        ip_addr = web.ctx.ip
        self.cursor.execute("SELECT * FROM sessions WHERE sid=? AND ip=?", (sid, ip_addr))
        row = self.cursor.fetchone()
        if not row:
            return False
        return row[1]

    def verify_redirect(self, url):
        if not self.verify_user():
            web.seeother(url)
        return True

    def destroy_session(self):
        cookies =  web.cookies()
        sid = cookies.get("session")
        if sid == None:
            return False
        self.cursor.execute("DELETE FROM sessions WHERE sid=?", (sid,))
        self.db.commit()
        web.setcookie('session', '', expires=-1)
        return True

    def gen_sid(self):
        t = str(time.time())
        r = str(random.getrandbits(512))
        l = list(r + t)
        random.shuffle(l)
        return hashlib.sha256(''.join(l)).hexdigest()

    def has_user(self, username):
        self.cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        if self.cursor.fetchone():
            return True
        return False

    def get_user(self, username):
        self.cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        return self.cursor.fetchone()

    def hash_password(self, password):
        return bcrypt.hashpw(password, bcrypt.gensalt())

    def check_password(self, username, password):
        user = self.get_user(username)
        if not user:
            return False
        user_pass = user[1]
        return bcrypt.hashpw(password, user_pass) == user_pass

def authentication_processor(handle):
    authenticator = Authenticator()
    user = authenticator.verify_user()
    if user:
        web.ctx.username = user
        web.ctx.auth = True
    else:
        web.ctx.username = False
        web.ctx.auth = False
    return handle()
