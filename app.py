# --- IMPORTS ---
import os
import graphviz
import sqlite3
import logging
import yaml
from datetime import datetime, timedelta
from flask import Flask, render_template, url_for, jsonify, request, redirect, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import numpy as np
# Importation de votre détecteur et des outils pour l'email
from detector import AnomalyDetector 
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# --- CONFIGURATION DU LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- INITIALISATION DE L'APPLICATION FLASK ---
app = Flask(__name__)

# --- CONFIGURATION DES CHEMINS ET CONSTANTES ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
METRICS_DB_FILE = os.path.join(BASE_DIR, 'sdn_metrics.db')
USER_DB_FILE = os.path.join(BASE_DIR, 'users.db')
FAUCET_CONFIG_FILE = '/home/mininet/faucet-env/etc/faucet/faucet.yaml' 
CHART_POINTS = 30
ANOMALY_SCORE_THRESHOLD = -0.15

# --- CONFIGURATION FLASK ---
app.config['SECRET_KEY'] = 'a79b38249e924ad813cb4aa95dfe20f710ca8525fa3a91e1f9bad7eca1c06084'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{USER_DB_FILE}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- CONFIGURATION BREVO POUR LES EMAILS ---
app.config['BREVO_API_KEY'] = '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'
app.config['SENDER_EMAIL'] = 'kak.basma08@gmail.com'
app.config['SENDER_NAME'] = 'SDN Monitor Alert'

# --- INITIALISATION DES EXTENSIONS ---
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "info"

# --- MODÈLE UTILISATEUR ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- LOGIQUE DE L'APPLICATION (DÉTECTEUR) ---
anomaly_detector = AnomalyDetector()
model_loaded = anomaly_detector.load_model()
if not model_loaded:
    logging.warning("Modèle de détection non chargé. Lancez `python3 detector.py` pour l'entraîner.")
# Cette variable globale gardera en mémoire les switchs pour lesquels une alerte a déjà été envoyée
notified_anomalies = set() 

# --- FONCTION D'ENVOI D'EMAIL ---
def send_alert_email_brevo(recipient_email, switch_name, score, threshold):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = app.config['BREVO_API_KEY']
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    subject = f"🚨 Alerte d'Anomalie sur le switch {switch_name}"
    html_content = f"<h1>Alerte de Sécurité SDN</h1><p>Une anomalie a été détectée sur le switch <strong>{switch_name}</strong>.</p><p>Score de l'anomalie: <strong>{score:.4f}</strong> (Seuil: {threshold}).</p><p>Veuillez vérifier le dashboard.</p>"
    sender = {"name": app.config['SENDER_NAME'], "email": app.config['SENDER_EMAIL']}
    to = [{"email": recipient_email}]
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(to=to, html_content=html_content, sender=sender, subject=subject)
    try:
        api_instance.send_transac_email(send_smtp_email)
        logging.info(f"Email d'alerte pour {switch_name} envoyé à {recipient_email}.")
    except ApiException as e:
        logging.error(f"Erreur lors de l'envoi de l'email via Brevo: {e}")

# --- ROUTES D'AUTHENTIFICATION ---
# ... (vos routes login, register, logout ici, elles sont correctes) ...
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        identifier = request.form['username']
        password = request.form['password']
        user = User.query.filter(or_(User.username == identifier, User.email == identifier)).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants invalides.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter(or_(User.username == username, User.email == email)).first()
        if existing_user:
            flash('Le nom d\'utilisateur ou l\'adresse email est déjà utilisé(e).', 'warning')
            return redirect(url_for('register'))
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Votre compte a été créé ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('login'))


# --- FONCTION UTILITAIRE ---
def format_total(value):
    if not isinstance(value, (int, float)) or np.isnan(value): return "0"
    return str(int(value))

# --- ROUTES DE L'APPLICATION ---
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

# DANS VOTRE app.py, REMPLACEZ LA FONCTION history() EXISTANTE PAR CELLE-CI :

# DANS VOTRE app.py, REMPLACEZ LA FONCTION history() EXISTANTE PAR CELLE-CI :
# DANS VOTRE app.py, REMPLACEZ À NOUVEAU LA FONCTION history()

