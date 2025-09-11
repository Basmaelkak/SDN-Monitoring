# detector.py (VERSION FINALE CORRIGÉE SANS SCALER)

import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
import logging
import sqlite3
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONSTANTES ---
FEATURES_FOR_TRAINING = ['packet_ins_total', 'flow_msgs_sent_total']
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MODEL_FILE = os.path.join(BASE_DIR, 'anomaly_detector_model_cp.joblib')
DB_FILE = os.path.join(BASE_DIR, 'sdn_metrics.db')

class AnomalyDetector:
    def __init__(self):
        self.model = None

    def train(self):
        """Entraîne le modèle directement sur les données brutes, sans scaling."""
        logging.info(f"Entraînement du modèle depuis la base de données {os.path.basename(DB_FILE)}...")
        try:
            # S'assurer qu'un scaler obsolète est supprimé pour éviter toute confusion
            scaler_file_path = os.path.join(BASE_DIR, 'data_scaler_cp.joblib')
            if os.path.exists(scaler_file_path):
                os.remove(scaler_file_path)
                logging.info("Ancien fichier scaler (data_scaler_cp.joblib) supprimé.")

            con = sqlite3.connect(DB_FILE)
            df = pd.read_sql_query("SELECT * FROM metrics", con)
            con.close()

            if df.empty or len(df) < 20:
                logging.error("ERREUR : Pas assez de données pour un entraînement fiable.")
                return False

            logging.info(f"{len(df)} lignes de données chargées pour l'entraînement.")
            df_features = df[FEATURES_FOR_TRAINING].fillna(0)
            
            # On entraîne le modèle directement sur les valeurs.
            # L'algorithme apprendra les ordres de grandeur normaux.
            self.model = IsolationForest(contamination='auto', random_state=42)
            self.model.fit(df_features)
            
            joblib.dump(self.model, MODEL_FILE)
            logging.info("Modèle entraîné et sauvegardé.")
            return True
            
        except Exception as e:
            logging.error(f"ERREUR lors de l'entraînement : {e}", exc_info=True)
            return False

    def load_model(self):
        try:
            self.model = joblib.load(MODEL_FILE)
            logging.info("Modèle chargé.")
            # On s'assure qu'aucun scaler n'est chargé par erreur
            self.scaler = None
            return True
        except FileNotFoundError:
            logging.warning("Aucun modèle pré-entraîné trouvé. Lancez `python3 detector.py` pour l'entraîner.")
            return False

    def predict(self, new_data_df):
        if not self.model:
            raise Exception("Modèle non chargé.")
        
        new_features = new_data_df[FEATURES_FOR_TRAINING].fillna(0)
        
        # Prédiction directe sur les features, sans scaling
        prediction = self.model.predict(new_features)
        scores = self.model.decision_function(new_features)
        return prediction, scores

def run_tests_on_model():
    detector_test = AnomalyDetector()
    if not detector_test.load_model(): return
    logging.info("\n--- Test du modèle sur des scénarios connus ---")
    scenarios = {
        "Faible trafic (ping)": pd.DataFrame([[5, 20]], columns=FEATURES_FOR_TRAINING),
        "Trafic modéré": pd.DataFrame([[150, 200]], columns=FEATURES_FOR_TRAINING),
        "Attaque par flood": pd.DataFrame([[10000, 8000]], columns=FEATURES_FOR_TRAINING),
        "Attaque subtile (Packet-In)": pd.DataFrame([[5000, 300]], columns=FEATURES_FOR_TRAINING)
    }
    for name, sample_df in scenarios.items():
        pred, score = detector_test.predict(sample_df)
        status = "Anomalie" if pred[0] == -1 else "Normal"
        print(f"\nTest '{name}':\n  - Données: {sample_df.to_dict('records')[0]}\n  - Prédiction: {status}\n  - Score: {score[0]:.4f}")
    print("\n--- Fin des tests ---")

if __name__ == '__main__':
    if AnomalyDetector().train(): run_tests_on_model()