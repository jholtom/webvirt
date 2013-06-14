"""
    WebVirt URL Handlers
"""
from . import auth
from . import common
from .common import setupProxy
import routing
from . import config
import libvirt
from . import virt
import web
import os
from .pymagic import magic
import subprocess
import sys
from .hurry.filesize import size as hsize
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('webvirt/templates'))

def sidebarGen(conn):
	suspended = []
        dead = []
        running = []
        for dom in conn.listAllDomains(0):
            dom = virt.Domain(dom)
            if(dom.rawstate == libvirt.VIR_DOMAIN_RUNNING):
                running.append({'name':dom.name, 'state':dom.state})
            elif(dom.rawstate == libvirt.VIR_DOMAIN_SHUTOFF):
                dead.append({'name':dom.name, 'state':dom.state})
            else:
                suspended.append({'name':dom.name, 'state':dom.state})

        sidebar = env.get_template('sidebar.html')
        return sidebar.render(running=running,suspended=suspended,dead=dead, urlprefix=config.urlprefix)

class Index:
    __metaclass__ = routing.ControllerMeta
    url = '/?'

    def GET(self):
        if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
        templates = web.template.render('webvirt/templates/')
        conn = web.ctx.libvirt
        content = ""
        numVMs = float(len(conn.listAllDomains(0)))
        # avoid div by 0
        if numVMs > 0:
            perRunningVMs = 100 * (float(len(conn.listAllDomains(16)))) / numVMs
            perSuspendVMs = 100 * (float(len(conn.listAllDomains(32)))) / numVMs
            perShutoffVMs = 100 * (float(len(conn.listAllDomains(64)))) / numVMs #Should be numVMs
            content += '<h2>VM State Statistics</h2><br />\n'
            content += '<div class="progress">\n'
            content += '  <div class="bar bar-success" style="width: ' + str(perRunningVMs) + '%;">Running</div>\n'
            content += '  <div class="bar bar-warning" style="width: ' + str(perSuspendVMs) + '%;">Suspended</div>\n'
            content += '  <div class="bar bar-danger" style="width: ' + str(perShutoffVMs) + '%;">Shut Down</div>\n'
            content += '</div>\n'
        data = ""
        hs = virt.HostServer()
        freemem, usedmem = common.pct_from_mem(hs.memstats)
        usedmem = str(usedmem) + '%'
        if usedmem <= '40%':
            bar = 'bar-success'
        elif '75%' >= usedmem > '40%':
            bar = 'bar-warning'
        else:
            bar = 'bar-danger'
        content += str(templates.host(hs.hostname, hs.hosttype, usedmem, bar))
        data += sidebarGen(conn)
	return templates.index(content, data, web.ctx.username, config.urlprefix)

class VM:
    __metaclass__ = routing.ControllerMeta
    url = '/vm/?'

    def GET(self):
        if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
        templates = web.template.render('webvirt/templates/')
        conn = web.ctx.libvirt
        data2 = web.input()
        content = ""
        vm = data2['vm']
        domObj = virt.Domain(conn.lookupByName(vm))
        if 'action' in list(data2.keys()):
            if data2['action'] == 'start':
                domObj.startVM()
            elif data2['action'] == 'stop':
                domObj.stopVM()
            elif data2['action'] == 'destroy':
                domObj.destroyVM()
            elif data2['action'] == 'suspend':
                domObj.suspendVM()
            elif data2['action'] == 'resume':
                domObj.resumeVM()
            if data2['action'] in ['start', 'stop', 'destroy', 'suspend', 'resume']:
                content += '<div class="alert">\n'
                content += '  <button type="button" class="close" data-dismiss="alert">&times;</button>'
            content += '  ' + vm + ' ' +  data2['action'] + ('p' if data2['action'] == 'stop' else '') + ('e' if data2['action'] != 'resume' else '') + 'd.'
            content += '</div>'
        content += """<div class="btn-group">
        <a class="btn dropdown-toggle" data-toggle="dropdown" href="#">Power Options<span class="caret"></span></a>
        <ul class="dropdown-menu"><li    ><a href="{0}/vm?vm={1}&action=start">Start</a></li>
        <li><a href="{0}/vm?vm={1}&action=stop">Stop</a></li>
        <li><a href="{0}/vm?vm={1}&action=destroy">Destroy</a></li>
        <li><a href="{0}/vm?vm={1}&action=suspend">Suspend</a></li>
        <li><a href="{0}/vm?vm={1}&action=resume">Resume</a></li></ul></div>""".format(config.urlprefix,vm)
        vmdict = domObj.get_dict()
        #mempct = str(vmdict['mempct']) + '%'
        #content += str(templates.vmmemory(mempct))
        content += "<br /><br />"
        vncport = domObj.getVNC()
        if vncport == -1:
            button = "disabled"
            content += '<div class="alert">VNC is not configured for this VM.</div>'
        else:
            button = ""
            common.setupProxy(vncport)
        site = web.ctx.host.split(':')[0]
        content += "<a href='{0}/static/novnc/vnc.html?host={1}&port={2}'><button {3} class=\"btn btn-info\">Launch Display Connection</button></a>".format(config.urlprefix,site,vncport+1000,button)
        data = ""
        data += sidebarGen(conn)
	return templates.vm(content, data, vm, web.ctx.username, config.urlprefix)

