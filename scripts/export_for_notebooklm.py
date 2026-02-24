import os

def export_codebase():
    root_dir = "/Users/anurag/codebase/personalProjects/tiger_research_buddy"
    output_file = os.path.join(root_dir, "notebookllm_source.txt")
    
    # Directories to completely ignore during traversal
    ignore_dirs = {'.git', '__pycache__', 'venv', 'env', '.venv', 'node_modules', '.gemini', '.pytest_cache', '__MACOSX'}
    
    # Allowed extensions to include
    allowed_exts = {'.py', '.md', '.yaml', '.yml', '.toml', '.txt'}
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("# Tiger Research Buddy - Project Source Code & Details\n\n")
        out.write("This document contains the source code, documentation, and prompt configurations for the Tiger Research Buddy project. It is intended to be used as a knowledge base.\n\n")
        
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Remove ignored directories in-place so we don't traverse them
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
            
            # Sort files for consistent output
            filenames.sort()
            
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                rel_path = os.path.relpath(file_path, root_dir)
                
                # Skip hidden files
                if file.startswith('.'):
                    continue
                    
                # Check extension
                ext = os.path.splitext(file)[1].lower()
                if ext not in allowed_exts and file != 'Makefile':
                    continue
                    
                # Exclude the data directory heavily, EXCEPT for the prompts directory which has our LLM instructions
                if rel_path.startswith('data/') and not rel_path.startswith('data/prompts/'):
                    continue
                
                # We also shouldn't include this generator script or the output itself
                if file == "notebookllm_source.txt" or file == "export_for_notebooklm.py":
                    continue
                
                # Write file content
                out.write(f"## File: {rel_path}\n\n")
                lang = ext[1:] if ext else 'text'
                if lang == 'md': lang = 'markdown'
                if file == 'Makefile': lang = 'makefile'
                
                out.write(f"```{lang}\n")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        out.write(f.read())
                except Exception as e:
                    out.write(f"Error reading file: {e}\n")
                out.write(f"\n```\n\n")
                
    print(f"Successfully generated {output_file} ({os.path.getsize(output_file) / 1024 / 1024:.2f} MB)")

if __name__ == "__main__":
    export_codebase()
