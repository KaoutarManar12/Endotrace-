import streamlit as st
from database import DatabaseManager

def check_authentication():
    """Check if user is authenticated"""
    return 'authenticated' in st.session_state and st.session_state.authenticated

def get_user_role():
    """Get current user role"""
    return st.session_state.get('user_role', None)

def get_username():
    """Get current username"""
    return st.session_state.get('username', None)

def login_form():
    """Display login form"""

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image('attached_assets/Capture 22_1750416327416.JPG', use_container_width=True)
        except Exception as e:
            st.error(f"Impossible de charger le logo : {e}")

    st.title("Bienvenue sur EndoTrace")
    st.markdown("<h3 style='text-align: center;'>Veuillez vous connecter pour continuer.</h3>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter", use_container_width=True)
        
        if submit:
            if username and password:
                db = DatabaseManager()
                role = db.authenticate_user(username, password)
                
                if role:
                    st.session_state.authenticated = True
                    st.session_state.user_role = role
                    st.session_state.username = username
                    st.success(f"Connexion réussie! Bienvenue {username}.")
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur ou mot de passe incorrect")
            else:
                st.error("Veuillez remplir tous les champs")

def logout():
    """Logout user"""
    for key in ['authenticated', 'user_role', 'username']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def require_role(allowed_roles):
    """Decorator to require specific roles"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not check_authentication():
                st.error("Vous devez être connecté pour accéder à cette page")
                return
            
            user_role = get_user_role()
            if user_role not in allowed_roles:
                st.error(f"Accès refusé. Rôles autorisés: {', '.join(allowed_roles)}")
                return
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
