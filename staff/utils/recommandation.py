# recommender_logic.py (or similar name in your Django app)

import os
import django
import sys
import datetime
import json
import numpy as np
import pandas as pd
import pickle

from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

# For data preprocessing
from textblob import TextBlob
from spellchecker import SpellChecker
from sentence_transformers import SentenceTransformer

# --- Django Setup ---
# This block ensures Django ORM is available when this script is run
# either standalone for testing or imported by a Django view.
# Replace 'your_django_project.settings' with your actual project's settings path.
# Replace 'yourappname.models' with the correct path to your app's models.
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_django_project.settings')
    django.setup()
    from yourappname.models import UserProfile, Project, Task, emp_registers, Member, StatusMaster
except Exception as e:
    print(
        f"Django setup or model import failed: {e}. This is expected if running outside a Django context without proper setup, but required for DB interaction.")
    # Set models to None to prevent errors if Django setup truly fails (e.g., during standalone testing without a full Django project)
    UserProfile, Project, Task, emp_registers, Member, StatusMaster = None, None, None, None, None, None

# --- Configuration for a dynamic system ---
CONFIG = {
    "sbert_model_name": "all-MiniLM-L6-v2",  # The Sentence Transformer model
    "trending_skills_source": "simulated_trending_skills_professional_types.json",  # For general skill recommendations
    "recommendation_params": {
        "top_n_similar_employees": 7,  # For peer-to-peer recommendations (less relevant for project matching directly)
        "similarity_threshold": 0.45,  # For peer-to-peer recommendations
        "weight_skills": 1.0,  # Weight for skills from UserProfile
        "weight_projects": 2,  # Weight for projects from UserProfile
        "weight_certifications": 1.5,  # Weight for certifications from UserProfile/Experience
        "weight_roles": 1.0,  # Weight for roles from EmpRegister/Experience
        "trend_boost_factor": 0.08,  # For general skill recommendations
        "max_pure_trending_suggestions": 1,  # For general skill recommendations
        "min_peer_suggestions_before_pure_trends": 3,  # For general skill recommendations
        "min_recommendation_score": 0.08,  # For general skill recommendations
        "max_total_suggestions_per_person": 5,  # For general skill recommendations
        "trending_skill_base_score": 0.05,  # For general skill recommendations
        "trending_skill_relevance_map": {
            "generative ai": 1.5, "prompt engineering": 1.4, "cloud security": 1.3,
            "communication": 0.8, "time management": 0.7, "negotiation skills": 0.9, "power bi": 1.1,
            "python": 1.2, "java": 1.2, "react": 1.1, "node.js": 1.1, "sql": 1.0, "machine learning": 1.3
        },
        "adaptive_threshold_attempts": [0.45, 0.40, 0.35, 0.30, 0.25]  # For peer-to-peer recommendations
    }
}

# Global Sentence Transformer model instance to load once
SBERT_MODEL = None


# --- Data Preprocessing ---
def preprocess_skills_text(text_list_or_str):
    """
    Preprocesses skills text. Handles both a list of skills and a comma-separated string.
    Corrects spelling and applies synonyms.
    """
    if isinstance(text_list_or_str, list):
        text = ', '.join(text_list_or_str)
    elif not isinstance(text_list_or_str, str):
        return ""
    else:
        text = text_list_or_str

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


# --- Data Loading and Embedding Generation from Django ORM ---

