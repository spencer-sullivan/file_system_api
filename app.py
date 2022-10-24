import os
import pathlib

from flask import Flask

from blueprints.file_system_endpoints import blueprint as file_system_list_endpoint


_ROOT_DIRECTORY_ENV_VARIABLE = "ROOT_DIRECTORY"
_ROOT_DIRECTORY_DEFAULT = "./root_directory"


def _get_root_directory() -> pathlib.Path:
    root_directory = pathlib.Path(os.environ.get(_ROOT_DIRECTORY_ENV_VARIABLE, _ROOT_DIRECTORY_DEFAULT))

    if not root_directory.exists():
        raise ValueError(f"The specified path does not exist: {root_directory}")
    if not root_directory.is_dir():
        raise ValueError(f"The specified path is not a directory: {root_directory}")
    return root_directory


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["root_directory"] = _get_root_directory()
    app.register_blueprint(file_system_list_endpoint)
    return app


if __name__ == "__main__":
    create_app().run()
