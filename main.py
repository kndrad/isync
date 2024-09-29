from pyicloud import PyiCloudService
import yaml
import os
from datetime import datetime
from typing import List
from os.path import join

DATETIME_FORMAT = "%H:%M %d-%m-%Y"


def rm_tilde(path) -> str:
    if path.startswith("~"):
        path = os.environ["HOME"] + path[1:]
    return path


class Config:
    def __init__(self, path: str):
        with open(path, "r") as f:
            config = yaml.safe_load(f)

            self.apple_id = config["login"]["username"]
            self.password = config["login"]["password"]

            local_passwords_dir = config["paths"]["local_passwords_dir"]
            local_passwords_dir = rm_tilde(local_passwords_dir)

            if not os.path.isdir(local_passwords_dir):
                print(f"Error: the directory '{local_passwords_dir}' does not exist.")

            self.local_passwords_dir = local_passwords_dir
            self.icloud_passwords_dir = config["paths"]["icloud_passwords_dir"]


def read_config(path: str) -> Config:
    config = Config(path)
    return config


class PasswordFile:
    def __init__(self, name: str, date_modified: datetime):
        self.name = name
        self.date_modified = date_modified

    def __str__(self) -> str:
        return f"{self.name}    {self.date_modified.strftime("%H:%M %d-%m-%Y")}"

    def __lt__(self, other) -> bool:
        return self.date_modified < other.date_modified


def icloud_passwords(path: str) -> List[PasswordFile]:
    if not path:
        print("Error: iCloud Drive passwords directory path required.")
        raise Exception  # TODO

    password_files: List[PasswordFile] = []

    for filename in api.drive[path].dir():
        name = api.drive[path][filename].name
        date_modified = api.drive[path][filename].date_modified
        password_files.append(PasswordFile(name=name, date_modified=date_modified))

    return sorted(password_files, reverse=True)


def local_passwords(path: str) -> List[PasswordFile]:
    local_passwords_path = config.local_passwords_dir
    if not local_passwords_path:
        print("Error: Local passwords directory path required.")
        exit(1)

    local_password_files: List[PasswordFile] = []

    for root, dirs, files in os.walk(local_passwords_path):
        for name in files:
            stat_result = os.stat(join(root, name))

            # Convert into normal datetime object.
            date_modified = datetime.fromtimestamp(stat_result.st_mtime)
            local_password_files.append(
                PasswordFile(name=name, date_modified=date_modified)
            )

    return sorted(local_password_files)


if __name__ == "__main__":
    # Credentials can be read from the keyring as well.
    #
    # Docs of pyicloud:
    #   "Authentication will expire after an interval set by Apple,
    #   at which point you will have to re-authenticate.
    #   This interval is currently two months."
    config = read_config("./config_dev.yaml")

    apple_id = config.apple_id
    password = config.password

    api = PyiCloudService(apple_id=apple_id, password=password)
    api.authenticate()

    if api.requires_2fa:
        code = input("enter code:")
        result = api.validate_2fa_code(code)
        print("2fa validation ok:", result)

    if not api.is_trusted_session:
        api.trust_session()

    if api.requires_2fa or not api.is_trusted_session:
        print(
            "Error: Authentication failed. Please check your credentials and try again."
        )
        exit(1)

    # Get icloud drive passwords directory path from config
    # then read all files from that directory.
    try:
        icloud_passwords = icloud_passwords(config.icloud_passwords_dir)
    except Exception as e:
        print(e)
        exit(1)

    # Now get local password files directory by it's path read from config.
    try:
        local_passwords: List[PasswordFile] = local_passwords(
            config.local_passwords_dir
        )
    except Exception as e:
        print(e)
        exit(1)

    # Compare local password files with that from the icloud drive.
    local_newest_pswd_file = local_passwords[0]
    print("Newest local passwords file:", local_newest_pswd_file)

    icloud_newest_pswd_file = icloud_passwords[0]
    print("Newest icloud passwords drive:", icloud_newest_pswd_file)

    local_pswd_date = local_newest_pswd_file.last_modified.date()
    icloud_pswd_date = icloud_newest_pswd_file.last_modified.date()

    # For testing purposes, to see if it's capable of listing dir contents:
    try:
        print(
            "Contents of iCloud passwords directory:",
            api.drive[config.icloud_passwords_dir].dir(),
        )
    except Exception as e:
        print("Error listing iCloud directory:", e)

    # Check if local needs to be synchronized with the iCloud drive
    if local_pswd_date > icloud_pswd_date:
        print(
            f"Local password file {local_newest_pswd_file.name} is newer than the icloud one - syncing..."
        )
        local_pswd_file_path = join(
            config.local_passwords_dir, local_newest_pswd_file.name
        )
        with open(local_pswd_file_path, "rb") as file_in:
            # FIX for KeyError: "clientid"
            api._drive.params["clientId"] = api.client_id

            try:
                api.drive[config.icloud_passwords_dir].upload(file_in)
                print(f"File {local_newest_pswd_file.name} uploaded.")
            except Exception as e:
                print(f"Error uploading file: {e}")
    elif local_pswd_date < icloud_pswd_date:
        print(
            f"iCloud password file {icloud_newest_pswd_file.name} is newer than the local one - syncing..."
        )
        # TODO: Synchronization logic
    else:
        print(
            "No need for synchronization between local password files and iCloud password files."
        )

    print("Program completed succesfully.")
