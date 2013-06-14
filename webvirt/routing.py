#!/usr/bin/env python2

urls = []
mapping = {}


class ControllerMeta(type):
    def __new__(cls, name, bases, attrs):
        assert 'url' in attrs, "Controller %s does not have a URL" %(name)
        urls.append(attrs['url'])
        urls.append(name)
        new = type.__new__(cls, name, bases, attrs)
        mapping[name] = new
        return new
