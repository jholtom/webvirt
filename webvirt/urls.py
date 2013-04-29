"""
    WebVirt URL Handlers
"""
import auth
import common
import config
import libvirt
from connection import conn
import virt
import web
import os
from pymagic import magic
import subprocess
import sys
from hurry.filesize import size as hsize

class Index:
    def GET(self):
        auth.verify_auth("http://" + config.urlprefix + "/hackathon/login")
        templates = web.template.render('webvirt/templates/')
        content = ""
        numVMs = float(len(conn.listAllDomains(0)))
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
        for dom in conn.listAllDomains(0):   
            dom = virt.Domain(dom)
            if(dom.rawstate == libvirt.VIR_DOMAIN_RUNNING):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-success'>" + dom.state + "</span></div></a></li>"
            elif(dom.rawstate == libvirt.VIR_DOMAIN_SHUTOFF):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-important'>" + dom.state + "</span></div></a></li>"
            else:
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-warning'>" + dom.state + "</span></div></a></li>"
        return templates.index(content, data,web.cookies().get("session"))

class VM:
    def GET(self):
        cookies = web.cookies()
        if cookies.get("session") == None:
            web.seeother("http://" + config.urlprefix + "/hackathon/login")
        templates = web.template.render('webvirt/templates/')
        data2 = web.input()
        content = ""
        vm = data2['vm']
        domObj = virt.Domain(conn.lookupByName(vm))
        if 'action' in data2.keys():
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
        content += "<div class=\"btn-group\">\n<a class=\"btn dropdown-toggle\" data-toggle=\"dropdown\" href=\"#\">Power Options<span class=\"caret\"></span></a>\n<ul class=\"dropdown-menu\"><li    ><a href=\"/hackathon/vm?vm=" + vm + "&action=start\">Start</a></li>\n<li><a href=\"/hackathon/vm?vm=" + vm + "&action=stop\">Stop</a></li>\n<li><a href=\"/hackathon/vm?vm=" + vm + "&action=destroy\">Destroy</a></li>\n<li><a href=\"/hackathon/vm?vm=" + vm + "&action=suspend\">Suspend</a></li>\n<li><a href=\"/hackathon/vm?vm=" + vm + "&action=resume\">Resume</a></li></ul></div>"
        vmdict = domObj.get_dict()
        #mempct = str(vmdict['mempct']) + '%'
        #content += str(templates.vmmemory(mempct))
        content += "<br /><br />"
        content += "<a href='http://" + config.urlprefix + "/novnc/vnc.html?host=www.tjhsst.edu&port=6080'><button class=\"btn btn-info\">Launch Display Connection</button></a>"  
        data = ""
        for dom in conn.listAllDomains(0):
            dom = virt.Domain(dom)
            if(dom.rawstate == libvirt.VIR_DOMAIN_RUNNING):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-success'>" + dom.state + "</span></div></a></li>"
            elif(dom.rawstate == libvirt.VIR_DOMAIN_SHUTOFF):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-important'>" + dom.state + "</span></div></a></li>"
            else:
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-warning'>" + dom.state + "</span></div></a></li>"
        return templates.vm(content, data, vm,web.cookies().get("session"))

class Create:
    def GET(self):
        cookies = web.cookies()
        if cookies.get("session") == None:
            web.seeother("http://" + config.urlprefix + "/hackathon/login")
        templates = web.template.render('webvirt/templates/')
        myform = web.form.Form( 
                web.form.Textbox("name",web.form.notnull,description="Name of Virtual Machine: ",align='left'),
                web.form.Textbox("mem",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="Amount of Memory (in KiB): ",align='left'),
                web.form.Textbox("cpu",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="Number of Virtual Processors: ",align='left'),
                web.form.Textbox("hd",web.form.notnull,description='Full Path to hard drive file: ',align='left'),
                web.form.Textbox("iso",web.form.notnull,description="Full Path to cdrom iso file (e.x /var/hackfiles/gentoo.iso): ",align='left'),
                web.form.Textbox("vnc",web.form.notnull,description="VNC Port Number: ",align='left'),
                web.form.Textbox("pts",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="PTS number for serial console: ",align='left')
                )
        form = myform()
        data = ""
        content = "<h2>Create a New VM</h2>"
        for dom in conn.listAllDomains(0):
            dom = virt.Domain(dom)
            if(dom.rawstate == libvirt.VIR_DOMAIN_RUNNING):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-success'>" + dom.state + "</span></div></a></li>"
            elif(dom.rawstate == libvirt.VIR_DOMAIN_SHUTOFF):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-important'>" + dom.state + "</span></div></a></li>"
            else:
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-warning'>" + dom.state + "</span></div></a></li>"
        return templates.create(content, data,form,web.cookies().get("session"))

    def POST(self): 
        myform = web.form.Form( 
                web.form.Textbox("name",web.form.notnull,description="Name of Virtual Machine: ",align='left'),
                web.form.Textbox("mem",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="Amount of Memory (in KiB): ",align='left'),
                web.form.Textbox("cpu",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="Number of Virtual Processors: :",align='left'),
                web.form.Textbox("hd",web.form.notnull,description="Full Path to hard drive file (e.x /var/hackfiles/$name.qcow2): ",align='left'),
                web.form.Textbox("iso",web.form.notnull,description="Full Path to cdrom iso file (e.x /var/hackfiles/gentoo.iso): ",align='left'),
                web.form.Textbox("vnc",web.form.notnull,description="VNC Port Number: ",align='left'),
                web.form.Textbox("pts",web.form.notnull,web.form.regexp('\d+', 'Must be a digit'),description="PTS number for serial console: ",align='left')
                )
        form = myform() 
        if not form.validates(): 
            return web.template.render.formtest(form)
        else:
            hs = virt.HostServer()
            hs.createDomain(form['name'].value, form['mem'].value, form['cpu'].value, form['hd'].value, form['iso'].value, form['vnc'].value ,form['pts'].value)
            web.seeother("http://" + config.urlprefix + "/hackathon/")  