@app.route('/history')
@login_required
def history():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    default_start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    default_end_date = datetime.now().strftime('%Y-%m-%d')
    
    records = []
    time_chart_data = { 'labels': [], 'anomaly_scores': [], 'packet_ins': [] }
    pie_chart_data = {} # On initialise les données pour les graphiques circulaires

    try:
        con = sqlite3.connect(METRICS_DB_FILE)
        query = "SELECT * FROM metrics"
        params = []
        if start_date_str and end_date_str:
            query += " WHERE date(timestamp) BETWEEN ? AND ?"
            params.extend([start_date_str, end_date_str])
        
        df_all = pd.read_sql_query(query, con, params=params)
        con.close()
        
        if not df_all.empty:
            df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
            df_all.sort_values(by='timestamp', inplace=True)
            
            if 'anomaly_score' not in df_all.columns:
                df_all['anomaly_score'] = 0.0
            df_all['anomaly_score'] = df_all['anomaly_score'].fillna(0.0)

            # Préparation des données pour le tableau
            records = [ row.to_dict() for index, row in df_all.iterrows() ]

            # --- LOGIQUE POUR LES GRAPHIQUES CIRCULAIRES (RÉINTÉGRÉE) ---
            numeric_cols = ['packet_ins_total', 'flow_msgs_sent_total']
            for col in numeric_cols:
                df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0)
            
            df_pie_data = df_all.groupby('dp_name')[numeric_cols].sum().reset_index()
            pie_chart_data = {
                'packet_ins': {
                    'labels': df_pie_data['dp_name'].tolist(),
                    'data': df_pie_data['packet_ins_total'].tolist()
                },
                'flow_msgs': {
                    'labels': df_pie_data['dp_name'].tolist(),
                    'data': df_pie_data['flow_msgs_sent_total'].tolist()
                }
            }
            # --- FIN DE LA LOGIQUE ---

            # Préparation des données pour le graphique temporel
            sample_df = df_all
            if len(df_all) > 1000:
                step = len(df_all) // 1000
                sample_df = df_all.iloc[::step]
            
            time_chart_data['labels'] = [ts.isoformat() for ts in sample_df['timestamp']]
            time_chart_data['anomaly_scores'] = sample_df['anomaly_score'].tolist()
            time_chart_data['packet_ins'] = sample_df['packet_ins_total'].fillna(0).tolist()

        if not start_date_str: start_date_str = default_start_date
        if not end_date_str: end_date_str = default_end_date

    except Exception as e:
        logging.error(f"Erreur dans la route /history: {e}", exc_info=True)
        flash("Une erreur est survenue lors du chargement de l'historique.", "danger")
        start_date_str = default_start_date
        end_date_str = default_end_date

    return render_template(
        'history.html', 
        records=records, 
        start_date=start_date_str, 
        end_date=end_date_str,
        time_chart_data=time_chart_data,
        pie_chart_data=pie_chart_data  # <-- PASSER LES DONNÉES AU TEMPLATE
    )
@app.route('/configuration')
@login_required
def configuration():
    config_content, error_message = "", None
    try:
        with open(FAUCET_CONFIG_FILE, 'r') as f: config_content = f.read()
    except FileNotFoundError: error_message = f"Le fichier de configuration Faucet est introuvable à : {FAUCET_CONFIG_FILE}"
    except Exception as e: error_message = f"Erreur de lecture du fichier : {e}"
    return render_template('configuration.html', config_content=config_content, error_message=error_message, config_file_path=FAUCET_CONFIG_FILE)

# --- ROUTES API ---
# Dans app.py, remplacez la fonction /api/data

