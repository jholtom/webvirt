import libvirt
from .common import getState
from bs4 import BeautifulSoup
import web

class Domain:
    def __init__(self, dom):
        self.dom = dom
        self.name = dom.name()
        self.rawstate = dom.state(0)[0]
        self.state = getState(self.rawstate)
        self.memmax = dom.info()[1]
        self.memused = dom.info()[2]
        self.mempct = round(100 * (float(self.memused) / float(self.memmax)))

    def startVM(self):
        if self.rawstate != libvirt.VIR_DOMAIN_RUNNING:
            self.dom.create()

    def stopVM(self):
        if self.rawstate != libvirt.VIR_DOMAIN_SHUTOFF:
            self.dom.shutdown()

    def destroyVM(self):
        if self.rawstate != libvirt.VIR_DOMAIN_SHUTOFF:
            self.dom.destroy()

    def suspendVM(self):
        if self.rawstate == libvirt.VIR_DOMAIN_RUNNING:
            self.dom.suspend()

    def resumeVM(self):
        self.dom.resume()

    def get_dict(self):
        return {
                "name": self.name,
                "state": self.state,
                "memmax": self.memmax,
                "memused": self.memused,
                "mempct": self.mempct
                }

    def getXML(self):
        return BeautifulSoup(self.dom.XMLDesc(2),'xml')

    def setXML(self,xml):
        return web.ctx.libvirt.defineXML(str(xml))

    def getVNC(self):
        xml = self.getXML()
        if xml.domain.devices.graphics != None:
            return int(xml.domain.devices.graphics.attrs['port'])
        else:
            return -1

class HostServer:
    def __init__(self):
        conn = web.ctx.libvirt
        self.hostname = conn.getHostname()
        self.hosttype = conn.getType()
        self.caps = conn.getCapabilities()
        self.cpustats = conn.getCPUStats(libvirt.VIR_NODE_CPU_STATS_ALL_CPUS,0)
        self.cpumap = conn.getCPUMap(0)
        self.info = conn.getInfo()
        self.memstats = conn.getMemoryStats(libvirt.VIR_NODE_MEMORY_STATS_ALL_CELLS,0)
        self.domains = [Domain(dom) for dom in conn.listAllDomains(0)]

    def createDomain(self,name,mem,numcpus,vncport):
        #def createDomain(self,name,mem,cpu,hd,iso,vnc,pts):
        xml = BeautifulSoup('<domain/>','xml')
        dom = xml.domain
        dom.attrs['type'] = 'kvm'

        # can't use dom.name because it's a builtin property
        nametag = xml.new_tag('name')
        nametag.string = name
        dom.append(nametag)

        dom.append(xml.new_tag('memory'))
        dom.memory.attrs['unit'] = 'MiB'
        dom.memory.string = mem

        dom.append(xml.new_tag('vcpu'))
        dom.vcpu.string = numcpus

        dom.append(xml.new_tag('os'))
        dom.os.append(xml.new_tag('type'))
        dom.os.type.string = 'hvm'

        dom.append(xml.new_tag('devices'))
        dom.devices.append(xml.new_tag('graphics'))
        dom.devices.graphics.attrs['type'] = 'vnc'
        dom.devices.graphics.attrs['port'] = vncport

        virdom = web.ctx.libvirt.defineXML(str(xml))
        self.domains.append(virdom)
        return dom

def virt_processor(handle):
    conn = libvirt.open(None)
    web.ctx.libvirt = conn
    web.ctx.proxylist = {}
    ret = handle()
    virt_cleanup(conn, web.ctx.proxylist)
    return ret

def virt_cleanup(conn, proxylist={}):
    for proc in proxylist.values():
        proc.terminate()
    conn.close()
