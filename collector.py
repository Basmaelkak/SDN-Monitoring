# collector.py (VERSION FINALE AVEC CONTEXTE HISTORIQUE)

import requests
import time
import sqlite3
from datetime import datetime
import argparse
import logging
from prometheus_client.parser import text_string_to_metric_families
import pandas as pd
from detector import AnomalyDetector

# Configuration du logging et de la base de données
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DB_FILE = 'sdn_metrics.db'

def setup_database():
    """Crée la table 'metrics' et ajoute la colonne 'anomaly_score' si nécessaire."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            dp_id TEXT NOT NULL,
            dp_name TEXT,
            packet_ins_total REAL,
            flow_msgs_sent_total REAL,
            vlan_hosts_learned_total REAL,
            of_errors_total REAL,
            dp_disconnections_total REAL,
            anomaly_score REAL
        )
    ''')
    
    # Vérifie si la colonne existe et l'ajoute si ce n'est pas le cas
    cursor.execute("PRAGMA table_info(metrics)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'anomaly_score' not in columns:
        cursor.execute("ALTER TABLE metrics ADD COLUMN anomaly_score REAL")
        logging.info("Colonne 'anomaly_score' ajoutée à la table metrics.")

    conn.commit()
    conn.close()

def get_metrics_from_faucet(url):
    """Récupère les métriques de Faucet et les retourne dans une liste de dictionnaires."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        dp_metrics = {}

        for family in text_string_to_metric_families(response.text):
            for sample in family.samples:
                if 'dp_id' not in sample.labels:
                    continue
                
                dp_id = sample.labels['dp_id']
                
                if dp_id not in dp_metrics:
                    dp_metrics[dp_id] = {
                        'dp_id': dp_id, 'dp_name': sample.labels.get('dp_name', f'dp_{dp_id}'),
                        'packet_ins_total': 0, 'flow_msgs_sent_total': 0,
                        'vlan_hosts_learned_total': 0, 'of_errors_total': 0,
                        'dp_disconnections_total': 0,
                    }

                metric_name_map = {
                    'of_packet_ins_total': 'packet_ins_total', 'of_flowmsgs_sent_total': 'flow_msgs_sent_total',
                    'vlan_hosts_learned_total': 'vlan_hosts_learned_total', 'of_errors_total': 'of_errors_total',
                    'of_dp_disconnections_total': 'dp_disconnections_total'
                }

                if sample.name in metric_name_map:
                    if sample.name == 'vlan_hosts_learned_total':
                         dp_metrics[dp_id]['vlan_hosts_learned_total'] += sample.value
                    else:
                         dp_metrics[dp_id][metric_name_map[sample.name]] = sample.value

        return list(dp_metrics.values())
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur de connexion à Faucet: {e}")
        return []

# DANS collector.py, REMPLACEZ LA FONCTION save_metrics_to_db PAR CELLE-CI :
# DANS collector.py, REMPLACEZ LA FONCTION save_metrics_to_db PAR CELLE-CI :

def save_metrics_to_db(metrics_list, detector):
    """
    Calcule le score pour chaque métrique en utilisant un contexte historique propre
    et enregistre le tout dans la DB.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    # --- AJOUT : Définir explicitement les features attendues par le modèle ---
    # Cette liste DOIT correspondre à FEATURES_FOR_TRAINING dans detector.py
    features_for_prediction = ['packet_ins_total', 'flow_msgs_sent_total']
    # --- FIN DE L'AJOUT ---

    for metrics in metrics_list:
        dp_id = metrics.get('dp_id')
        
        # 1. Récupérer l'historique
        query = "SELECT * FROM metrics WHERE dp_id = ? ORDER BY timestamp DESC LIMIT 29"
        historical_df = pd.read_sql_query(query, conn, params=(dp_id,))
        
        # 2. Combiner avec la métrique actuelle
        current_metric_df = pd.DataFrame([metrics])
        prediction_df_raw = pd.concat([historical_df.iloc[::-1], current_metric_df], ignore_index=True)

        # 3. Nettoyer le DataFrame en utilisant notre liste de features
        clean_df = prediction_df_raw.reindex(columns=features_for_prediction).fillna(0)
        
        # 4. Prédire le score
        current_score = 0.0
        if detector.model and not clean_df.empty:
            try:
                _, scores = detector.predict(clean_df)
                current_score = scores[-1]
                
                if current_score < -0.1:
                     logging.warning(f"ANOMALIE DÉTECTÉE -> DP: {metrics.get('dp_name')}, Score: {current_score:.4f}")
                else:
                     logging.info(f"DP: {metrics.get('dp_name')}, Score: {current_score:.4f}")

            except Exception as e:
                logging.error(f"Erreur de prédiction pour DP {dp_id}: {e}")
        
        # 5. Ajouter le score et sauvegarder
        metrics['anomaly_score'] = current_score

        cursor.execute('''
            INSERT INTO metrics (
                timestamp, dp_id, dp_name, 
                packet_ins_total, flow_msgs_sent_total, vlan_hosts_learned_total, 
                of_errors_total, dp_disconnections_total, anomaly_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            metrics.get('dp_id'),
            metrics.get('dp_name'),
            metrics.get('packet_ins_total'),
            metrics.get('flow_msgs_sent_total'),
            metrics.get('vlan_hosts_learned_total'),
            metrics.get('of_errors_total'),
            metrics.get('dp_disconnections_total'),
            metrics.get('anomaly_score')
        ))
    
    conn.commit()
    conn.close()
def main(args):
    """Fonction principale du collecteur."""
    setup_database()
    logging.info(f"Collecteur démarré. Enregistrement dans {DB_FILE}")

    # Initialisation du détecteur d'anomalie
    anomaly_detector = AnomalyDetector()
    if not anomaly_detector.load_model():
        logging.warning("Le modèle d'anomalie n'a pas pu être chargé. Les scores seront à 0.")
    else:
        logging.info("Modèle d'anomalie chargé avec succès.")

    while True:
        time.sleep(args.interval) 
        all_dp_metrics = get_metrics_from_faucet(args.url)
        
        if not all_dp_metrics:
            continue
        
        save_metrics_to_db(all_dp_metrics, anomaly_detector)
        logging.info(f"Données enregistrées pour {len(all_dp_metrics)} DP(s).")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Collecteur de métriques Faucet vers une base de données SQLite.")
    parser.add_argument('--url', default='http://127.0.0.1:9302', help="URL de l'endpoint Prometheus de Faucet.")
    parser.add_argument('--interval', type=int, default=5, help="Intervalle de collecte en secondes.")
    
    parsed_args = parser.parse_args()
    
    try:
        main(parsed_args)
    except KeyboardInterrupt:
        logging.info("Arrêt du collecteur.")