#!/usr/bin/env python3
"""Generate mkgendocs.yaml from Python files by iterating over files, classes, functions, and methods."""

import os
import ast
import yaml


def get_mkgendocs_config():
    """
    Get the mkgendocs configuration file.

    If the file does not exist, return an empty dictionary.
    If there's a parsing error, raise an exception.

    Returns:
        dict: The mkgendocs configuration.
    """
    try:
        with open("mkgendocs.yaml", encoding="UTF-8") as mkgendocs_config:
            return yaml.safe_load(mkgendocs_config) or {}
    except FileNotFoundError:
        print("mkgendocs.yaml not found. A new configuration will be created.")
        return {}
    except yaml.YAMLError as error_message:
        print("Error parsing mkgendocs.yaml")
        raise yaml.YAMLError from error_message


def get_python_files(directory):
    """
    Get a list of Python files in a directory, excluding 'tests' and 'dist' folders.

    Args:
        directory (str): Directory to search.

    Returns:
        list: List of Python file paths.
    """
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Modify dirs in-place to exclude 'tests' and 'dist'
        dirs[:] = [d for d in dirs if d not in ("tests", "dist")]

        for file in files:
            if file.endswith(".py") and not file.startswith("_"):
                python_files.append(os.path.join(root, file))
    return python_files


def extract_definitions(filename):
    """
    Extract classes, methods, and functions from a Python file using AST.

    Args:
        filename (str): The name of the Python file to parse.

    Returns:
        dict: A dictionary with 'classes' and 'functions' keys.
    """
    with open(filename, encoding="UTF-8") as file:
        file_content = file.read()

    tree = ast.parse(file_content, filename=filename)
    definitions = {"classes": [], "functions": []}

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                class_node.name
                for class_node in node.body
                if isinstance(class_node, ast.FunctionDef)
            ]
            if methods:
                # Add class with its methods
                definitions["classes"].append({node.name: methods})
            else:
                # Add class without methods
                definitions["classes"].append(node.name)
        elif isinstance(node, ast.FunctionDef):
            definitions["functions"].append(node.name)

    return definitions


def main():
    """Generate configuration for mkgendocs to build documentation."""
    print("Starting doc generation")

    # Load existing configuration or create a new one
    mkgendocs_config = get_mkgendocs_config()

    # Set 'sources_dir'
    mkgendocs_config["sources_dir"] = "docs/"

    # Set 'repo' to the current working directory
    mkgendocs_config["repo"] = "https://github.com/astercapital/airless"

    # Set 'version' to 'master'
    mkgendocs_config["version"] = "master"

    # Ensure that 'sources_dir'
    os.makedirs(mkgendocs_config["sources_dir"], exist_ok=True)

    new_pages = []

    packages_dir = "packages"
    if not os.path.isdir(packages_dir):
        print(f"Directory '{packages_dir}' does not exist.")
        return

    print("Getting a list of Python files in 'packages'...")
    python_files = get_python_files(packages_dir)
    for python_file in python_files:
        definitions = extract_definitions(python_file)
        relative_python_file = os.path.relpath(python_file, start=".")

        # Determine the corresponding markdown page path
        # For example, "packages/package1/module1.py" -> "api/package1/module1.md"
        if relative_python_file.startswith("packages" + os.sep):
            relative_path = os.path.relpath(relative_python_file, start="packages")
            page_path = os.path.join("packages", os.path.splitext(relative_path)[0] + ".md")
        else:
            page_path = os.path.splitext(relative_python_file)[0] + ".md"

        # Normalize paths to use forward slashes
        page_path = page_path.replace(os.sep, "/")
        source_path = relative_python_file.replace(os.sep, "/")

        page_entry = {
            "page": page_path,
            "source": source_path,
        }

        # Add classes and their methods if any
        if definitions["classes"]:
            page_entry["classes"] = definitions["classes"]

        # Add functions if any
        if definitions["functions"]:
            page_entry["functions"] = definitions["functions"]

        # Determine if this should be an index page
        # For example, if the file is __init__.py
        if os.path.basename(python_file) == "__init__.py":
            page_entry["index"] = True

        has_content = bool(
            definitions["classes"] or definitions["functions"] or page_entry.get("index")
        )

        if has_content:
            print(f"Definitions found in {python_file}, adding to documentation.")
            new_pages.append(page_entry)
        else:
            print(f"No definitions found in {python_file}, skipping.")

    mkgendocs_config["pages"] = new_pages

    try:
        with open("mkgendocs.yaml", "w", encoding="UTF-8") as mkgendocs_config_file:
            yaml.dump(mkgendocs_config, mkgendocs_config_file, sort_keys=False)
        print("mkgendocs.yaml has been updated successfully.")
    except Exception as e:
        print(f"Error writing to mkgendocs.yaml: {e}")


if __name__ == "__main__":
    main()
