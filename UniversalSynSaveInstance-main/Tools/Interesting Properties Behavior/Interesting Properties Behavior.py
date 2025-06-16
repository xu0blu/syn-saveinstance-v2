import requests
import os
import re


def array_to_dictionary(table, hybrid_mode=None):
    tmp = {}
    if hybrid_mode == "adjust":
        for key, value in table.items():
            if isinstance(key, int):
                tmp[value] = True
            elif isinstance(value, dict):
                tmp[key] = array_to_dictionary(value, "adjust")
            else:
                tmp[key] = value
    else:
        for value in table:
            if isinstance(value, str):
                tmp[value] = True
    return tmp


s = "\n"


def api():

    deploy_history_url = "https://setup.rbxcdn.com/DeployHistory.txt"
    deploy_history = requests.get(deploy_history_url).text

    lines = deploy_history.splitlines()

    for line in reversed(lines):

        match = re.search(r"(version-[^\s]+)", line)

        if match:
            version_hash = match.group(1)

            api_dump_url = f"https://setup.rbxcdn.com/{version_hash}-Full-API-Dump.json"

            try:
                response = requests.get(api_dump_url)
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                print(f"Error fetching API dump for {version_hash}: {e}")


def fetch_api():
    response = api()
    api_classes = response.json()["Classes"]

    global s
    class_list = {}

    for api_class in api_classes:
        class_name = api_class["Name"]
        class_members = api_class["Members"]
        class_tags = api_class.get("Tags")

        if class_tags:
            # print(class_tags)
            if len(class_tags) == 0:
                print("tagsempty")
            class_tags = array_to_dictionary(class_tags)
        else:
            print(class_name, "notags")

        class_info = {
            "Tags": class_tags,
            "Superclass": api_class["Superclass"],
            "Properties": {},
        }

        prev_len = len(s)

        for member in class_members:
            if member["MemberType"] == "Property":
                property_name = member["Name"]
                ignored = False

                if not ignored:
                    member_tags = member.get("Tags")

                    if member_tags:
                        member_tags = array_to_dictionary(member_tags)

                    serialization = member["Serialization"]
                    if (
                        serialization["CanLoad"] or serialization["CanSave"]
                    ):  # Check if at least one is true
                        tags = []

                        # Add CanLoad/CanSave conditions
                        if serialization["CanLoad"] and not serialization["CanSave"]:
                            tags.append("{CanLoad Only}")
                        elif serialization["CanSave"] and not serialization["CanLoad"]:
                            tags.append("{CanSave Only}")

                        # Add Deprecated tag if present
                        if member_tags and member_tags.get("Deprecated"):
                            deprecated_tag = "{Deprecated}"
                            if serialization["CanSave"]:
                                deprecated_tag += " {CanSave}"
                            tags.append(deprecated_tag)

                        # Combine tags into one line, each tag in separate brackets
                        if tags:
                            s += f"{class_name}.{property_name} {' '.join(tags)}\n"

                    class_info["Properties"][property_name] = {
                        "Serialization": serialization,
                        "Tags": member_tags,
                        "Default": member.get("Default"),
                    }

        if class_tags and class_tags.get("NotCreatable"):
            for property_name, property_info in class_info["Properties"].items():
                value = property_info.get("Default")
                if (
                    value != "__api_dump_class_not_creatable__"
                    and "__api_dump_" not in value
                ):
                    s += f"{class_name} is NotCreatable but {class_name}.{property_name} has a default value: {value}\n"
                    break

        if len(s) != prev_len:
            s += "\n"

        class_list[class_name] = class_info

    return class_list


try:
    fetch_api()
    print(s)
    script_dir = os.path.dirname(os.path.realpath(__file__))
    output_file_path = os.path.join(script_dir, "Dump")
    with open(output_file_path, "w") as file:
        file.write(s)
except Exception as e:
    print(f"Error: {e}")
