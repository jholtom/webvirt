#!/usr/bin/python2 -OO
import web
import webvirt

urlprefix = webvirt.config.urlprefix

urls = (
        '{0}/'.format(urlprefix), 'Index',
        '{0}/auth'.format(urlprefix), 'Auth',
        '{0}/list'.format(urlprefix), 'List',
        '{0}/login'.format(urlprefix), 'Login',
        '{0}/logout'.format(urlprefix), 'Logout',
        '{0}/console'.format(urlprefix), 'Console',
        '{0}/vm'.format(urlprefix), 'VM',
        '{0}/create'.format(urlprefix), 'Create',
        '{0}/upload'.format(urlprefix), 'Upload',
        '{0}/hd'.format(urlprefix),'HD',
        '{0}/listhd'.format(urlprefix), 'ListHD',
        '{0}/listisos'.format(urlprefix), 'ListISOs'
        )

if __name__ == '__main__':
    app = web.application(urls, webvirt.urls.classes)
    app.run()
