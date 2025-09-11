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
- [Notifications Email](#notifications-email)
- [Topologie Mininet](#topologie-mininet)
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

- **VM** avec Mininet et Faucet installés
- Python 3.8+
- Bibliothèques Python :  
  ```bash
  pip install flask flask-login sqlalchemy pandas numpy scikit-learn requests graphviz sib_api_v3_sdk