class Auth:
    def GET(self):
        web.header('Content-type', 'text/html')
        return "<h1>Incorrect method</h1>"

    def POST(self):
        data = web.input()
        try:
            username = data['username']
            password = data['password']
            if auth.authuser(username, password):
                if 'redirect' in data:
                    web.seeother(data['redirect'])
                else:
                    web.seeother("http://" + config.urlprefix + "/hackathon/")
            else:
                web.seeother("http://" + config.urlprefix + "/hackathon/login?failed=1")
        except Exception as e:
            return "Caught " + str(e) + " on login auth"

class Logout:
    def GET(self):
        auth.destroy_session()
        web.seeother("http://" + config.urlprefix + "/hackathon/")

class Login:
    def GET(self):
        if auth.verify_auth():
            web.seeother("http://" + config.urlprefix + "/hackathon/")
        templates = web.template.render('webvirt/templates/')
        data = web.input()
        if "failed" in data:
            return templates.login('<span><p style="color:#FF0000">Failed Login</p></span>')
        else:
            return templates.login('')

class List:
    def GET(self):
        auth.verify_auth("http://" + config.urlprefix + "/hackathon/login")
        data = []
        for dom in conn.listAllDomains(0):
            data[dom] = Domain(dom)
        return web.template.render('webvirt/templates/').index(data)

class Console:
    def GET(self):
        auth.verify_auth("http://" + config.urlprefix + "/hackathon/login")
        templates = web.template.render('webvirt/templates/')
        return templates.console()

class Upload:
    def GET(self):
        params = web.input()
        if 'bad' in params.keys() and int(params['bad']) == 1:
            return web.template.render("webvirt/templates/").index("<div class=\"alert\"><strong>Error! Your uploaded file was not an ISO file.</strong></div>", "", web.cookies().get("session"))
        content = """
        <h2>Upload CDROM/DVDROM ISO file</h2>
        <form method="POST" enctype="multipart/form-data" action="">
        <input type="file" name="myfile" />
        <br/>
        <input type="submit" />
        </form>"""
        data = ""
        for dom in conn.listAllDomains(0):
            dom = virt.Domain(dom)
            if(dom.rawstate == libvirt.VIR_DOMAIN_RUNNING):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-success'>" + dom.state + "</span></div></a></li>"
            elif(dom.rawstate == libvirt.VIR_DOMAIN_SHUTOFF):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-important'>" + dom.state + "</span></div></a></li>"
            else:
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-warning'>" + dom.state + "</span></div></a></li>"
        templates = web.template.render("webvirt/templates/")
        return templates.index(content, data, web.cookies().get("session"))

    def POST(self):
        x = web.input(myfile={})
        filedir = '/var/hackfiles/' # change this to the directory you want to store the file in.
        if 'myfile' in x: # to check if the file-object is created
            filepath=x.myfile.filename.replace('\\','/') # replaces the windows-style slashes with linux ones.
            filename=filepath.split('/')[-1] # splits the and chooses the last part (the filename with extension)
            fout = open(filedir +'/'+ filename,'w') # creates the file where the uploaded file should be stored
            fout.write(x.myfile.file.read()) # writes the uploaded file to the newly created file.
            fout.close() # closes the file, upload complete.
            if magic.from_file(filedir + filename, mime=True) != "application/x-iso9660-image":
                os.remove(filedir + filename)
                raise web.seeother('http://' + config.urlprefix + '/hackathon/upload?bad=1')
        raise web.seeother('http://' + config.urlprefix + '/hackathon/upload')