@app.route('/api/data')
@login_required
def get_data():
    kpis, switches_data = {}, {}
    try:
        con = sqlite3.connect(METRICS_DB_FILE)
        df = pd.read_sql_query("SELECT * FROM metrics", con)
        con.close()
        if df.empty: raise pd.errors.EmptyDataError
        
        latest_per_dp = df.groupby('dp_id').tail(1)
        kpis['num_dps'] = len(latest_per_dp)
        kpis['total_packet_ins_str'] = format_total(latest_per_dp['packet_ins_total'].sum())
        kpis['total_flow_msgs_str'] = format_total(latest_per_dp['flow_msgs_sent_total'].sum())
        kpis['total_errors_str'] = format_total(latest_per_dp['of_errors_total'].sum())

        network_has_anomaly = False
        for dp_id, group in df.groupby('dp_id'):
            latest_data_df = group.tail(1)
            if latest_data_df.empty: continue
            
            latest_data_series = latest_data_df.iloc[0]
            history = group.tail(CHART_POINTS).copy()
            
            is_switch_active = (latest_data_series['packet_ins_total'] > 0 or latest_data_series['flow_msgs_sent_total'] > 0)
            is_anomaly, current_score = False, 0.0
            
            if model_loaded and is_switch_active:
                try:
                    # La prédiction est faite ici
                    _, scores = anomaly_detector.predict(latest_data_df)
                    current_score = scores[0]

                    # Si le score est sous le seuil, on déclenche l'état d'anomalie
                    if current_score < ANOMALY_SCORE_THRESHOLD:
                        is_anomaly = True
                        if dp_id not in notified_anomalies:
                            send_alert_email_brevo(
                                recipient_email=current_user.email,
                                switch_name=latest_data_series['dp_name'],
                                score=current_score,
                                threshold=ANOMALY_SCORE_THRESHOLD
                            )
                            notified_anomalies.add(dp_id)
                    else:
                        # Si le score remonte au-dessus du seuil, on retire l'état d'anomalie
                        if dp_id in notified_anomalies:
                            notified_anomalies.remove(dp_id)
                except Exception as e:
                    logging.error(f"Erreur de prédiction pour {dp_id}: {e}")

            # On met à jour l'état global du réseau
            if len(notified_anomalies) > 0:
                network_has_anomaly = True

            switches_data[dp_id] = {
                'dp_name': latest_data_series['dp_name'],
                # L'état 'is_anomaly' reflète la détection actuelle, la persistance est gérée par le JS
                'is_anomaly': is_anomaly,
                'anomaly_score': f"{current_score:.4f}",
                'anomaly_threshold': ANOMALY_SCORE_THRESHOLD,
                'latest_metrics': {
                    'packet_ins_total': format_total(latest_data_series['packet_ins_total']), 
                    'flow_msgs_sent_total': format_total(latest_data_series['flow_msgs_sent_total']), 
                    'vlan_hosts_learned_total': format_total(latest_data_series['vlan_hosts_learned_total']), 
                    'of_errors_total': format_total(latest_data_series['of_errors_total'])
                },
                'chart_data': {
                    'timestamps': list(history['timestamp']), 
                    'traffic_total': list(history['flow_msgs_sent_total']), 
                    'chart_label_total': 'Total Cumulatif des Flow-Mods',
                    'borderColor': 'rgba(220, 53, 69, 0.8)' if is_anomaly else 'rgba(13, 202, 240, 0.8)',
                    'backgroundColor': 'rgba(220, 53, 69, 0.2)' if is_anomaly else 'rgba(13, 202, 240, 0.2)'
                }
            }
        
        if network_has_anomaly:
            kpis['network_status'], kpis['status_color'] = '🚨 ANOMALIE', 'danger'
        else:
            kpis['network_status'], kpis['status_color'] = '✅ ACTIF', 'success'

    except (sqlite3.OperationalError, pd.errors.EmptyDataError):
        kpis['network_status'], kpis['status_color'] = '📄 INDISPONIBLE', 'warning'
        kpis['error_message'] = "Base de données non trouvée ou vide."
    except Exception as e:
        kpis['network_status'], kpis['status_color'] = '🔥 ERREUR APP', 'danger'
        kpis['error_message'] = f"Erreur inattendue : {e}"
        
    return jsonify({'kpis': kpis, 'switches': switches_data})

# DANS app.py, remplacez la fonction topology_page par celle-ci :

# DANS app.py, remplacez la fonction topology_page par celle-ci :

