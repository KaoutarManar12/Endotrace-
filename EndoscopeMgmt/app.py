import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

from database import DatabaseManager
from auth import check_authentication, login_form, logout, get_user_role, get_username, require_role
from email_alerts import EmailAlertManager

# Page configuration
st.set_page_config(
    page_title="EndoTrace - Système de Traçabilité",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
def init_database():
    return DatabaseManager()

db = init_database()

def print_record_html(data, title):
    """Generate HTML for printing records"""
    html = f"""
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #1f4e79; text-align: center; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .record {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; }}
            .field {{ margin: 5px 0; }}
            .label {{ font-weight: bold; }}
            .timestamp {{ text-align: right; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏥 EndoTrace</h1>
            <h2>{title}</h2>
            <p>Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</p>
        </div>
        {data}
    </body>
    </html>
    """
    return html

def main():
    # Check authentication
    if not check_authentication():
        login_form()
        return
    
    # Sidebar navigation
    st.sidebar.image('attached_assets/Capture 22_1750416327416.JPG', use_container_width=True)
    st.sidebar.title(f"👋 Bonjour {get_username()}")
    st.sidebar.write(f"**Rôle:** {get_user_role()}")
    
    # Navigation menu based on role
    user_role = get_user_role()
    
    if user_role == 'admin':
        menu_options = ["Dashboard", "Gestion des Utilisateurs", "Archives"]
    elif user_role == 'biomedical':
        menu_options = ["Dashboard", "Gestion Inventaire", "Archives"]
    elif user_role == 'sterilisation':
        menu_options = ["Dashboard", "Rapports de Stérilisation", "Archives"]
    else:
        menu_options = ["Dashboard"]
    
    selected_page = st.sidebar.selectbox("Navigation", menu_options)
    
    if st.sidebar.button("🚪 Déconnexion"):
        logout()
    
    # Main content based on selected page
    if selected_page == "Dashboard":
        show_dashboard()
    elif selected_page == "Gestion des Utilisateurs":
        show_admin_interface()
    elif selected_page == "Gestion Inventaire":
        show_biomedical_interface()
    elif selected_page == "Rapports de Stérilisation":
        show_sterilization_interface()
    elif selected_page == "Archives":
        show_archives_interface()

def show_dashboard():
    """Display dashboard with analytics"""
    st.title("📊 Tableau de Bord")
    
    # --- Section for new breakdown alerts ---
    with st.container(border=True):
        st.subheader("🚨 Alertes de Pannes Récentes")
        recent_breakdowns = db.get_recent_breakdowns(days=7)

        if not recent_breakdowns.empty:
            for idx, report in recent_breakdowns.iterrows():
                st.warning(
                    f"**Panne signalée le {report['date_desinfection']} par {report['nom_operateur']}:** "
                    f"L'endoscope **{report['endoscope']} (N/S: {report['numero_serie']})** a été déclaré 'en panne'. "
                    f"Raison: {report.get('nature_panne', 'Non spécifiée')}"
                )
        else:
            st.info("✔️ Aucune panne récente signalée au cours des 7 derniers jours.")

    st.divider()

    # Get statistics
    stats = db.get_dashboard_stats()
    malfunction_percentage, broken_count, total_count = db.get_malfunction_percentage()
    
    # Check for email alert
    if malfunction_percentage > 50:
        st.error(f"🚨 **ALERTE CRITIQUE**: {malfunction_percentage:.1f}% des endoscopes sont en panne!")
        
        # Try to send email alert
        email_manager = EmailAlertManager()
        if st.button("📧 Envoyer alerte par email"):
            if email_manager.send_malfunction_alert(malfunction_percentage, broken_count, total_count):
                st.success("Email d'alerte envoyé avec succès!")
            else:
                st.warning("Erreur lors de l'envoi de l'email. Vérifiez la configuration SMTP.")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Endoscopes", total_count)
    
    with col2:
        st.metric("Fonctionnels", total_count - broken_count)
    
    with col3:
        st.metric("En Panne", broken_count)
    
    with col4:
        st.metric("Taux de Panne", f"{malfunction_percentage:.1f}%")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("État des Endoscopes")
        if not stats['status_stats'].empty:
            fig_status = px.pie(
                stats['status_stats'], 
                values='count', 
                names='etat',
                title="Répartition par État",
                color_discrete_map={'fonctionnel': '#4CAF50', 'en panne': '#F44336'}
            )
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("Aucune donnée disponible")
    
    with col2:
        st.subheader("Localisation des Endoscopes")
        if not stats['location_stats'].empty:
            fig_location = px.bar(
                stats['location_stats'], 
                x='localisation', 
                y='count',
                title="Répartition par Localisation",
                color='count',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_location, use_container_width=True)
        else:
            st.info("Aucune donnée disponible")

@require_role(['admin'])
def show_admin_interface():
    """Admin interface for user management"""
    st.title("👤 Administration des Utilisateurs")
    
    tab1, tab2 = st.tabs(["Gestion des Utilisateurs", "Ajouter un Utilisateur"])
    
    with tab1:
        st.subheader("Liste des Utilisateurs")
        users_df = db.get_all_users()
        
        if not users_df.empty:
            # Display users with edit/delete options
            for idx, user in users_df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                
                with col1:
                    st.write(f"**{user['username']}**")
                
                with col2:
                    current_role = str(user['role'])
                    new_role = st.selectbox(
                        "Rôle", 
                        ['admin', 'biomedical', 'sterilisation'],
                        index=['admin', 'biomedical', 'sterilisation'].index(current_role),
                        key=f"role_{user['id']}"
                    )
                
                with col3:
                    new_password = st.text_input("Nouveau mot de passe", type="password", key=f"pwd_{user['id']}")
                
                with col4:
                    if st.button("💾 Modifier", key=f"edit_{user['id']}"):
                        try:
                            updated = False
                            if new_role != current_role:
                                if db.update_user_role(user['id'], new_role):
                                    updated = True
                                    st.success(f"Rôle modifié pour {user['username']}")
                                else:
                                    st.error(f"Erreur lors de la modification du rôle pour {user['username']}")
                            
                            if new_password:
                                if db.update_user_password(user['id'], new_password):
                                    updated = True
                                    st.success(f"Mot de passe modifié pour {user['username']}")
                                else:
                                    st.error(f"Erreur lors de la modification du mot de passe pour {user['username']}")
                            
                            if updated:
                                st.rerun()
                            else:
                                st.warning("Aucune modification effectuée")
                        except Exception as e:
                            st.error(f"Erreur lors de la modification: {str(e)}")
                
                with col5:
                    if str(user['username']) != 'admin':  # Prevent admin deletion
                        if st.button("❌ Supprimer", key=f"delete_{user['id']}"):
                            try:
                                if db.delete_user(user['id']):
                                    st.success(f"Utilisateur {user['username']} supprimé avec succès!")
                                    st.rerun()
                                else:
                                    st.error(f"Erreur lors de la suppression de {user['username']}")
                            except Exception as e:
                                st.error(f"Erreur lors de la suppression: {str(e)}")
                    else:
                        st.info("Admin protégé")
                
                st.divider()
        else:
            st.info("Aucun utilisateur trouvé")
    
    with tab2:
        st.subheader("Ajouter un Nouvel Utilisateur")
        
        with st.form("add_user_form", clear_on_submit=True):
            new_username = st.text_input("Nom d'utilisateur")
            new_password = st.text_input("Mot de passe", type="password")
            new_role = st.selectbox("Rôle", ['admin', 'biomedical', 'sterilisation'])
            
            if st.form_submit_button("➕ Ajouter Utilisateur"):
                if new_username and new_password:
                    if db.add_user(new_username, new_password, new_role):
                        st.success("Utilisateur ajouté avec succès!")
                        st.rerun()
                    else:
                        st.error("Erreur: Nom d'utilisateur déjà existant")
                else:
                    st.error("Veuillez remplir tous les champs")

@require_role(['biomedical'])
def show_biomedical_interface():
    """Biomedical engineer interface for inventory management"""
    st.title("🔬 Gestion de l'Inventaire des Endoscopes")
    
    tab1, tab2 = st.tabs(["Inventaire", "Ajouter Endoscope"])
    
    with tab1:
        st.subheader("Liste des Endoscopes")
        endoscopes_df = db.get_all_endoscopes()
        
        if not endoscopes_df.empty:
            for idx, endoscope in endoscopes_df.iterrows():
                with st.expander(f"📱 {endoscope['designation']} - {endoscope['numero_serie']}"):
                    # --- Affichage des détails ---
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Marque:** {endoscope['marque']}")
                        st.write(f"**Modèle:** {endoscope['modele']}")
                        st.write(f"**État:** {endoscope['etat']}")
                        st.write(f"**Localisation:** {endoscope['localisation']}")
                        obs_value = endoscope.get('observation')
                        if obs_value and pd.notna(obs_value) and str(obs_value).strip():
                            st.write(f"**Observation:** {obs_value}")
                        st.write(f"**Créé par:** {endoscope.get('created_by', 'N/A')} le {endoscope['created_at']}")

                    # --- Boutons d'action ---
                    with col2:
                        edit_key = f"edit_mode_{endoscope['id']}"
                        if st.button("✏️ Modifier", key=f"edit_btn_{endoscope['id']}"):
                            st.session_state[edit_key] = True
                            st.rerun()

                        if st.button("🗑️ Supprimer", key=f"delete_btn_{endoscope['id']}", type="secondary"):
                            if db.delete_endoscope(endoscope['id']):
                                st.success("✅ Endoscope supprimé avec succès!")
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de la suppression.")

                    # --- Formulaire de modification (si activé) ---
                    if st.session_state.get(edit_key, False):
                        st.info(f"Modification de : {endoscope['designation']}")
                        with st.form(f"update_form_{endoscope['id']}"):
                            new_designation = st.text_input("Désignation", value=endoscope['designation'])
                            new_marque = st.text_input("Marque", value=endoscope['marque'])
                            new_modele = st.text_input("Modèle", value=endoscope['modele'])
                            new_numero_serie = st.text_input("Numéro de série", value=endoscope['numero_serie'])
                            new_etat = st.selectbox("État", ['fonctionnel', 'en panne'], 
                                                  index=0 if endoscope['etat'] == 'fonctionnel' else 1)
                            new_observation = st.text_area("Observation", value=str(endoscope.get('observation', '')))
                            
                            location_options = ['stock', 'en utilisation', 'externe', 'zone de stérilisation']
                            current_location_index = location_options.index(endoscope['localisation']) if endoscope['localisation'] in location_options else 0
                            new_localisation = st.selectbox("Localisation", options=location_options, index=current_location_index)
                            
                            col_f1, col_f2 = st.columns(2)
                            with col_f1:
                                if st.form_submit_button("💾 Mettre à jour"):
                                    update_data = {
                                        'designation': new_designation, 'marque': new_marque, 'modele': new_modele,
                                        'numero_serie': new_numero_serie, 'etat': new_etat,
                                        'observation': new_observation, 'localisation': new_localisation
                                    }
                                    if db.update_endoscope(endoscope['id'], **update_data):
                                        st.success("✅ Endoscope mis à jour!")
                                        st.session_state.pop(edit_key, None)
                                        st.rerun()
                                    else:
                                        st.error("❌ Erreur lors de la mise à jour.")
                            with col_f2:
                                if st.form_submit_button("❌ Annuler"):
                                    st.session_state.pop(edit_key, None)
                                    st.rerun()
        else:
            st.info("Aucun endoscope dans l'inventaire.")

    with tab2:
        st.subheader("Ajouter un Nouvel Endoscope")
        with st.form("add_endoscope_form", clear_on_submit=True):
            designation = st.text_input("Désignation*")
            marque = st.text_input("Marque*")
            modele = st.text_input("Modèle*")
            numero_serie = st.text_input("Numéro de série*")
            etat = st.selectbox("État*", ['fonctionnel', 'en panne'])
            observation = st.text_area("Observation")
            localisation = st.selectbox("Localisation*", ['stock', 'en utilisation', 'externe', 'zone de stérilisation'])
            
            submitted = st.form_submit_button("➕ Ajouter Endoscope")
            if submitted:
                if all([designation, marque, modele, numero_serie, localisation]):
                    if db.add_endoscope(designation, marque, modele, numero_serie, etat, observation, localisation, get_username()):
                        st.success("✅ Endoscope ajouté avec succès!")
                    else:
                        st.error("❌ Erreur: Numéro de série déjà existant.")
                else:
                    st.error("❌ Veuillez remplir tous les champs obligatoires (*)")

@require_role(['sterilisation', 'biomedical'])
def show_sterilization_interface():
    """Sterilization agent interface for sterilization reports"""
    st.title("🧴 Rapports de Stérilisation et Désinfection")
    tab1, tab2 = st.tabs(["Nouveau Rapport Stérilisation", "Gérer Rapports"])
    
    with tab1:
        st.subheader("Enregistrer un Rapport de Stérilisation")
        
        endoscopes_df = db.get_all_endoscopes()
        
        if endoscopes_df.empty:
            st.warning("⚠️ Aucun endoscope n'est disponible dans l'inventaire. Veuillez en ajouter un avant de créer un rapport.")
            return

        with st.form("sterilisation_report_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📋 Informations Générales**")
                
                # Operator name is auto-filled and disabled
                st.text_input("Nom de l'opérateur*", value=get_username(), disabled=True)
                
                # Dropdown for endoscope selection
                endoscope_options = {row['id']: f"{row['designation']} - {row['numero_serie']}" for index, row in endoscopes_df.iterrows()}
                selected_id = st.selectbox(
                    "Endoscope*",
                    options=list(endoscope_options.keys()),
                    format_func=lambda x: endoscope_options.get(x, "Inconnu")
                )
                
                selected_endoscope_details = None
                if selected_id:
                    selected_endoscope_details = endoscopes_df[endoscopes_df['id'] == selected_id].iloc[0]
                    st.text_input("Numéro de série*", value=selected_endoscope_details['numero_serie'], disabled=True)

                medecin_responsable = st.text_input("Médecin responsable*")
                
                st.write("**💧 Désinfection**")
                date_desinfection = st.date_input("Date de désinfection*")
                type_desinfection = st.selectbox("Type de désinfection*", ['manuel', 'automatique'])
                cycle = st.selectbox("Cycle*", ['complet', 'incomplet'])
                test_etancheite = st.selectbox("Test d'étanchéité*", ['réussi', 'échoué'])
            
            with col2:
                st.write("**⏰ Horaires**")
                heure_debut = st.text_input("Heure de début* (HH:MM)", placeholder="14:30")
                heure_fin = st.text_input("Heure de fin* (HH:MM)", placeholder="15:45")
                
                st.write("**🏥 Informations Médicales**")
                salle = st.text_input("Salle*")
                type_acte = st.text_input("Type d'acte*")
                
                st.write("**⚙️ État**")
                etat_endoscope = st.selectbox("État de l'endoscope*", ['fonctionnel', 'en panne'])
                nature_panne = None
                if etat_endoscope == 'en panne':
                    nature_panne = st.text_area("Nature de la panne*")
            
            if st.form_submit_button("📝 Enregistrer Rapport de Stérilisation"):
                # Validation
                if not selected_id or not medecin_responsable or not salle or not type_acte or not heure_debut or not heure_fin:
                    st.error("Veuillez remplir tous les champs obligatoires (*)")
                elif etat_endoscope == 'en panne' and not nature_panne:
                    st.error("Veuillez spécifier la nature de la panne")
                elif ":" not in heure_debut or ":" not in heure_fin:
                    st.error("Format d'heure invalide. Utilisez HH:MM (ex: 14:30)")
                else:
                    nom_operateur = get_username()
                    # Re-fetch details inside the submit block to be safe
                    selected_endoscope_details = endoscopes_df[endoscopes_df['id'] == selected_id].iloc[0]
                    endoscope_name = selected_endoscope_details['designation']
                    numero_serie_val = selected_endoscope_details['numero_serie']
                    
                    if db.add_sterilisation_report(
                        nom_operateur, endoscope_name, numero_serie_val, medecin_responsable,
                        date_desinfection, type_desinfection, cycle, test_etancheite,
                        heure_debut, heure_fin, "N/A", salle, type_acte,
                        etat_endoscope, nature_panne, nom_operateur
                    ):
                        st.success("Rapport de stérilisation enregistré avec succès!")
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'enregistrement - Vérifiez le format des données")
    
    with tab2:
        st.subheader("Gérer les Rapports de Stérilisation")
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_by_user = st.checkbox("Mes rapports uniquement", value=(get_user_role() == 'sterilisation'))
        with col2:
            filter_date = st.date_input("Filtrer par date", value=None)
        with col3:
            filter_etat = st.selectbox("Filtrer par état", ['Tous', 'fonctionnel', 'en panne'])
        if filter_by_user or get_user_role() == 'sterilisation':
            steril_reports = db.get_user_sterilisation_reports(get_username())
        else:
            steril_reports = db.get_all_sterilisation_reports()
        if not steril_reports.empty:
            if filter_date:
                steril_reports = steril_reports[steril_reports['date_desinfection'] == str(filter_date)]
            if filter_etat != 'Tous':
                steril_reports = steril_reports[steril_reports['etat_endoscope'] == filter_etat]
            if not steril_reports.empty:
                st.write(f"**Rapports trouvés: {len(steril_reports)}**")
                for idx, report in steril_reports.iterrows():
                    with st.expander(f"📋 Rapport #{report['id']} - {report['endoscope']} ({report['date_desinfection']})"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Opérateur:** {report['nom_operateur']}")
                            st.write(f"**Médecin:** {report['medecin_responsable']}")
                            st.write(f"**Désinfection:** {report['type_desinfection']} - {report['cycle']}")
                            st.write(f"**Test étanchéité:** {report['test_etancheite']}")
                            st.write(f"**Horaires:** {report['heure_debut']} - {report['heure_fin']}")
                            st.write(f"**Salle:** {report['salle']}")
                            st.write(f"**État:** {report['etat_endoscope']}")
                            try:
                                nature_panne = str(report['nature_panne'])
                                if nature_panne not in ['nan', 'None', '']:
                                    st.write(f"**Nature panne:** {nature_panne}")
                            except:
                                pass
                        with col2:
                            can_modify = db.can_user_modify_sterilisation_report(get_user_role(), report['id'], get_username())
                            if can_modify:
                                if st.button("✏️ Modifier", key=f"edit_steril_{report['id']}"):
                                    st.session_state[f"edit_steril_{report['id']}"] = True
                                    st.rerun()
                                if st.button("🗑️ Supprimer", key=f"del_steril_{report['id']}"):
                                    try:
                                        if db.delete_sterilisation_report(report['id']):
                                            st.success("✅ Rapport supprimé avec succès!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Erreur lors de la suppression du rapport")
                                    except Exception as e:
                                        st.error(f"❌ Erreur lors de la suppression: {str(e)}")
                            else:
                                st.info("Lecture seule")
                        edit_key = f"edit_steril_{report['id']}"
                        if st.session_state.get(edit_key, False):
                            st.info("Modification du rapport en cours...")
                            with st.form(f"edit_sterilisation_report_form_{report['id']}"):
                                new_nom_operateur = st.text_input("Nom de l'opérateur*", value=report['nom_operateur'])
                                new_endoscope = st.text_input("Endoscope*", value=report['endoscope'])
                                new_numero_serie = st.text_input("Numéro de série*", value=report['numero_serie'])
                                new_medecin_responsable = st.text_input("Médecin responsable*", value=report['medecin_responsable'])
                                new_date_desinfection = st.date_input("Date de désinfection*", value=pd.to_datetime(report['date_desinfection']).date())
                                new_type_desinfection = st.selectbox("Type de désinfection*", ['manuel', 'automatique'], index=0 if report['type_desinfection']=='manuel' else 1)
                                new_cycle = st.selectbox("Cycle*", ['complet', 'incomplet'], index=0 if report['cycle']=='complet' else 1)
                                new_test_etancheite = st.selectbox("Test d'étanchéité*", ['réussi', 'échoué'], index=0 if report['test_etancheite']=='réussi' else 1)
                                new_heure_debut = st.text_input("Heure de début* (HH:MM)", value=report['heure_debut'])
                                new_heure_fin = st.text_input("Heure de fin* (HH:MM)", value=report['heure_fin'])
                                new_salle = st.text_input("Salle*", value=report['salle'])
                                new_type_acte = st.text_input("Type d'acte*", value=report['type_acte'])
                                new_etat_endoscope = st.selectbox("État de l'endoscope*", ['fonctionnel', 'en panne'], index=0 if report['etat_endoscope']=='fonctionnel' else 1)
                                new_nature_panne = st.text_area("Nature de la panne*", value=report['nature_panne'] if report['etat_endoscope']=='en panne' else '') if new_etat_endoscope=='en panne' else None
                                if st.form_submit_button("💾 Enregistrer les modifications"):
                                    try:
                                        # Validate required fields
                                        required_fields = [new_nom_operateur, new_endoscope, new_numero_serie, 
                                                         new_medecin_responsable, new_salle, new_type_acte, 
                                                         new_heure_debut, new_heure_fin]
                                        
                                        if not all(required_fields):
                                            st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
                                        elif new_etat_endoscope == 'en panne' and not new_nature_panne:
                                            st.error("❌ Veuillez spécifier la nature de la panne")
                                        elif ":" not in new_heure_debut or ":" not in new_heure_fin:
                                            st.error("❌ Format d'heure invalide. Utilisez HH:MM (ex: 14:30)")
                                        else:
                                            update_fields = {
                                                'nom_operateur': new_nom_operateur,
                                                'endoscope': new_endoscope,
                                                'numero_serie': new_numero_serie,
                                                'medecin_responsable': new_medecin_responsable,
                                                'date_desinfection': str(new_date_desinfection),
                                                'type_desinfection': new_type_desinfection,
                                                'cycle': new_cycle,
                                                'test_etancheite': new_test_etancheite,
                                                'heure_debut': new_heure_debut,
                                                'heure_fin': new_heure_fin,
                                                'salle': new_salle,
                                                'type_acte': new_type_acte,
                                                'etat_endoscope': new_etat_endoscope,
                                                'nature_panne': new_nature_panne,
                                                'procedure_medicale': report.get('procedure_medicale', 'N/A')
                                            }
                                            
                                            if db.update_sterilisation_report(report['id'], **update_fields):
                                                st.success("✅ Rapport modifié avec succès!")
                                                st.session_state.pop(edit_key, None)
                                                st.rerun()
                                            else:
                                                st.error("❌ Erreur lors de la modification du rapport.")
                                    except Exception as e:
                                        st.error(f"❌ Erreur lors de la modification: {str(e)}")
                            if st.button("❌ Annuler la modification", key=f"cancel_edit_{report['id']}"):
                                st.session_state.pop(edit_key, None)
                                st.rerun()
            else:
                st.info("Aucun rapport correspondant aux filtres")
        else:
            st.info("Aucun rapport de stérilisation disponible")

def show_archives_interface():
    """Archives interface for all users with filtering and sorting"""
    st.title("🗃️ Archives")

    user_role = get_user_role()
    
    tab_titles = ["Rapports de Stérilisation"]
    if user_role in ['biomedical', 'admin']:
        tab_titles.append("Historique Inventaire")
    
    tabs = st.tabs(tab_titles)
    
    # --- Tab 1: Sterilization Reports ---
    with tabs[0]:
        st.subheader("Historique des Rapports de Stérilisation")
        steril_reports = db.get_all_sterilisation_reports()
        
        if not steril_reports.empty:
            filtered_steril = steril_reports.copy()
            with st.expander("🔍 Filtres et Tri pour les Rapports"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    operators = st.multiselect("Opérateur", options=steril_reports['nom_operateur'].unique(), key="op_filter")
                    medecins = st.multiselect("Médecin", options=steril_reports['medecin_responsable'].unique(), key="med_filter")
                with col2:
                    states = st.multiselect("État de l'endoscope", options=steril_reports['etat_endoscope'].unique(), key="state_filter")
                    start_date = st.date_input("Du", None, key="steril_start")
                    end_date = st.date_input("Au", None, key="steril_end")
                with col3:
                    sort_by_steril = st.selectbox("Trier par", options=list(steril_reports.columns), index=5, key="sort_steril_col")
                    sort_order_steril = st.radio("Ordre", ["Descendant", "Ascendant"], key="sort_steril_order")

            if operators: filtered_steril = filtered_steril[filtered_steril['nom_operateur'].isin(operators)]
            if medecins: filtered_steril = filtered_steril[filtered_steril['medecin_responsable'].isin(medecins)]
            if states: filtered_steril = filtered_steril[filtered_steril['etat_endoscope'].isin(states)]
            if start_date: filtered_steril = filtered_steril[pd.to_datetime(filtered_steril['date_desinfection']).dt.date >= start_date]
            if end_date: filtered_steril = filtered_steril[pd.to_datetime(filtered_steril['date_desinfection']).dt.date <= end_date]
            if sort_by_steril: filtered_steril = filtered_steril.sort_values(by=sort_by_steril, ascending=(sort_order_steril == 'Ascendant'))
            
            st.dataframe(filtered_steril.drop(columns=['procedure_medicale'], errors='ignore'), use_container_width=True)
            
            # Prepare data for download
            html_content_steril = filtered_steril.to_html(index=False, justify='center')
            html_file_steril = print_record_html(html_content_steril, "Rapports de Stérilisation")
            
            st.download_button(
                label="📥 Télécharger les rapports",
                data=html_file_steril,
                file_name="rapports_sterilisation.html",
                mime="text/html",
                key="download_steril_report"
            )
        else:
            st.info("Aucun rapport de stérilisation disponible.")

    # --- Tab 2: Inventory History ---
    if user_role in ['biomedical', 'admin']:
        with tabs[1]:
            st.subheader("Historique de l'Inventaire des Endoscopes")
            inventory_df = db.get_all_endoscopes()
            
            if not inventory_df.empty:
                display_inventory = inventory_df.copy()
                with st.expander("🔍 Filtres et Tri pour l'Inventaire"):
                    col1, col2 = st.columns(2)
                    with col1:
                        inv_states = st.multiselect("État de l'endoscope", options=inventory_df['etat'].unique(), key="inv_state")
                        inv_locs = st.multiselect("Localisation", options=inventory_df['localisation'].unique(), key="inv_loc")
                    with col2:
                        sort_by_inv = st.selectbox("Trier par", options=list(inventory_df.columns), key="inv_sort")
                        sort_order_inv = st.radio("Ordre", ["Ascendant", "Descendant"], key="inv_order")
                
                if inv_states: display_inventory = display_inventory[display_inventory['etat'].isin(inv_states)]
                if inv_locs: display_inventory = display_inventory[display_inventory['localisation'].isin(inv_locs)]
                if sort_by_inv: display_inventory = display_inventory.sort_values(by=sort_by_inv, ascending=(sort_order_inv == 'Ascendant'))
                
                st.dataframe(display_inventory, use_container_width=True)
                
                # Prepare data for download
                html_content_inv = display_inventory.to_html(index=False, justify='center')
                html_file_inv = print_record_html(html_content_inv, "Historique de l'Inventaire")

                st.download_button(
                    label="📥 Télécharger l'inventaire",
                    data=html_file_inv,
                    file_name="historique_inventaire.html",
                    mime="text/html",
                    key="download_inv_report"
                )
            else:
                st.info("Aucun historique d'inventaire disponible.")

if __name__ == "__main__":
    main()