def load_employee_data_for_recommendation():
    """
    Loads comprehensive employee data from Django's UserProfile, emp_registers, and Task models.
    Parses JSON fields, preprocesses text, performs task analysis, and generates SBERT embeddings
    for a holistic employee profile.
    """
    if UserProfile is None or emp_registers is None or Task is None or Member is None or StatusMaster is None:
        print("Django models not loaded. Cannot fetch data from DB.")
        return pd.DataFrame()

    print(f"[{datetime.datetime.now()}] Loading employee data from Django ORM for recommendation...")
    data_list = []
    try:
        user_profiles = UserProfile.objects.select_related('emp_register').all()

        # Optimize task fetching: Get all relevant tasks once and map them to members
        # This assumes Member.emp_register links to emp_registers
        all_members = Member.objects.select_related('emp_register').all()
        member_to_emp_reg_id = {m.id: m.emp_register.id for m in all_members if m.emp_register}
        emp_reg_id_to_member_id = {m.emp_register.id: m.id for m in all_members if m.emp_register}

        # Fetch all tasks and group by assigned member ID
        all_tasks = Task.objects.select_related('project', 'status').prefetch_related('assigned_to').all()
        tasks_by_member_id = defaultdict(list)
        for task in all_tasks:
            for member in task.assigned_to.all():
                tasks_by_member_id[member.id].append(task)

        for profile in user_profiles:
            emp_id = profile.emp_register.employee_id
            name = profile.name

            # Get the Member ID associated with this emp_register for task lookup
            member_id_for_tasks = emp_reg_id_to_member_id.get(profile.emp_register.id)

            # Extract and preprocess skills, projects, experiences
            raw_skills = [s.get('skill_name') for s in profile.get_skills() if s.get('skill_name')]
            processed_skills = preprocess_skills_text(raw_skills)

            projects_text = " ".join([p.get('description', '') for p in profile.get_projects() if p.get('description')])
            experiences_data = profile.get_experiences()
            experiences_text = " ".join([e.get('description', '') for e in experiences_data if e.get('description')])
            roles_from_experience = " ".join([e.get('role', '') for e in experiences_data if e.get('role')])
            certifications_text = " ".join(
                [e.get('certification_name', '') for e in experiences_data if e.get('certification_name')])

            role = profile.emp_register.designation if hasattr(profile.emp_register, 'designation') else ''
            role_combined = f"{role} {roles_from_experience}".strip()

            # --- Task Analysis ---
            today = datetime.date.today()
            active_tasks = 0
            overdue_tasks = 0
            total_tasks = 0
            tasks_on_time = 0
            is_on_going = False  # True if any active task exists

            if member_id_for_tasks is not None:
                tasks_for_employee = tasks_by_member_id.get(member_id_for_tasks, [])

                for task in tasks_for_employee:
                    total_tasks += 1
                    # Check status name from StatusMaster
                    if task.status and task.status.name.lower() in ['in progress', 'assigned',
                                                                    'open']:  # Adjust status names as per your StatusMaster
                        active_tasks += 1
                        is_on_going = True
                        if task.due_date and task.due_date < today:
                            overdue_tasks += 1
                    if task.complete_date and task.due_date and task.complete_date.date() <= task.due_date.date():  # Compare dates only
                        tasks_on_time += 1

            task_analysis_summary = {
                'total_tasks': total_tasks,
                'active_tasks': active_tasks,
                'overdue_tasks': overdue_tasks,
                'tasks_on_time': tasks_on_time,
                'on_time_percentage': (tasks_on_time / total_tasks) * 100 if total_tasks > 0 else 0,
                'is_on_going': is_on_going
            }

            data_list.append({
                'ID': emp_id,
                'Name': name,
                'Skills': processed_skills,
                'Projects': projects_text,
                'Certifications': certifications_text,
                'Role': role_combined,
                'Task_Analysis': task_analysis_summary
            })

        employee_data_df = pd.DataFrame(data_list)
        if employee_data_df.empty:
            raise ValueError("No employee data found in Django models.")

        # --- Generate SBERT Embeddings for the comprehensive profile ---
        global SBERT_MODEL
        if SBERT_MODEL is None:
            print(f"[{datetime.datetime.now()}] Loading Sentence Transformer model '{CONFIG['sbert_model_name']}'...")
            SBERT_MODEL = SentenceTransformer(CONFIG['sbert_model_name'])
            print(f"[{datetime.datetime.now()}] Sentence Transformer model loaded.")

        # Construct the comprehensive profile string for SBERT
        employee_data_df['profile'] = employee_data_df['Skills']  # Always include skills
        if CONFIG["recommendation_params"].get('weight_projects', 0) > 0:
            employee_data_df['profile'] += employee_data_df['Projects'].apply(lambda x: '. ' + x if x else '')
        if CONFIG["recommendation_params"].get('weight_certifications', 0) > 0:
            employee_data_df['profile'] += employee_data_df['Certifications'].apply(lambda x: '. ' + x if x else '')
        if CONFIG["recommendation_params"].get('weight_roles', 0) > 0:
            employee_data_df['profile'] += employee_data_df['Role'].apply(lambda x: '. ' + x if x else '')

        # Clean up profile string
        employee_data_df['profile'] = employee_data_df['profile'].str.replace(r'\s*\.\s*', '. ',
                                                                              regex=True).str.replace(r'\.{2,}', '.',
                                                                                                      regex=True).str.strip()
        employee_data_df['profile'] = employee_data_df['profile'].apply(lambda x: x[2:] if x.startswith('. ') else x)
        employee_data_df['profile'] = employee_data_df['profile'].apply(
            lambda x: "no information provided" if not x else x)

        print(f"[{datetime.datetime.now()}] Encoding employee profiles with Sentence Transformer...")
        embeddings = SBERT_MODEL.encode(employee_data_df['profile'].tolist(), show_progress_bar=False,
                                        convert_to_numpy=True)
        employee_data_df['profile_embedding'] = list(embeddings)

        print(
            f"[{datetime.datetime.now()}] Successfully loaded {len(employee_data_df)} employee records and generated embeddings.")
        return employee_data_df

    except Exception as e:
        print(f"Error loading employee data from Django ORM: {e}")
        return pd.DataFrame()


