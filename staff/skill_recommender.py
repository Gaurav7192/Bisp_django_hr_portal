# staff/skill_recommender.py

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import datetime
import json
import os
import numpy as np
import pickle

# For data preprocessing
from textblob import TextBlob
from spellchecker import SpellChecker
from sentence_transformers import SentenceTransformer

# Import ALL necessary Django models based on your final models.py structure
from staff.models import (
    UserProfile,
    emp_registers,
    DepartmentMaster,
    RoleMaster,  # Used by emp_registers.position
    DesignationMaster,  # Used by emp_registers.designation AND UserProfile.role
    JobStatusMaster  # Used by emp_registers.job_status
)

# --- Configuration for a dynamic system ---
# Paths are set relative to the Django project root, which is where manage.py is.
# This assumes skill_recommender.py is in a Django app directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG = {
    "data_path": os.path.join(BASE_DIR, "mixed_employee_data (1).csv"),  # Only if you still use CSV for initial data
    "output_excel": os.path.join(BASE_DIR, "skill_recommendations_dynamic_professional_skills.xlsx"),
    "similarity_matrix_path": os.path.join(BASE_DIR, "similarity_matrix_professional_skills.npy"),
    "sbert_model_name": "all-MiniLM-L6-v2",  # The Sentence Transformer model
    "trending_skills_source": os.path.join(BASE_DIR, "simulated_trending_skills_professional_types.json"),
    "recommendation_params": {
        "top_n_similar_employees": 7,
        "similarity_threshold": 0.45,
        "ngram_range_tfidf": (1, 3),  # Only relevant if TF-IDF were used, kept for completeness
        "weight_projects": 2,
        "weight_certifications": 1.5,
        "weight_roles": 1.0,  # This now refers to 'role' from UserProfile.role (DesignationMaster)
        "weight_department": 0.5,
        "weight_position": 0.7,  # This refers to 'position' from emp_registers (RoleMaster)
        "trend_boost_factor": 0.08,
        "max_pure_trending_suggestions": 1,
        "min_peer_suggestions_before_pure_trends": 3,
        "min_recommendation_score": 0.08,
        "max_total_suggestions_per_person": 5,
        "trending_skill_base_score": 0.05,
        "trending_skill_relevance_map": {
            "generative ai": 1.5, "prompt engineering": 1.4, "cloud security": 1.3,
            "communication": 0.8, "time management": 0.7, "negotiation skills": 0.9, "power bi": 1.1,
            "python": 1.2, "java": 1.2, "react": 1.1, "node.js": 1.1, "sql": 1.0, "machine learning": 1.3
        },
        "adaptive_threshold_attempts": [0.45, 0.40, 0.35, 0.30, 0.25]
    },
    "scheduling_info": {
        "model_retrain_frequency_days": 7,
        "trend_data_fetch_frequency_hours": 24
    }
}

# Global Sentence Transformer model instance to load once
SBERT_MODEL = None


# --- Data Preprocessing ---
def preprocess_skills_text(text):
    if not isinstance(text, str):
        return ""

    text = text.replace(';', ',')
    skills = [s.strip() for s in text.split(',') if s.strip()]

    synonyms = {
        "ml": "machine learning", "ai": "artificial intelligence", "js": "javascript",
        "reactjs": "react", "nodejs": "node.js", "db": "database", "comm": "communication",
        "ex": "microsoft excel", "excel": "microsoft excel",
        "powerbi": "power bi", "tableau": "tableau software"
    }

    spell = SpellChecker()
    common_tech_terms = [
        "kubernetes", "django", "tensorflow", "spring boot", "rest api", "azure", "aws", "gcp",
        "agile", "devops", "html", "css", "sql", "php", "mysql", "flask", "angular", "typescript",
        "vue.js", "firebase", "pandas", "scikit-learn", "numpy", "java", "c++", "c#", "bootstrap",
        "kotlin", "swift", "r", "go", "ruby", "rust", "graphql", "docker", "terraform", "ansible",
        "jenkins", "gitlab ci", "jira", "confluence", "spring security", "microservices", "unit testing",
        "data analysis", "data science", "data modeling", "ui/ux", "frontend", "backend", "full-stack"
    ]
    spell.word_frequency.load_words(common_tech_terms)

    processed_skills = []
    for s in skills:
        s_lower = s.lower()
        s_mapped = synonyms.get(s_lower, s_lower)
        corrected_s = spell.correction(s_mapped)
        if corrected_s and corrected_s != s_mapped and s_mapped not in common_tech_terms:
            s_mapped = corrected_s
        s_final = ' '.join(s_mapped.split()).title()
        processed_skills.append(s_final)
    return ', '.join(processed_skills)


# --- External Data Sources and Persistence ---