class Create:
    __metaclass__ = routing.ControllerMeta
    url = '/create/?'

    def GET(self):
        if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
        templates = web.template.render('webvirt/templates/')
        conn = web.ctx.libvirt
        myform = web.form.Form( 
                web.form.Textbox("name",web.form.notnull,description="Name of Virtual Machine: ",align='left'),
                web.form.Textbox("mem",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="Amount of Memory (in KiB): ",align='left'),
                web.form.Textbox("cpu",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="Number of Virtual Processors: ",align='left'),
                web.form.Textbox("hd",web.form.notnull,description='Full Path to hard drive file: ',align='left'),
                web.form.Textbox("iso",web.form.notnull,description="Full Path to cdrom iso file (e.x " + config.datadir + "gentoo.iso): ",align='left'),
                web.form.Textbox("vnc",web.form.notnull,description="VNC Port Number (5901+): ",align='left'),
                web.form.Textbox("pts",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="PTS number for serial console: ",align='left')
                )
        form = myform()
        data = ""
        content = "<h2>Create a New VM</h2>"
        data += sidebarGen(conn)
	return templates.create(content, data, form, web.ctx.username, config.urlprefix)

    def POST(self): 
        myform = web.form.Form( 
                web.form.Textbox("name",web.form.notnull,description="Name of Virtual Machine: ",align='left'),
                web.form.Textbox("mem",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="Amount of Memory (in KiB): ",align='left'),
                web.form.Textbox("cpu",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="Number of Virtual Processors: :",align='left'),
                web.form.Textbox("hd",web.form.notnull,description="Full Path to hard drive file (e.x " + config.datadir + "$name.qcow2): ",align='left'),
                web.form.Textbox("iso",web.form.notnull,description="Full Path to cdrom iso file (e.x " + config.datadir + "gentoo.iso): ",align='left'),
                web.form.Textbox("vnc",web.form.notnull,description="VNC Port Number: ",align='left'),
                web.form.Textbox("pts",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="PTS number for serial console: ",align='left')
                )
        form = myform() 
        if not form.validates(): 
            return web.template.render.formtest(form)
        else:
            hs = virt.HostServer()
            hs.createDomain(form['name'].value, form['mem'].value, form['cpu'].value, form['hd'].value, form['iso'].value, form['vnc'].value ,form['pts'].value)
            web.seeother('/'+config.urlprefix)

class Auth:
    __metaclass__ = routing.ControllerMeta
    url = '/auth/?'

    def GET(self):
        web.header('Content-type', 'text/html')
        return "<h1>Incorrect method</h1>"

    def POST(self): 
        authenticator = auth.Authenticator()
        data = web.input()
        username = data['username']
        password = data['password']
        if authenticator.authenticate_user(username, password):
            if 'redirect' in data:
                web.seeother(data['redirect'])
            else:
                web.seeother('/'+config.urlprefix)
        else:
            web.seeother("{0}/login?failed=1".format(config.urlprefix))

class Logout:
    __metaclass__ = routing.ControllerMeta
    url = '/logout/?'

    def GET(self):
        authenticator = web.ctx.authenticator
        authenticator.destroy_session()
        web.seeother('/'+config.urlprefix)

class Login:
    __metaclass__ = routing.ControllerMeta
    url = '/login/?'

    def GET(self):
        if web.ctx.auth:
            web.seeother("{0}/".format(config.site_prefix))
        templates = web.template.render('webvirt/templates/')
        data = web.input()
        if "failed" in data:
            return templates.login('<span><p style="color:#FF0000">Failed Login</p></span>', config.urlprefix)
        else:
            return templates.login('', config.urlprefix)

class List:
    __metaclass__ = routing.ControllerMeta
    url = '/list/?'

    def GET(self):
        if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
        data = []
        conn = web.ctx.libvirt
        for dom in conn.listAllDomains(0):
            data[dom] = Domain(dom)
        return web.template.render('webvirt/templates/').index(data)

class Console: 
    __metaclass__ = routing.ControllerMeta
    url = '/console/?'

    def GET(self):
        if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
        templates = web.template.render('webvirt/templates/')
        return templates.console()