def get_project_skill_embedding(project_skills, sbert_model):
    """
    Generates a single embedding for a list of project skills.
    """
    if not project_skills:
        return None
    project_skills_string = ", ".join(project_skills)
    print(f"[{datetime.datetime.now()}] Encoding project skills: '{project_skills_string}'")
    embedding = sbert_model.encode([project_skills_string], convert_to_numpy=True)
    return embedding[0]


def recommend_project_members(employee_data_df, project_skills, top_n=5, min_final_score=0.2):
    """
    Recommends employees for a project based on skill/experience similarity and task analysis.

    Args:
        employee_data_df (pd.DataFrame): DataFrame containing employee data, including
                                        'profile_embedding' and 'Task_Analysis'.
                                        This DataFrame should be pre-loaded and pre-embedded.
        project_skills (list): List of skills required for the project.
        top_n (int): Number of top employees to recommend.
        min_final_score (float): Minimum combined score for an employee to be recommended.

    Returns:
        pd.DataFrame: DataFrame of recommended employees with their scores.
    """
    if employee_data_df.empty or 'profile_embedding' not in employee_data_df.columns:
        print(
            "Error: Employee data is empty or 'profile_embedding' is missing. Ensure load_employee_data_for_recommendation was run.")
        return pd.DataFrame()

    global SBERT_MODEL
    if SBERT_MODEL is None:
        print("SBERT model not loaded. Please ensure it's loaded before calling this function.")
        return pd.DataFrame()

    project_embedding = get_project_skill_embedding(project_skills, SBERT_MODEL)
    if project_embedding is None:
        print("No project skills provided for recommendation.")
        return pd.DataFrame()

    # Calculate cosine similarity between project embedding and each employee's comprehensive profile embedding
    similarity_scores = []
    for emp_embedding in employee_data_df['profile_embedding']:
        score = cosine_similarity(project_embedding.reshape(1, -1), emp_embedding.reshape(1, -1))[0][0]
        similarity_scores.append(score)

    employee_data_df['Skill_Match_Score'] = similarity_scores  # Renamed for clarity

    # --- Incorporate Task Analysis into the Final Recommendation Score ---
    # 1. Availability (based on 'is_on_going' and active tasks)
    # Give a penalty if they have ongoing tasks, or a boost if they are free.
    employee_data_df['Availability_Score'] = employee_data_df['Task_Analysis'].apply(
        lambda x: 0.7 if x['is_on_going'] else 1.0  # 1.0 if free, 0.7 if ongoing
    )

    # 2. Performance (on-time percentage) - higher is better
    employee_data_df['On_Time_Performance_Score'] = employee_data_df['Task_Analysis'].apply(
        lambda x: x['on_time_percentage'] / 100  # Normalize to 0-1
    )

    # 3. Overdue Task Penalty - lower score if they have overdue tasks
    # A simple approach: 0.5 penalty if any overdue, else 1.0. Can be more nuanced.
    employee_data_df['Overdue_Penalty_Factor'] = employee_data_df['Task_Analysis'].apply(
        lambda x: 0.5 if x['overdue_tasks'] > 0 else 1.0
    )

    # Combine scores with adjustable weights
    # These weights are crucial for tuning the recommendation system.
    # Experiment with them based on what HR prioritizes (skills, availability, performance).
    weight_skill_match = 0.60
    weight_availability = 0.20
    weight_performance = 0.15
    weight_overdue_impact = 0.05  # This weight is for how much overdue tasks reduce the score

    # Calculate Final Recommendation Score
    employee_data_df['Final_Recommendation_Score'] = (
                                                             employee_data_df['Skill_Match_Score'] * weight_skill_match
                                                             + employee_data_df[
                                                                 'Availability_Score'] * weight_availability
                                                             + employee_data_df[
                                                                 'On_Time_Performance_Score'] * weight_performance
                                                     ) * employee_data_df[
                                                         'Overdue_Penalty_Factor']  # Apply overdue penalty multiplicatively

    # Sort and filter by minimum final score
    recommended_df = employee_data_df[employee_data_df['Final_Recommendation_Score'] >= min_final_score].sort_values(
        by='Final_Recommendation_Score', ascending=False
    ).head(top_n)

    return recommended_df[
        ['ID', 'Name', 'Skills', 'Role', 'Task_Analysis', 'Skill_Match_Score', 'Final_Recommendation_Score']]


