import json

from bs4 import BeautifulSoup


class JSONData:
    def __init__(self, file_path):
        with open(file_path, "r") as f:
            self.json_data = json.load(f)

    def extract_meaningful_info(self, data):
        """
        Extracts meaningful information from JSON data.

        Args:
            data (dict): A dictionary containing JSON data.

        Returns:
            dict: A dictionary containing the extracted meaningful information.
                The dictionary has the following keys:
                - id (int): The ID of the data.
                - title (str): The title of the data.
                - likes (int): The number of likes for the data.
                - description (str): The description of the data.
                - tags (list): A list of tags associated with the data.
        """
        meaningful_info = {}
        meaningful_info["id"] = data["id"]
        meaningful_info["title"] = data["name"]
        meaningful_info["likes"] = data["like_count"]
        meaningful_info["description"] = data["description"]
        meaningful_info["tags"] = data["tags"]

        return meaningful_info

    def clean_data(self):
        cleaned_data = []

        for data in self.json_data:
            meaningful_info = self.extract_meaningful_info(data)

            html_info = meaningful_info["description"]
            soup = BeautifulSoup(html_info, "html.parser")
            text = soup.get_text(separator=" ")
            padded_text = "\n".join(["    " + line for line in text.split("\n")])

            meaningful_info["description"] = padded_text
            cleaned_data.append(meaningful_info)

        return cleaned_data


if __name__ == "__main__":
    data = JSONData("../data/latest/meta.json")
    cleaned_data = data.clean_data()

    with open("../data/latest/cleaned_meta.json", "w") as f:
        json.dump(cleaned_data, f, indent=4)