def fetch_trending_skills_from_api(source_url):
    print(f"[{datetime.datetime.now()}] Fetching trending skills from {source_url}...")
    try:
        with open(source_url, 'r') as f:
            trending_data = json.load(f)
        raw_skills = trending_data.get("trending_skills", [])
        return set(map(str.strip, [skill.lower() for skill in raw_skills]))
    except FileNotFoundError:
        print(f"Warning: Simulated trend data file '{source_url}' not found. Using empty set.")
        return set()
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from '{source_url}'. Using empty set.")
        return set()


def load_employee_data_from_db():
    """
    Loads employee data from Django UserProfile models into a DataFrame.
    """
    print(f"[{datetime.datetime.now()}] Loading employee data from UserProfile models...")
    data = []
    # Use select_related for efficiency to fetch related emp_registers, department, role (DesignationMaster), and position (RoleMaster)
    for profile in UserProfile.objects.select_related(
            'emp_register__department',
            'emp_register__position',  # This is a FK to RoleMaster
            'emp_register__designation',
            # This is a FK to DesignationMaster (redundant with UserProfile.role, but included for completeness if needed)
            'role'  # This is a FK to DesignationMaster
    ).all():
        # --- ROBUST DATA EXTRACTION FOR JSON FIELDS ---
        # Skills
        skills_data = profile.get_skills()
        skills_extracted = []
        if skills_data:
            for item in skills_data:
                if isinstance(item, dict):
                    skills_extracted.append(item.get('name', ''))
                elif isinstance(item, str):
                    skills_extracted.append(item)
        skills_str = ', '.join(filter(None, skills_extracted))

        # Projects
        projects_data = profile.get_projects()
        projects_extracted = []
        if projects_data:
            for item in projects_data:
                if isinstance(item, dict):
                    projects_extracted.append(item.get('name', ''))  # Projects typically have a 'name' key
                elif isinstance(item, str):
                    projects_extracted.append(item)
        projects_str = ', '.join(filter(None, projects_extracted))

        # Certifications/Experiences
        certs_data = profile.get_experiences()
        certs_extracted = []
        if certs_data:
            for item in certs_data:
                if isinstance(item, dict):
                    # Experiences/Certifications typically have a 'title' key
                    certs_extracted.append(item.get('title', ''))
                elif isinstance(item, str):
                    certs_extracted.append(item)
        certifications_str = ', '.join(filter(None, certs_extracted))
        # --- END ROBUST DATA EXTRACTION ---

        # Access role name from UserProfile's role (DesignationMaster)
        # Access 'designation_name' attribute from the DesignationMaster object
        role_name_str = profile.role.designation_name if profile.role else ''

        # Access department name from emp_register
        department_name_str = profile.emp_register.department.name if profile.emp_register and profile.emp_register.department else ''

        # Access general position from emp_register (RoleMaster)
        # Access 'role' attribute from the RoleMaster object linked via emp_registers.position
        position_str = profile.emp_register.position.role if profile.emp_register and profile.emp_register.position else ''

        # Note: emp_registers.designation is also a FK to DesignationMaster.
        # If needed, you can include it here:
        # emp_designation_str = profile.emp_register.designation.designation_name if profile.emp_register and profile.emp_register.designation else ''
        # For recommendations, we primarily use UserProfile.role (DesignationMaster) as the main role.

        data.append({
            'ID': profile.id,  # Use Django model ID
            'Name': profile.name,
            'Skills': skills_str,
            'Projects': projects_str,
            'Certifications': certifications_str,
            'Role': role_name_str,  # Now uses UserProfile.role's 'designation_name' attribute (from DesignationMaster)
            'Department': department_name_str,
            'Position': position_str  # Now uses emp_registers.position's 'role' attribute (from RoleMaster)
        })
    if not data:
        print("No UserProfile data found in database. Returning empty DataFrame.")
        return pd.DataFrame()
    df = pd.DataFrame(data)

    # Apply preprocessing to skills after loading from DB
    df['Skills'] = df['Skills'].fillna('').apply(preprocess_skills_text)
    df['Projects'] = df['Projects'].fillna('')
    df['Certifications'] = df['Certifications'].fillna('')
    df['Role'] = df['Role'].fillna('')
    df['Department'] = df['Department'].fillna('')
    df['Position'] = df['Position'].fillna('')
    return df


def save_model_artifacts(similarity_matrix):
    """Saves similarity matrix."""
    try:
        np.save(CONFIG["similarity_matrix_path"], similarity_matrix)
        print(f"[{datetime.datetime.now()}] Similarity matrix saved to {CONFIG['similarity_matrix_path']}.")
    except Exception as e:
        print(f"Error saving model artifacts: {e}")


