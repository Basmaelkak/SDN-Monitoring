# Fichier : topo.py
#!/usr/bin/python3
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel

class FaucetStackTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1', dpid='0000000000000001')
        s2 = self.addSwitch('s2', dpid='0000000000000002')
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        self.addLink(h1, s1, port1=1, port2=1)
        self.addLink(h2, s2, port1=1, port2=1)
        # Lien de stack : port 2 de s1 <--> port 2 de s2
        self.addLink(s1, s2, port1=2, port2=2)

def run():
    topo = FaucetStackTopo()
    c0 = RemoteController('c0', ip='127.0.0.1', port=6653)
    net = Mininet(topo=topo, controller=c0, autoSetMacs=True, waitConnected=True)
    net.start()
    print("[INFO] Attente de 10s pour la configuration de Faucet...")
    CLI(net, script='sleep 10')
    print("[Test] Ping de h1 vers h2")
    net.pingPair()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')