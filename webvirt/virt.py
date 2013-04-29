import libvirt
from common import conn
import common

class Domain:
    def __init__(self, dom):
        self.dom = dom
        self.name = dom.name()
        self.rawstate = dom.state(0)[0]
        self.state = common.getState(self.rawstate)
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

    def createDomain(self,name,mem,cpu,hd,iso,vnc,pts):
        dom = conn.defineXML("""
              <domain type="kvm">
                   <name>%s</name>
                   <memory>%s</memory>
                   <vcpu>%s</vcpu>
                   <os>
                        <type arch="x86_64">hvm</type>
                        <boot dev="cdrom"/>
                   </os>
                   <devices>
                       <disk type="block" device="disk">
                            <source dev="%s"/>
                            <target dev="hda" bus="virtio"/>
                       </disk>
                       <disk type='file' device='cdrom'>
                            <source file='%s'/>
                            <target dev='hdc' bus='ide' tray='closed'/>
                            <readonly/>
                       </disk>
                       <interface type="bridge" >
                           <mac address="02:00:c6:26:13:19"/>
                           <source bridge="vbr1900"/>
                           <model type="virtio"/>
                       </interface>
                       <graphics type="vnc" port="%s" autoport="no"/>
                       <console type='pty'>
                           <source path='/dev/pts/%s' />
                           <target type='serial' port='0' />
                       </console>
                    </devices>
                </domain>
                """ % (name,mem,cpu,hd,iso,vnc,pts))
        self.domains.append(dom)
        return dom