class Upload:
    __metaclass__ = routing.ControllerMeta
    url = '/upload/?'

    def GET(self):
        if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
        params = web.input()
        conn = web.ctx.libvirt
        if 'bad' in list(params.keys()) and int(params['bad']) == 1:
            return web.template.render("webvirt/templates/").index("<div class=\"alert\"><strong>Error! Your uploaded file was not an ISO file.</strong></div>", "", web.ctx.username)
        content = """
        <h2>Upload CDROM/DVDROM ISO file</h2>
        <form method="POST" enctype="multipart/form-data" action="">
        <input type="file" name="myfile" />
        <br/>
        <input type="submit" />
        </form>"""
        data = ""
        data += sidebarGen(conn)
	templates = web.template.render("webvirt/templates/")
        return templates.index(content, data, web.ctx.username, config.urlprefix)

    def POST(self):
        x = web.input(myfile={})
        if 'myfile' in x: # to check if the file-object is created
            filepath=x.myfile.filename.replace('\\','/') # replaces the windows-style slashes with linux ones.
            filename=filepath.split('/')[-1] # splits the and chooses the last part (the filename with extension)
            fout = open(config.datadir +'/'+ filename,'w') # creates the file where the uploaded file should be stored
            fout.write(x.myfile.file.read()) # writes the uploaded file to the newly created file.
            fout.close() # closes the file, upload complete.
            if magic.from_file(config.datadir + filename, mime=True) != "application/x-iso9660-image":
                os.remove(config.datadir + filename)
                raise web.seeother('{0}/upload?bad=1'.format(config.urlprefix))
        raise web.seeother('{0}/upload'.format(config.urlprefix))

class HD:
    __metaclass__ = routing.ControllerMeta
    url = '/hd/?'

    def GET(self):
       if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
       templates = web.template.render('webvirt/templates/')
       myform = web.form.Form(
               web.form.Textbox("name",web.form.notnull,description="Name of Hard Drive: ",align='left'),
               web.form.Textbox("size",web.form.notnull,description="Size of Hard Drive (GB): ",align='left')
               )
       form = myform()
       conn = web.ctx.libvirt
       data = ""
       content = "<h2>Create a New Virtual Machine Hard Drive</h2>"
       data += sidebarGen(conn)
       return templates.create(content, data, form, web.ctx.username, config.urlprefix)

    def POST(self):
       myform = web.form.Form(
               web.form.Textbox("name",web.form.notnull,description="Name of Hard Drive: ",align='left'),
               web.form.Textbox("size",web.form.notnull,description="Size of Hard Drive (GB): ",align='left')
               )
       form = myform()
       if not form.validates():
           return render.formtest(form)
       else:
           os.system('cd ' + config.datadir +  ' && qemu-img create ' + form['name'].value + ".qcow2 " + form['size'].value + 'G')
           web.seeother('/'+config.urlprefix)

class ListHD:
    __metaclass__ = routing.ControllerMeta
    url = '/listhd/?'

    def GET(self):
        if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
        templates = web.template.render('webvirt/templates/')
        if os.access(config.datadir,os.F_OK) == False:
            os.mkdir(config.datadir)
        files = os.listdir(config.datadir)
        files = [x for x in files if x.endswith('.qcow2')]
        sizes = []
        for f in files:
            for line in common.run_proc(['qemu-img', 'info', config.datadir + f]):
                if "virtual size" in line:
                    sizes.append(line.split(' ')[2])
        pack = list(zip(files, sizes))
        contents='<h2>Available Hard Drives</h2><table class="table"><tr><td><b>Name</b></td><td><b>Size</b></td></tr>'
        for f, size in pack:
            contents += "<tr><td>" + config.datadir
            contents += "%s</td><td>%s</td></tr>" % (f, size)
        contents += "</table>"
        data = ""
        conn = web.ctx.libvirt
        data += sidebarGen(conn)
	return templates.index(contents, data, web.ctx.username, config.urlprefix)

class ListISOs:
    __metaclass__ = routing.ControllerMeta
    url = '/listisos/?'

    def GET(self):
        if not web.ctx.auth:
            web.seeother("{0}/login".format(config.site_prefix))
        templates = web.template.render('webvirt/templates/')
        files = os.listdir(config.datadir)
        files = [x for x in files if x.endswith('.iso')]
        sizes = []
        for f in files:
            sizes.append(hsize(os.path.getsize(config.datadir + f)))
        pack = list(zip(files, sizes))
        contents = '<h2>Available ISOs</h2><table class="table"><tr><td><b>Name</b></td><td><b>Size</b></td></tr>'
        for f, size in pack:
            contents += "<tr><td>" + config.datadir
            contents += "%s</td><td>%s</td></tr>" % (f, size)
        contents += "</table>"
        data = ""
        conn = web.ctx.libvirt
        data += sidebarGen(conn)
	return templates.index(contents, data, web.ctx.username, config.urlprefix)