def load_model_artifacts():
    """Loads similarity matrix."""
    try:
        if not os.path.exists(CONFIG["similarity_matrix_path"]):
            print(
                f"[{datetime.datetime.now()}] No existing similarity matrix found at {CONFIG['similarity_matrix_path']}. Will train new.")
            return None

        similarity_matrix = np.load(CONFIG["similarity_matrix_path"])
        print(f"[{datetime.datetime.now()}] Similarity matrix loaded from {CONFIG['similarity_matrix_path']}.")
        return similarity_matrix
    except Exception as e:
        print(f"Error loading model artifacts: {e}. Will train new.")
        return None


def train_and_get_similarity(data_df, params):
    """
    Trains the Sentence Transformer model and calculates similarity matrix.
    """
    if data_df.empty:
        print(f"[{datetime.datetime.now()}] Cannot train model: Employee data is empty.")
        return None

    global SBERT_MODEL
    if SBERT_MODEL is None:
        print(f"[{datetime.datetime.now()}] Loading Sentence Transformer model '{CONFIG['sbert_model_name']}'...")
        SBERT_MODEL = SentenceTransformer(CONFIG['sbert_model_name'])
        print(f"[{datetime.datetime.now()}] Sentence Transformer model loaded.")

    data_df['profile'] = data_df['Skills']
    if params['weight_projects'] > 0:
        data_df['profile'] += data_df['Projects'].apply(lambda x: '. ' + x if x else '')
    if 'Certifications' in data_df.columns and params['weight_certifications'] > 0:
        data_df['profile'] += data_df['Certifications'].apply(lambda x: '. ' + x if x else '')
    if 'Role' in data_df.columns and params['weight_roles'] > 0:
        data_df['profile'] += data_df['Role'].apply(lambda x: '. ' + x if x else '')
    if 'Department' in data_df.columns and params['weight_department'] > 0:
        data_df['profile'] += data_df['Department'].apply(lambda x: '. ' + x if x else '')
    if 'Position' in data_df.columns and params['weight_position'] > 0:
        data_df['profile'] += data_df['Position'].apply(lambda x: '. ' + x if x else '')

    data_df['profile'] = data_df['profile'].str.replace(r'\s*\.\s*', '. ', regex=True).str.replace(r'\.{2,}', '.',
                                                                                                   regex=True).str.strip()
    data_df['profile'] = data_df['profile'].apply(lambda x: x[2:] if x.startswith('. ') else x)
    data_df['profile'] = data_df['profile'].apply(lambda x: "no information provided" if not x else x)

    print(f"[{datetime.datetime.now()}] Encoding profiles with Sentence Transformer...")
    embeddings = SBERT_MODEL.encode(data_df['profile'].tolist(), show_progress_bar=True, convert_to_numpy=True)

    print(f"[{datetime.datetime.now()}] Calculating cosine similarity from embeddings...")
    similarity = cosine_similarity(embeddings)
    print(
        f"[{datetime.datetime.now()}] Embeddings and similarity matrix calculated. Shape: {similarity.shape}")  # Added shape print
    return similarity


