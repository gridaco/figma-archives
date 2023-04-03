import json
import os


def extract_absolute_bounding_box(json_data):
    """

    Extracts the absolute bounding box of all top level frames in a Figma file.

    """
    result = []

    if json_data['document']['type'] == "DOCUMENT":
        for node in json_data['document']['children']:
            if node['type'] == "CANVAS":
                for child in node['children']:
                    if child['type'] == "FRAME":
                        result.append(child['absoluteBoundingBox'])

    return result

def main():
    """

    This script will extract the absolute bounding box of all top level frames in a Figma file.

    """
    # Use a relative path from the script's directory
    relative_path_folder = "../data/samples/figma-samples-5k.min"

    for folder in os.listdir(relative_path_folder):
        folder_path = os.path.join(relative_path_folder, folder)
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith("file.json"):
                    print(os.path.join(folder_path, file))

                    try:
                        with open(os.path.join(folder_path, file), "r") as json_file:
                            json_data = json.load(json_file)
                    except:
                        print(f"Error loading JSON data from {file}")
                        continue

                    absolute_bounding_boxes = extract_absolute_bounding_box(json_data)

                    with open("artifacts/top_level_frame_size_stat.txt", "a") as stat_file:
                        for box in absolute_bounding_boxes:
                            stat_file.write(str(box["width"]) + ",")
                        stat_file.write("\n")

if __name__ == "__main__":
    main()
