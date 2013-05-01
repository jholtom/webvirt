import libvirt
from common import conn, getState
from bs4 import BeautifulSoup

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

class HostServer:
    def __init__(self):
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

        virdom = conn.defineXML(str(xml))
        self.domains.append(virdom)
        return dom
