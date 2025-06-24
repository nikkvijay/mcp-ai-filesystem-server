import os

def create_file(file_path, content):
    with open(file_path, 'w') as file:
        file.write(content)

def edit_file(file_path, new_content):
    with open(file_path, 'w') as file:
        file.write(new_content)

def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        raise FileNotFoundError(f"The file {file_path} does not exist.")