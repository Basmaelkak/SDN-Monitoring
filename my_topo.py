# my_topo.py

from mininet.topo import Topo

class MyTopo( Topo ):
    "Topologie personnalisée avec 2 switches et 4 hôtes."

    def build( self ):
        "Créer la topologie."

        # Ajouter les switches
        s1 = self.addSwitch( 's1' )
        s2 = self.addSwitch( 's2' )

        # Ajouter les hôtes
        h1 = self.addHost( 'h1', ip='10.0.0.1/24' )
        h2 = self.addHost( 'h2', ip='10.0.0.2/24' )
        h3 = self.addHost( 'h3', ip='10.0.0.3/24' )
        h4 = self.addHost( 'h4', ip='10.0.0.4/24' )

        # Créer les liens Hôte <-> Switch
        # h1 et h2 sont sur s1
        self.addLink( h1, s1, port1=1, port2=1 )
        self.addLink( h2, s1, port1=1, port2=2 )

        # h3 et h4 sont sur s2
        self.addLink( h3, s2, port1=1, port2=1 )
        self.addLink( h4, s2, port1=1, port2=2 )

        # Créer le lien Trunk Switch <-> Switch
        self.addLink( s1, s2, port1=3, port2=3 )

# Permet d'exécuter cette topologie directement
topos = { 'mytopo': ( lambda: MyTopo() ) }
