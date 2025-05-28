import os

# Define the paths relative to the script's location (which is your project root)
management_init_path = os.path.join('management', '__init__.py')
commands_init_path = os.path.join('management', 'commands', '__init__.py')

# Ensure directories exist (redundant if already created, but safe)
os.makedirs(os.path.dirname(management_init_path), exist_ok=True)
os.makedirs(os.path.dirname(commands_init_path), exist_ok=True)

# Create truly empty __init__.py files
with open(management_init_path, 'w', encoding='utf-8') as f:
    pass # Creates an empty file

with open(commands_init_path, 'w', encoding='utf-8') as f:
    pass # Creates an empty file

print(f"Created empty {management_init_path}")
print(f"Created empty {commands_init_path}")