from pyicloud import PyiCloudService
import yaml
import os


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

    # TODO: Move these lines of code to execute after sync with icloud passwords dir.
    # if not config.local_passwords_dir:
    #     # Specify the path to the password directory.
    #     passwords_dir = input("enter path to the passwords directory:")
    #     passwords_dir = rm_tilde(passwords_dir)
    #     print("input:", passwords_dir)

    #     if not os.path.isdir(passwords_dir):
    #         print(f"Error: the directory '{passwords_dir}' does not exist.")
    #         exit(1)

    icloud_passwords_dir = config.icloud_passwords_dir
    if not icloud_passwords_dir:
        print("Error: iCloud Drive passwords directory path required.")

    # Access the drive and read the files within the icloud passwords directory.
    try:
        files = api.drive[icloud_passwords_dir].dir()
    except Exception as e:
        print(f"Error: Could not find icloud passwords directory: {e}.")
        exit(1)

    print("Authentication status:", api.authenticate())
    print("Requires 2FA:", api.requires_2fa)
    print("Is trusted session:", api.is_trusted_session)

    # Sort files by their modification dates and check the youngest one and get the title of it.
    for filename in files:
        print(api.drive[icloud_passwords_dir][filename].name)

    print("Program completed succesfully.")