def generate_recommendations(data_df, similarity_matrix, trending_skills, params):
    """
    Generates skill recommendations for each employee, incorporating trends and adaptive thresholds.
    Returns a Series of lists of recommended skills.
    """
    if data_df.empty or similarity_matrix is None:
        print(f"[{datetime.datetime.now()}] Skipping recommendations: Data or model missing.")
        return pd.Series([[]] * len(data_df)), pd.Series(['Error'] * len(data_df))

    # Add a check here for consistency
    if len(data_df) != similarity_matrix.shape[0]:
        print(
            f"[{datetime.datetime.now()}] Mismatch: DataFrame size ({len(data_df)}) and similarity matrix size ({similarity_matrix.shape[0]}) are different. This might lead to errors if not handled by retraining earlier.")
        # For safety, you might consider raising an error or returning empty results here,
        # but the fix in run_recommendation_process aims to prevent this state.
        # For now, let's proceed and see if the fix in run_recommendation_process handles it.

    recommendations = []
    all_top_peer_ids = []

    def get_trend_relevance(skill_lower):
        return params.get('trending_skill_relevance_map', {}).get(skill_lower, 1.0)

    for idx, row in data_df.iterrows():
        user_skills_raw = set(map(str.strip, row['Skills'].split(',')))
        user_skills_lower = set(map(str.strip, [s.lower() for s in user_skills_raw]))

        suggested_skills_with_scores = defaultdict(float)
        top_similar_peers = []

        # Make sure that `idx` is a valid index for `similarity_matrix`
        # This check is crucial if the matrix size is indeed smaller than data_df length
        if idx >= similarity_matrix.shape[0]:
            print(
                f"[{datetime.datetime.now()}] Warning: Skipping recommendations for index {idx} as it's out of bounds for similarity matrix of shape {similarity_matrix.shape}.")
            recommendations.append([])
            all_top_peer_ids.append('N/A')
            continue  # Skip to the next employee

        for attempt_threshold in params['adaptive_threshold_attempts']:
            sim_scores = list(enumerate(similarity_matrix[idx]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

            potential_peers = [
                                  score for score in sim_scores
                                  if score[0] != idx and score[1] >= attempt_threshold
                              ][:params['top_n_similar_employees']]

            if potential_peers:
                top_similar_peers = potential_peers
                break

        if top_similar_peers:
            for i, score in top_similar_peers:
                peer_skills_raw = set(map(str.strip, data_df.iloc[i]['Skills'].split(',')))
                peer_skills_lower = set(map(str.strip, [s.lower() for s in peer_skills_raw]))
                new_skills_from_peer = peer_skills_lower - user_skills_lower

                for skill_lower in new_skills_from_peer:
                    original_casing_skill = next((s for s in peer_skills_raw if s.lower() == skill_lower),
                                                 skill_lower.title())
                    suggested_skills_with_scores[original_casing_skill] += score

        pure_trending_suggestions_added_count = 0
        sorted_trending_skills_for_user = sorted(
            list(trending_skills - user_skills_lower),
            key=get_trend_relevance,
            reverse=True
        )

        for trend_skill_lower in sorted_trending_skills_for_user:
            found_in_suggestions = False
            for s_key in list(suggested_skills_with_scores.keys()):
                if s_key.lower() == trend_skill_lower:
                    suggested_skills_with_scores[s_key] += params['trend_boost_factor'] * get_trend_relevance(
                        trend_skill_lower)
                    found_in_suggestions = True
                    break

            if (not found_in_suggestions and
                    pure_trending_suggestions_added_count < params['max_pure_trending_suggestions'] and
                    len(suggested_skills_with_scores) < params['min_peer_suggestions_before_pure_trends']):
                suggested_skills_with_scores[trend_skill_lower.title()] += params[
                                                                               'trending_skill_base_score'] * get_trend_relevance(
                    trend_skill_lower)
                pure_trending_suggestions_added_count += 1

        final_suggestions_with_scores = sorted(suggested_skills_with_scores.items(), key=lambda item: item[1],
                                               reverse=True)

        recommended_skills_list = []
        for skill, score in final_suggestions_with_scores:
            if score >= params['min_recommendation_score'] and skill.lower() not in user_skills_lower:
                recommended_skills_list.append(skill)
            if len(recommended_skills_list) >= params['max_total_suggestions_per_person']:
                break

        recommendations.append(recommended_skills_list)  # Store as list
        # Correctly use emp_register.email or emp_register.id as the identifier
        current_employee_peer_ids = [data_df.iloc[i]['ID'] for i, _ in top_similar_peers]
        all_top_peer_ids.append(', '.join(map(str, current_employee_peer_ids)) if current_employee_peer_ids else 'N/A')

    print(f"[{datetime.datetime.now()}] Recommendations generated for {len(data_df)} employees.")
    return pd.Series(recommendations), pd.Series(all_top_peer_ids)


# --- Feedback Loop ---
def record_feedback(user_profile_id, recommended_skill, feedback_type):
    """Records user feedback to a log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp},{user_profile_id},{recommended_skill},{feedback_type}\n"
    print(
        f"[{timestamp}] Feedback received: UserProfile ID {user_profile_id}, Skill '{recommended_skill}', Type: {feedback_type}")
    with open(os.path.join(BASE_DIR, "feedback_log.csv"), "a") as f:
        f.write(log_entry)


def run_recommendation_process():
    """
    Orchestrates the entire recommendation process.
    This function should be called by Django views or management commands.
    Returns a DataFrame with employee data and their recommendations.
    """
    # 1. Generate/Load simulated trending skills data
    trending_skills_for_demo = [
        "Python", "Excel", "React", "Node.js", "JavaScript", "Django", "REST API",
        "HTML", "CSS", "Java", "Spring Boot", "Flask", "SQL", "Angular", "TypeScript",
        "PHP", "MySQL", "Pandas", "Machine Learning", "Vue.js", "Firebase",
        "Generative AI", "Prompt Engineering", "Cloud Security", "DevOps Automation",
        "Data Governance", "Machine Learning Operations (MLOps)", "Kubernetes", "AWS", "Azure",
        "Cybersecurity Analytics", "Tableau", "Power BI", "Data Analytics", "Bootstrap", "C++",
        "NLP", "Computer Vision", "Blockchain", "Go", "Kotlin", "Swift", "Rust", "Scrum",
        "Spring Security", "Microservices", "Unit Testing", "Data Analysis", "Data Modeling", "UI/UX",
        "Frontend", "Backend", "Full-Stack", "Docker", "Git", "Jira", "Confluence", "Agile Methodologies",

        "Communication", "Teamwork", "Problem Solving", "Adaptability",
        "Leadership", "Critical Thinking", "Emotional Intelligence", "Time Management",
        "Strategic Planning", "Negotiation Skills", "Active Listening", "Presentation Skills",
        "Conflict Resolution", "Coaching", "Mentoring", "Business Acumen", "Change Management",
        "Cross-functional Collaboration", "Decision Making", "Ethical Reasoning"
    ]
    with open(CONFIG["trending_skills_source"], "w") as f:
        json.dump({"trending_skills": trending_skills_for_demo}, f)
    print(f"Simulated '{CONFIG['trending_skills_source']}' created.")

    # 2. Load current employee data from Django models
    employee_data_df = load_employee_data_from_db()
    if employee_data_df.empty:
        print("No employee data loaded from DB. Cannot generate recommendations.")
        return pd.DataFrame()  # Return empty DataFrame if no data

    print(f"[{datetime.datetime.now()}] Loaded {len(employee_data_df)} employee profiles.")

    # 3. Load/Train Model Artifacts
    similarity_matrix = load_model_artifacts()

    # Crucial check: Retrain if matrix is None OR its size doesn't match current data
    if similarity_matrix is None or similarity_matrix.shape[0] != len(employee_data_df):
        if similarity_matrix is not None:  # If it exists but is mismatched
            print(
                f"[{datetime.datetime.now()}] Mismatch detected: Similarity matrix shape {similarity_matrix.shape} vs. {len(employee_data_df)} employee profiles. Retraining model.")
        else:  # If it didn't exist at all
            print(f"[{datetime.datetime.now()}] Similarity matrix not found or corrupted. Training new model.")

        similarity_matrix = train_and_get_similarity(employee_data_df.copy(), CONFIG["recommendation_params"])
        if similarity_matrix is None:
            print("Failed to train model.")
            return pd.DataFrame()
        save_model_artifacts(similarity_matrix)
    else:
        print(f"[{datetime.datetime.now()}] Re-using existing similarity matrix (shape {similarity_matrix.shape}).")

    # 4. Fetch Trending Skills
    trending_skills_set = fetch_trending_skills_from_api(CONFIG["trending_skills_source"])

    # 5. Generate Recommendations
    recommended_skills_series, top_peer_ids_series = generate_recommendations(
        employee_data_df.copy(),
        similarity_matrix,
        trending_skills_set,
        CONFIG["recommendation_params"]
    )
    employee_data_df['Recommended Skills'] = recommended_skills_series
    employee_data_df['Top Peer IDs'] = top_peer_ids_series

    # For export to Excel, convert list of skills to a comma-separated string
    employee_data_df['Recommended Skills String'] = employee_data_df['Recommended Skills'].apply(
        lambda x: ', '.join(x) if x else 'No Suggestion')
    employee_data_df.to_excel(CONFIG['output_excel'], index=False)
    print(f"\nRecommendations saved to {CONFIG['output_excel']}")

    return employee_data_df


# This __name__ == "__main__" block is for direct testing of this script.
# It simulates the Django environment for standalone execution.
if __name__ == "__main__":
    # Configure Django settings minimally for standalone script execution
    import django
    from django.conf import settings
    from django.utils import timezone  # Import timezone for mock data

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            INSTALLED_APPS=['staff', 'simple_history'],  # Make sure your app name and simple_history are here
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
            # You might need to add other settings like TEMPLATES, STATIC_URL etc.
            # for a full Django context if your models or other Django features rely on them.
        )
    django.setup()

    # --- Populating Mock Data for Standalone Test ---
    print("\n--- Populating Mock Data for Standalone Test ---")
    # Clean up existing data to ensure a fresh test run
    UserProfile.objects.all().delete()
    emp_registers.objects.all().delete()
    DepartmentMaster.objects.all().delete()
    RoleMaster.objects.all().delete()
    DesignationMaster.objects.all().delete()
    JobStatusMaster.objects.all().delete()

    # Create mock Departments
    dept_it, _ = DepartmentMaster.objects.get_or_create(name="IT")
    dept_hr, _ = DepartmentMaster.objects.get_or_create(name="HR")
    dept_accounts, _ = DepartmentMaster.objects.get_or_create(name="Accounts")
    dept_marketing, _ = DepartmentMaster.objects.get_or_create(name="Marketing")

    # Create mock Job Statuses
    status_active, _ = JobStatusMaster.objects.get_or_create(status_name="Active")
    status_on_leave, _ = JobStatusMaster.objects.get_or_create(status_name="On Leave")

    # Create mock general Roles (RoleMaster)
    role_employee, _ = RoleMaster.objects.get_or_create(role="Employee")
    role_manager, _ = RoleMaster.objects.get_or_create(role="Manager")
    role_team_lead, _ = RoleMaster.objects.get_or_create(role="Team Lead")

    # Create mock specific Designations (DesignationMaster)
    des_ds, _ = DesignationMaster.objects.get_or_create(designation_name="Data Scientist")
    des_be, _ = DesignationMaster.objects.get_or_create(designation_name="Backend Developer")
    des_fe, _ = DesignationMaster.objects.get_or_create(designation_name="Frontend Developer")
    des_bi, _ = DesignationMaster.objects.get_or_create(designation_name="Business Intelligence Analyst")
    des_devops, _ = DesignationMaster.objects.get_or_create(designation_name="DevOps Engineer")
    des_ai, _ = DesignationMaster.objects.get_or_create(designation_name="AI Engineer")
    des_sol_arch, _ = DesignationMaster.objects.get_or_create(designation_name="Solutions Architect")
    des_uiux, _ = DesignationMaster.objects.get_or_create(designation_name="UI/UX Designer")
    des_data_gov, _ = DesignationMaster.objects.get_or_create(designation_name="Data Governance Specialist")
    des_gen_ai_res, _ = DesignationMaster.objects.get_or_create(designation_name="Generative AI Researcher")
    des_hr_manager, _ = DesignationMaster.objects.get_or_create(designation_name="HR Manager")
    des_accountant, _ = DesignationMaster.objects.get_or_create(designation_name="Accountant")
    des_marketing_specialist, _ = DesignationMaster.objects.get_or_create(designation_name="Marketing Specialist")
    des_it_support, _ = DesignationMaster.objects.get_or_create(designation_name="IT Support Specialist")

    # Create mock emp_registers records
    emp_reg_1, _ = emp_registers.objects.get_or_create(email="alice@example.com",
                                                       defaults={
                                                           'name': 'Alice Johnson', 'password': 'hashed_password_1',
                                                           'department': dept_it, 'position': role_employee,
                                                           'designation': des_ds, 'job_status': status_active,
                                                           'joindate': datetime.date(2022, 1, 15), 'salary': 75000.00
                                                       })
    emp_reg_2, _ = emp_registers.objects.get_or_create(email="bob@example.com",
                                                       defaults={
                                                           'name': 'Bob Williams', 'password': 'hashed_password_2',
                                                           'department': dept_it, 'position': role_employee,
                                                           'designation': des_be, 'job_status': status_active,
                                                           'joindate': datetime.date(2021, 6, 1), 'salary': 80000.00
                                                       })
    # NOTE: Intentionally creating only 2 UserProfiles for this test to demonstrate the error if not fixed
    # Remove the comment below to create more users and test the fix thoroughly
    emp_reg_3, _ = emp_registers.objects.get_or_create(email="charlie@example.com",
                                                       defaults={
                                                           'name': 'Charlie Brown', 'password': 'hashed_password_3',
                                                           'department': dept_marketing, 'position': role_employee,
                                                           'designation': des_fe, 'job_status': status_active,
                                                           'joindate': datetime.date(2023, 3, 10), 'salary': 70000.00
                                                       })
    emp_reg_4, _ = emp_registers.objects.get_or_create(email="diana@example.com",
                                                       defaults={
                                                           'name': 'Diana Miller', 'password': 'hashed_password_4',
                                                           'department': dept_accounts, 'position': role_manager,
                                                           'designation': des_bi, 'job_status': status_active,
                                                           'joindate': datetime.date(2020, 9, 1), 'salary': 90000.00
                                                       })
    emp_reg_5, _ = emp_registers.objects.get_or_create(email="eve@example.com",
                                                       defaults={
                                                           'name': 'Eve Davis', 'password': 'hashed_password_5',
                                                           'department': dept_it, 'position': role_team_lead,
                                                           'designation': des_devops, 'job_status': status_active,
                                                           'joindate': datetime.date(2019, 11, 20), 'salary': 95000.00
                                                       })
    emp_reg_6, _ = emp_registers.objects.get_or_create(email="frank@example.com",
                                                       defaults={
                                                           'name': 'Frank White', 'password': 'hashed_password_6',
                                                           'department': dept_it, 'position': role_employee,
                                                           'designation': des_ai, 'job_status': status_active,
                                                           'joindate': datetime.date(2022, 5, 1), 'salary': 78000.00
                                                       })
    emp_reg_7, _ = emp_registers.objects.get_or_create(email="grace@example.com",
                                                       defaults={
                                                           'name': 'Grace Taylor', 'password': 'hashed_password_7',
                                                           'department': dept_it, 'position': role_manager,
                                                           'designation': des_sol_arch, 'job_status': status_active,
                                                           'joindate': datetime.date(2018, 2, 1), 'salary': 100000.00
                                                       })
    emp_reg_8, _ = emp_registers.objects.get_or_create(email="henry@example.com",
                                                       defaults={
                                                           'name': 'Henry Clark', 'password': 'hashed_password_8',
                                                           'department': dept_marketing, 'position': role_employee,
                                                           'designation': des_uiux, 'job_status': status_active,
                                                           'joindate': datetime.date(2023, 1, 1), 'salary': 72000.00
                                                       })
    emp_reg_9, _ = emp_registers.objects.get_or_create(email="ivy@example.com",
                                                       defaults={
                                                           'name': 'Ivy Hall', 'password': 'hashed_password_9',
                                                           'department': dept_accounts, 'position': role_employee,
                                                           'designation': des_accountant, 'job_status': status_active,
                                                           'joindate': datetime.date(2021, 9, 1), 'salary': 65000.00
                                                       })
    emp_reg_10, _ = emp_registers.objects.get_or_create(email="jack@example.com",
                                                        defaults={
                                                            'name': 'Jack Green', 'password': 'hashed_password_10',
                                                            'department': dept_hr, 'position': role_employee,
                                                            'designation': des_hr_manager, 'job_status': status_active,
                                                            'joindate': datetime.date(2022, 4, 1), 'salary': 85000.00
                                                        })

    # Populating UserProfile records with accurate FK assignments
    UserProfile.objects.get_or_create(emp_register=emp_reg_1,
                                      defaults={'name': "Alice Johnson", 'role': des_ds,
                                                # UserProfile.role is DesignationMaster
                                                'skills_json': json.dumps(
                                                    [{"name": "Python", "level": "Expert"},
                                                     {"name": "Machine Learning", "level": "Advanced"},
                                                     {"name": "Data Analysis", "level": "Expert"},
                                                     {"name": "SQL", "level": "Advanced"}]),
                                                'projects_json': json.dumps(
                                                    [{"name": "Customer Churn Prediction",
                                                      "description": "Used ML to predict customer churn"},
                                                     {"name": "Sales Forecasting",
                                                      "description": "Developed a time series model"}]),
                                                'experiences_json': json.dumps(
                                                    [{"title": "Deep Learning Certification", "year": 2023},
                                                     {"title": "Data Science Bootcamp", "year": 2022}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_2,
                                      defaults={'name': "Bob Williams", 'role': des_be,
                                                'skills_json': json.dumps(
                                                    [{"name": "Java", "level": "Expert"},
                                                     {"name": "Spring Boot", "level": "Advanced"},
                                                     {"name": "REST API", "level": "Advanced"}]),
                                                'projects_json': json.dumps(
                                                    [{"name": "E-commerce Backend",
                                                      "description": "Built a scalable e-commerce API"},
                                                     {"name": "Payment Gateway Integration",
                                                      "description": "Integrated third-party payment services"}]),
                                                'experiences_json': json.dumps(
                                                    [{"title": "Spring Professional Certification", "year": 2022}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_3,
                                      defaults={'name': "Charlie Brown", 'role': des_fe,
                                                'skills_json': json.dumps(
                                                    [{"name": "JavaScript", "level": "Expert"},
                                                     {"name": "React", "level": "Advanced"},
                                                     {"name": "Node.js", "level": "Intermediate"}]),
                                                'projects_json': json.dumps(
                                                    [{"name": "Interactive Dashboard",
                                                      "description": "Developed a real-time data dashboard"},
                                                     {"name": "Mobile Responsive Website",
                                                      "description": "Created a responsive web layout"}]),
                                                'experiences_json': json.dumps(
                                                    [{"title": "Frontend Development Course", "year": 2023}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_4,
                                      defaults={'name': "Diana Miller", 'role': des_bi,
                                                'skills_json': json.dumps(
                                                    [{"name": "SQL", "level": "Expert"},
                                                     {"name": "Power BI", "level": "Advanced"},
                                                     {"name": "Excel", "level": "Expert"}]),
                                                'projects_json': json.dumps(
                                                    [{"name": "Sales Performance Report",
                                                      "description": "Generated reports for sales trends"},
                                                     {"name": "Inventory Management Dashboard",
                                                      "description": "Designed a dashboard for inventory"}]),
                                                'experiences_json': json.dumps(
                                                    [{"title": "Microsoft Certified: Data Analyst Associate",
                                                      "year": 2021}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_5, defaults={'name': "Eve Davis", 'role': des_devops,
                                                                        'skills_json': json.dumps(
                                                                            [{"name": "AWS", "level": "Expert"},
                                                                             {"name": "DevOps", "level": "Advanced"},
                                                                             {"name": "Kubernetes",
                                                                              "level": "Intermediate"}]),
                                                                        'projects_json': json.dumps(
                                                                            [{"name": "CI/CD Pipeline Setup",
                                                                              "description": "Automated software delivery"},
                                                                             {"name": "Cloud Migration Project",
                                                                              "description": "Migrated on-premise infrastructure to cloud"}]),
                                                                        'experiences_json': json.dumps(
                                                                            [{
                                                                                 "title": "AWS Certified Solutions Architect",
                                                                                 "year": 2020}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_6, defaults={'name': "Frank White", 'role': des_ai,
                                                                        'skills_json': json.dumps(
                                                                            [{"name": "Python", "level": "Expert"},
                                                                             {"name": "Django", "level": "Advanced"},
                                                                             {"name": "Machine Learning",
                                                                              "level": "Expert"},
                                                                             {"name": "NLP", "level": "Advanced"}]),
                                                                        'projects_json': json.dumps(
                                                                            [{"name": "Recommendation Engine",
                                                                              "description": "Built a content recommendation system"},
                                                                             {"name": "Sentiment Analysis Tool",
                                                                              "description": "Developed an NLP-based sentiment analyzer"}]),
                                                                        'experiences_json': json.dumps(
                                                                            [{
                                                                                 "title": "Machine Learning Specialization",
                                                                                 "year": 2023}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_7,
                                      defaults={'name': "Grace Taylor", 'role': des_sol_arch,
                                                'skills_json': json.dumps(
                                                    [{"name": "Java", "level": "Expert"},
                                                     {"name": "Spring Boot", "level": "Expert"},
                                                     {"name": "Microservices", "level": "Advanced"}]),
                                                'projects_json': json.dumps([{
                                                                                 "name": "Enterprise Application Modernization",
                                                                                 "description": "Led modernization efforts for a legacy system"},
                                                                             {"name": "API Gateway Development",
                                                                              "description": "Designed and implemented API gateway"}]),
                                                'experiences_json': json.dumps(
                                                    [{"title": "Azure Developer Associate", "year": 2019}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_8, defaults={'name': "Henry Clark", 'role': des_uiux,
                                                                        'skills_json': json.dumps(
                                                                            [{"name": "JavaScript",
                                                                              "level": "Advanced"}, {"name": "Angular",
                                                                                                     "level": "Intermediate"},
                                                                             {"name": "TypeScript",
                                                                              "level": "Intermediate"}]),
                                                                        'projects_json': json.dumps(
                                                                            [{"name": "Single Page Application",
                                                                              "description": "Developed a SPA for a client"},
                                                                             {"name": "User Interface Redesign",
                                                                              "description": "Redesigned existing application UI"}]),
                                                                        'experiences_json': json.dumps(
                                                                            [{"title": "Angular Development Course",
                                                                              "year": 2023}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_9,
                                      defaults={'name': "Ivy Hall", 'role': des_accountant,
                                                'skills_json': json.dumps(
                                                    [{"name": "SQL", "level": "Advanced"},
                                                     {"name": "Tableau", "level": "Intermediate"},
                                                     {"name": "Data Warehousing", "level": "Basic"}]),
                                                'projects_json': json.dumps(
                                                    [{"name": "Data Mart Design",
                                                      "description": "Designed and implemented data marts"},
                                                     {"name": "ETL Process Optimization",
                                                      "description": "Optimized data extraction processes"}]),
                                                'experiences_json': json.dumps(
                                                    [{"title": "Tableau Desktop Specialist", "year": 2022}])})
    UserProfile.objects.get_or_create(emp_register=emp_reg_10,
                                      defaults={'name': "Jack Green", 'role': des_hr_manager,
                                                'skills_json': json.dumps(
                                                    [{"name": "HR Policies", "level": "Expert"},
                                                     {"name": "Recruitment", "level": "Advanced"},
                                                     {"name": "Employee Engagement", "level": "Advanced"}]),
                                                'projects_json': json.dumps(
                                                    [{"name": "HRIS Implementation",
                                                      "description": "Implemented a new HR Information System"},
                                                     {"name": "Onboarding Process Redesign",
                                                      "description": "Streamlined employee onboarding"}]),
                                                'experiences_json': json.dumps(
                                                    [{"title": "HR Management Certification", "year": 2021},
                                                     {"title": "Conflict Resolution Training", "year": 2020}])})

    print("Mock UserProfile data populated.")

    # Run the full recommendation process
    recommended_df = run_recommendation_process()
    print("\n--- Recommendations Generated (for standalone test) ---")
    print(
        recommended_df[['Name', 'Department', 'Role', 'Position', 'Skills', 'Recommended Skills', 'Top Peer IDs']].head(
            15))

    # Simulate a user click for the first recommended person
    if not recommended_df.empty and recommended_df.iloc[0]['Recommended Skills']:
        first_user_id = recommended_df.iloc[0]['ID']
        first_suggested_skill = recommended_df.iloc[0]['Recommended Skills'][0]
        # record_feedback(first_user_id, first_suggested_skill, "clicked")