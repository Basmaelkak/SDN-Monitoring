# SDN Monitoring & Anomaly Detection

![SDN Logo](static/images/sdn_logo.png)

## Table des matières

- [Présentation](#présentation)
- [Architecture](#architecture)
- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation et Configuration](#installation-et-configuration)
- [Exécution](#exécution)
- [Collecte des métriques](#collecte-des-métriques)
- [Détection d'anomalies](#détection-danomalies)
- [Dashboard Flask](#dashboard-flask)
- [Contributeur](#contributeur)
- [Licence](#licence)

---

## Présentation

Ce projet permet de **monitorer un réseau SDN basé sur Faucet**, collecter les métriques Prometheus, détecter des anomalies et alerter les administrateurs par email.  
L’application inclut un **dashboard Flask** pour visualiser les métriques réseau et les anomalies.

---

## Architecture

- **Mininet** : topologie SDN simulée
- **Faucet** : contrôleur SDN exposant les métriques Prometheus
- **Collector** : récupère et stocke les métriques dans SQLite
- **AnomalyDetector** : détection d’anomalies avec IsolationForest
- **Dashboard Flask** : visualisation et gestion des alertes
- **Email Alerts** : notification des anomalies

---

## Fonctionnalités

- Collecte et stockage des métriques SDN (Packet-In, Flow-Mod, VLAN, erreurs)
- Détection automatique d’anomalies avec IsolationForest
- Dashboard Flask :
  - Vue d’ensemble du réseau (KPI)
  - Graphiques temporels et circulaires
  - Historique filtrable
  - Visualisation de la topologie réseau
- Notifications par email en cas d’anomalie

---

## Prérequis

- **VM** avec Mininet(v2.3.0) et Faucet(v1.10) installés
- Python 3.8+
- une clé API depuis Brevo pour l'envois des emails 
---

## installation-et-configuration

- Ouvrir une session SSH depuis VS Code vers la VM
- Cloner le projet dans un dossier de la VM:git clone https://github.com/USERNAME/SDN-Monitoring.git
cd SDN-Monitoring
- Installer les dépendances Python: pip install flask flask-login sqlalchemy pandas numpy scikit-learn requests graphviz sib_api_v3_sdk

## exécution 

- Lancer Faucet dans la VM:faucet --verbose
- Lancer la topologie Mininet dans la VM: sudo mn --custom ./my_topo.py --topo mytopo --controller=remote,ip=127.0.0.1,port=6653 --switch ovs,protocols=OpenFlow13
- Lancer le collecteur de métriques: python3 collector.py
- Lancer le dashboard Flask: python3 app.py


## collecte des métriques
- Fichier : collector.py
- Récupère les métriques Prometheus exposées par Faucet
-Stocke les données dans SQLite (sdn_metrics.db) pour analyse

## Détection d’anomalies
- Fichier : detector.py
- l'algorithme IsolationForest pour détecter les anomalies
- Déclenche l’envoi d’alertes email


##  Dashboard Flask
- Authentification avec Flask-Login
- Graphiques temporels et circulaires
- Historique filtrable
- Visualisation de la topologie réseau

##  Contributeur

Basma El Kak – Développement complet

##  Licence

Ce projet est sous licence MIT. 






  
  