class HD:
    def GET(self):
       cookies = web.cookies()
       if cookies.get("session") == None:
           web.seeother("http://" + config.urlprefix + "/hackathon/login")
       templates = web.template.render('webvirt/templates/')
       myform = web.form.Form(
               web.form.Textbox("name",web.form.notnull,description="Name of Hard Drive: ",align='left'),
               web.form.Textbox("size",web.form.notnull,description="Size of Hard Drive (GB): ",align='left')
               )
       form = myform()
       data = ""
       content = "<h2>Create a New Virtual Machine Hard Drive</h2>"
       for dom in conn.listAllDomains(0):
           dom = virt.Domain(dom)
           if(dom.rawstate == libvirt.VIR_DOMAIN_RUNNING):
               data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-success'>" + dom.state + "</span></div></a></li>"
           elif(dom.rawstate == libvirt.VIR_DOMAIN_SHUTOFF):
               data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-important'>" + dom.state + "</span></div></a></li>"
           else:
               data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-warning'>" + dom.state + "</span></div></a></li>"
       return templates.create(content, data,form,web.cookies().get("session"))

    def POST(self):
       myform = web.form.Form(
               web.form.Textbox("name",web.form.notnull,description="Name of Hard Drive: ",align='left'),
               web.form.Textbox("size",web.form.notnull,description="Size of Hard Drive (GB): ",align='left')
               )
       form = myform()
       if not form.validates():
           return render.formtest(form)
       else:
           os.system('cd /var/hackfiles && qemu-img create ' + form['name'].value + ".qcow2 " + form['size'].value + 'G')
           web.seeother("http://" + config.urlprefix + "/hackathon/")

class ListHD:
    def GET(self):
        auth.verify_auth("http://" + config.urlprefix + "/hackathon/login")
        templates = web.template.render('webvirt/templates/')
        files = os.listdir('/var/hackfiles/')
        files = [x for x in files if x.endswith('.qcow2')]
        sizes = []
        for f in files:
            for line in common.run_proc(['qemu-img', 'info', '/var/hackfiles/' + f]):
                if "virtual size" in line:
                    sizes.append(line.split(' ')[2])
        pack = zip(files, sizes)
        contents='<h2>Available Hard Drives</h2><table class="table"><tr><td><b>Name</b></td><td><b>Size</b></td></tr>'
        for f, size in pack:
            contents += "<tr><td>/var/hackfiles/%s</td><td>%s</td></tr>" % (f, size)
        contents += "</table>"
        data = ""
        for dom in conn.listAllDomains(0):
            dom = virt.Domain(dom)
            if(dom.rawstate == libvirt.VIR_DOMAIN_RUNNING):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-success'>" + dom.state + "</span></div></a></li>"
            elif(dom.rawstate == libvirt.VIR_DOMAIN_SHUTOFF):
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-important'>" + dom.state + "</span></div></a></li>"
            else:
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-warning'>" + dom.state + "</span></div></a></li>"
        return templates.index(contents, data, web.cookies().get("session"))

class ListISOs:
    def GET(self):
        auth.verify_auth("http://" + config.urlprefix + "/hackathon/login")
        templates = web.template.render('webvirt/templates/')
        files = os.listdir('/var/hackfiles/')
        files = [x for x in files if x.endswith('.iso')]
        sizes = []
        for f in files:
            sizes.append(hsize(os.path.getsize('/var/hackfiles/' + f)))
        pack = zip(files, sizes)
        contents = '<h2>Available ISOs</h2><table class="table"><tr><td><b>Name</b></td><td><b>Size</b></td></tr>'
        for f, size in pack:
            contents += "<tr><td>/var/hackfiles/%s</td><td>%s</td></tr>" % (f, size)
        contents += "</table>"
        data = ""
        for dom in conn.listAllDomains(0):
            dom = virt.Domain(dom)
            if dom.rawstate == libvirt.VIR_DOMAIN_RUNNING:
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-success'>" + dom.state + "</span></div></a></li>"
            elif dom.rawstate == libvirt.VIR_DOMAIN_SHUTOFF:
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-important'>" + dom.state + "</span></div></a></li>"
            else:
                data += "<li><a href='/hackathon/vm?vm=" + dom.name + "'>" + dom.name + "<div class='pull-right'><span class='label label-warning'>" + dom.state + "</span></div></a></li>"
        return templates.index(contents, data, web.cookies().get("session"))

classes  = globals()
