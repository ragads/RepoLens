import json
import os
import glob

def run_notebook(notebook_path):
    print(f"--- Running {notebook_path} ---")
    with open(notebook_path, 'r') as f:
        nb = json.load(f)
    
    code_cells = [c['source'] for c in nb['cells'] if c['cell_type'] == 'code']
    
    # helper for exec context
    global_context = {}
    
    for i, source in enumerate(code_cells):
        code = "".join(source)
        try:
            # Change directory to notebook's dir to ensure relative paths (like ../data) work
            # We assume notebooks are in a subdirectory
            current_dir = os.getcwd()
            nb_dir = os.path.dirname(os.path.abspath(notebook_path))
            os.chdir(nb_dir)
            
            exec(code, global_context)
            
            os.chdir(current_dir)
        except Exception as e:
            # Make sure to revert dir in case of error
            os.chdir(current_dir)
            print(f"Error in cell {i}:\n{code}\nError: {e}")
            raise e
    print(f"--- Completed {notebook_path} ---\n")

def main():
    notebooks = [
        'notebooks/1_data_preprocessing.ipynb',
        'notebooks/2_isolation_forest.ipynb',
        'notebooks/3_gradient_boosting.ipynb',
        'notebooks/4_model_evaluation.ipynb'
    ]
    
    for nb in notebooks:
        if os.path.exists(nb):
            run_notebook(nb)
        else:
            print(f"Notebook {nb} not found.")

if __name__ == "__main__":
    main()
