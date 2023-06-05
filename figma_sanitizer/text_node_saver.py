import glob
import json
import os
import sqlite3


# Function to find all text nodes in the JSON object
def find_text_nodes(json_object, result):
    if isinstance(json_object, dict):
        if json_object.get("type") == "TEXT":
            result.append(json_object)
        for _, value in json_object.items():
            find_text_nodes(value, result)
    elif isinstance(json_object, list):
        for item in json_object:
            find_text_nodes(item, result)

def main():
    # Create SQLite database and table
    conn = sqlite3.connect("text_nodes.db")
    cursor = conn.cursor()

    # Delete the table if it already exists
    cursor.execute("DROP TABLE IF EXISTS text_nodes")

    # Create the table
    cursor.execute("""CREATE TABLE text_nodes (
                      id TEXT PRIMARY KEY,
                      name TEXT,
                      type TEXT,
                      json_data TEXT
                      )""")

    # Loop through matching folders
    for folder in glob.glob("../data/samples/figma-samples-5k.min/*"):

        # if not a folder, skip
        if not os.path.isdir(folder):
            continue

        json_file = os.path.join(folder, "file.json")

        # Extract parent folder name
        parent_folder_name = os.path.basename(os.path.dirname(json_file))

        # Load JSON data
        try:
            with open(json_file, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            print(f"The file {json_file} does not exist.")
            # Handle the error or continue with the program execution


        # Find all the text nodes
        text_nodes = []
        find_text_nodes(data, text_nodes)

        # Insert text nodes into the database
        for node in text_nodes:
            # Concatenate parent_folder_name and node's id value
            try:
                prefixed_id = f"{parent_folder_name}_{node['id']}"
            except KeyError as e:
                continue

            cursor.execute("""INSERT INTO text_nodes (id, name, type, json_data)
                              VALUES (?, ?, ?, ?)""",
                           (prefixed_id, node["name"], node["type"], json.dumps(node)))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
