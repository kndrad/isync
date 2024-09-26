from pyicloud import PyiCloudService
import yaml
import os
import datetime
from typing import List


def rm_tilde(path) -> str:
    if path.startswith("~"):
        path = os.environ["HOME"] + path[1:]
    return path


class Config:
    def __init__(self, path: str):
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)

            self.apple_id = cfg["login"]["username"]
            self.password = cfg["login"]["password"]

            passwords_dir = cfg["paths"]["passwords_dir"]
            passwords_dir = rm_tilde(passwords_dir)

            if not os.path.isdir(passwords_dir):
                print(f"Error: the directory '{passwords_dir}' does not exist.")

            self.local_passwords_dir = passwords_dir
            self.icloud_passwords_dir = cfg["paths"]["icloud_passwords_dir"]


def read_config(path: str) -> Config:
    config = Config(path)
    return config


class PasswordFile:
    def __init__(self, name: str, date_modified: datetime.datetime):
        self.name = name
        self.date_modified = date_modified

    def __str__(self) -> str:
        return f"{self.name}    {self.date_modified.strftime("%H:%M %d-%m-%Y")}"

    def __lt__(self, other) -> bool:
        return self.date_modified < other.date_modified


def icloud_password_files(path: str) -> List[PasswordFile]:
    files: List[PasswordFile] = []

    for filename in api.drive[path].dir():
        name = api.drive[path][filename].name
        date_modified = api.drive[path][filename].date_modified
        files.append(PasswordFile(name=name, date_modified=date_modified))

    # Sort files by their modification dates
    return sorted(files, reverse=True)


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
    path = config.icloud_passwords_dir
    if not path:
        print("Error: iCloud Drive passwords directory path required.")
        exit(1)

    icloud_password_files = icloud_password_files(path)

    for file in icloud_password_files:
        print(file)

    print("Program completed succesfully.")
