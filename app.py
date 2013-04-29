#!/usr/bin/python2 -OO
import web
import webvirt

urls = (
        '/', 'Index',
        '/auth', 'Auth',
        '/list', 'List',
        '/login', 'Login',
        '/logout', 'Logout',
        '/console', 'Console',
        '/vm', 'VM',
        '/create', 'Create',
        '/upload', 'Upload',
        '/hd','HD',
        '/listhd', 'ListHD',
        '/listisos', 'ListISOs'
        )

if __name__ == '__main__':
    app = web.application(urls, webvirt.urls.classes)
    app.run()
