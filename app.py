#!/usr/bin/python2 -OO
import web

import webvirt

if __name__ == '__main__':
    app = web.application(webvirt.routing.urls, webvirt.routing.mapping)
    app.add_processor(webvirt.auth.authentication_processor)
    app.add_processor(webvirt.virt.virt_processor)
    app.run()