# --- Standalone Test Block ---
if __name__ == "__main__":
    print("--- Running standalone test for Project Recommendation ---")

    # Simulate creation of a trending skills JSON file (for completeness, not directly used in project rec)
    trending_skills_for_demo = [
        "Python", "Excel", "Generative AI", "Prompt Engineering", "Cloud Security", "DevOps",
        "Communication", "Teamwork", "Problem Solving"
    ]
    with open(CONFIG["trending_skills_source"], "w") as f:
        json.dump({"trending_skills": trending_skills_for_demo}, f)
    print(f"Simulated '{CONFIG['trending_skills_source']}' created for demonstration.")

    # Load all employee data and generate their comprehensive embeddings
    employee_data_df = load_employee_data_for_recommendation()
    if employee_data_df.empty:
        print("No employee data loaded. Exiting standalone test.")
        sys.exit(1)

    # Example new project skills entered by HR
    new_project_skills_hr = ["Generative AI", "Prompt Engineering", "Python", "React", "Cloud Security",
                             "Agile Methodologies", "Communication", "DevOps"]

    print(f"\nRecommending members for a project requiring: {', '.join(new_project_skills_hr)}")

    # Get recommendations
    recommended_members_df = recommend_project_members(
        employee_data_df.copy(),  # Pass a copy, as recommend_project_members adds columns
        new_project_skills_hr,
        top_n=5,
        min_final_score=0.4  # Adjust this threshold as needed
    )

    if not recommended_members_df.empty:
        print("\nTop Recommended Project Members:")
        print(recommended_members_df)
        output_project_members_excel = "project_member_recommendations_hr_flow_full_analysis.xlsx"
        recommended_members_df.to_excel(output_project_members_excel, index=False)
        print(f"\nProject member recommendations saved to {output_project_members_excel}")
    else:
        print("\nNo project members recommended.")

    print("\nStandalone test complete.")