@app.route('/topology')
@login_required
def topology_page():
    """
    Cette route génère l'image de la topologie à chaque fois qu'on charge la page
    et retourne le template qui l'affichera.
    """
    try:
        images_dir = os.path.join(BASE_DIR, 'static', 'images')
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
            
        switch_icon_path = os.path.join(images_dir, 'switch_icon.png')
        host_icon_path = os.path.join(images_dir, 'host_icon2.png')

        if not os.path.exists(switch_icon_path) or not os.path.exists(host_icon_path):
            flash("Fichiers d'icônes manquants dans static/images/. Utilisation des formes par défaut.", "warning")
            # Pour l'instant, on suppose que les fichiers existent
        
        with open(FAUCET_CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        
        dps = config.get('dps', {})
        if not dps:
            flash("Aucun switch (dps) défini dans faucet.yaml.", "warning")
            return render_template('topology_simple.html', image_file=None)

        # Créer le graphe avec des attributs pour mieux gérer les images
        dot = graphviz.Graph('sdn_topology', comment='Topologie du réseau SDN')
        dot.attr('graph', 
                 rankdir='TB',           # De haut en bas
                 splines='true',         # Lignes légèrement courbées, plus joli
                 overlap='false',        # Tente d'éviter les superpositions
                 bgcolor='transparent')
        dot.attr('node', 
                 fontname='sans-serif', 
                 fontsize='10', 
                 labelloc='b')           # Labels en bas (bottom)
        dot.attr('edge', 
                 fontname='sans-serif', 
                 fontsize='8')

        host_counter = 1
        for dp_name, dp_config in dps.items():
            # --- MODIFIÉ : Configuration plus robuste pour les nœuds images ---
            dot.node(dp_name, 
                     label=dp_name, 
                     image=switch_icon_path, 
                     shape='box',            # Utiliser 'box' comme base
                     style='filled',         # Nécessaire pour bgcolor
                     fillcolor='transparent',# Rend le fond de la boîte transparent
                     penwidth='0',           # Supprime la bordure de la boîte
                     fixedsize='true',       # Fixe la taille
                     width='0.7', height='0.7') # Taille de l'icône en pouces

            for port_num, port_config in dp_config.get('interfaces', {}).items():
                if 'native_vlan' in port_config:
                    host_label = port_config.get('description', f'Hote {host_counter}')
                    
                    # --- MODIFIÉ : Configuration plus robuste pour les nœuds images ---
                    dot.node(host_label, 
                             label=host_label, 
                             image=host_icon_path, 
                             shape='box', 
                             style='filled',
                             fillcolor='transparent',
                             penwidth='0',
                             fixedsize='true', 
                             width='0.6', height='0.6')

                    dot.edge(dp_name, host_label, label=f' port {port_num}')
                    host_counter += 1

        # Ajouter les liens "trunk" (pas de changement ici)
        edges_done = set()
        for dp_name, dp_config in dps.items():
            for port_num, port_config in dp_config.get('interfaces', {}).items():
                 if 'tagged_vlans' in port_config:
                    description = port_config.get('description', '').lower()
                    for other_dp in dps:
                        if other_dp != dp_name and other_dp in description:
                            edge_pair = tuple(sorted((dp_name, other_dp)))
                            if edge_pair not in edges_done:
                                dot.edge(dp_name, other_dp, label='trunk', style='dashed')
                                edges_done.add(edge_pair)

        image_filename = 'topology.png' # On passe en PNG pour une meilleure compatibilité
        output_path_without_ext = os.path.join(images_dir, 'topology')
        dot.render(output_path_without_ext, format='png', cleanup=True)
        
        return render_template('topology_simple.html', image_file=f'images/{image_filename}')

    except FileNotFoundError:
        flash(f"Fichier de config '{os.path.basename(FAUCET_CONFIG_FILE)}' introuvable.", "danger")
        return render_template('topology_simple.html', image_file=None)
    except Exception as e:
        logging.error(f"Erreur lors de la génération de la topologie: {e}", exc_info=True)
        flash(f'Erreur interne du serveur: {e}', "danger")
        return render_template('topology_simple.html', image_file=None)


# --- BLOC D'EXÉCUTION PRINCIPAL ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)