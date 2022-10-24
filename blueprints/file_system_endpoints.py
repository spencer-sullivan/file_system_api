import base64
from http import HTTPStatus
import os
import pathlib
from pwd import getpwuid
import shutil
import stat
from typing import Dict, Union

from flask import Blueprint, current_app, jsonify, request


blueprint = Blueprint("file_system_list_endpoints", __name__, url_prefix="")


def _get_file_details(path: pathlib.Path) -> Dict[str, Union[str, int]]:
    root_directory = current_app.config["root_directory"].resolve()
    file_stat = os.stat(path, follow_symlinks=False)
    return {
        "file_name": str(path.relative_to(root_directory)),
        "owner": getpwuid(file_stat.st_uid).pw_name,
        "size_in_bytes": file_stat.st_size,
        "permissions_octal": oct(file_stat.st_mode & 0o777)[-3:],
        "permissions_human": stat.filemode(file_stat.st_mode),
    }


@blueprint.route("/", defaults={"path": ""}, methods=["GET"])
@blueprint.route("/<path:path>", methods=["GET"])
def list_files(path: str):
    """
    An endpoint for either listing the files in a directory or listing the contents of a file.
    The path used will be a relative path from the root_directory. This assumes that the file
    contents are small enough to be returned via a single JSON blob, so there is no pagination
    to iterate over the contents.

    Status codes:
    200 - If the file or directory exists, and the contents were sucessfully returned
    403 - If the path is not inside of the root directory. This is a security measure to make sure
          the rest of the file system is not accessible.
    404 - If the file or directory is not found.
    """
    root_directory = current_app.config["root_directory"].resolve()
    full_file_path = (root_directory / path).resolve()

    if full_file_path != root_directory and root_directory not in full_file_path.parents:
        return (
            jsonify({"message": f"Cannot access paths that are outside of the root directory: {path}"}),
            HTTPStatus.FORBIDDEN,
        )

    if not full_file_path.exists():
        return jsonify({"message": f"Could not find file path {path}"}), HTTPStatus.NOT_FOUND

    if full_file_path.is_dir():
        return jsonify({"directory_contents": [_get_file_details(x) for x in full_file_path.iterdir()]})

    with full_file_path.open() as file:
        return jsonify({"file_contents": file.read()}), HTTPStatus.OK


@blueprint.route("/", defaults={"path": ""}, methods=["POST", "PUT"])
@blueprint.route("/<path:path>", methods=["POST", "PUT"])
def create_or_update_file(path: str):
    """
    An endpoint for creating or updating the contents of a file. If directories did not already
    exist, they will automatically be created. For normal ascii payloads, it is recommended to
    pass the body through "contents". For non-ascii data (i.e. images or binary files), it is
    recommeneded that you pass it through base64 encoded in "base64_contents" instead.

    Status codes:
    200 - If the file or directory was successfully created or updated.
    400 - If contents and base64_contents are both not specified, or if the method is POST and the
          file already exists.
    403 - If the path is not inside of the root directory. This is a security measure to make sure
          the rest of the file system is not accessible.
    """
    root_directory = current_app.config["root_directory"].resolve()
    full_file_path = (root_directory / path).resolve()

    if full_file_path != root_directory and root_directory not in full_file_path.parents:
        return (
            jsonify({"message": f"Cannot access paths that are outside of the root directory: {path}"}),
            HTTPStatus.FORBIDDEN,
        )

    if request.method == "POST" and full_file_path.exists():
        return (
            jsonify({"message": f"Path already exists. If you want to override, please use PUT instead: {path}"}),
            HTTPStatus.BAD_REQUEST,
        )

    request_body = request.get_json() or {}
    if "contents" not in request_body and "base64_contents" not in request_body:
        return jsonify({"message": "No file contents specified"}), HTTPStatus.BAD_REQUEST

    full_file_path.parent.mkdir(exist_ok=True, parents=True)

    if "contents" in request_body:
        with full_file_path.open("w+") as file:
            file.write(request_body["contents"])
    elif "base64_contents" in request_body:
        # In case you want to write binary to the file directly, this allows you
        # to pass in a base64 encoded string which will be decoded before being
        # written to the file. This is useful for uploading files such as
        # images, since this endpoint requires the input contents to be an ascii
        # string (a JSON requirement), and the normal string encoding of bytes
        # that looks like "\x00\x00\x00\x00" would produce an output file that is
        # improperly encoded (aka a string-escaped version of the contents).
        with full_file_path.open("wb+") as file:
            file.write(base64.b64decode(request_body["base64_contents"]))
    return jsonify({"message": f"Created file {path}"}), HTTPStatus.OK


@blueprint.route("/", defaults={"path": ""}, methods=["DELETE"])
@blueprint.route("/<path:path>", methods=["DELETE"])
def delete_file(path: str):
    """
    An endpoint for deleting files.

    Status codes:
    200 - If the file or directory was successfully deleted.
    403 - If the path is not inside of the root directory. This is a security measure to make sure
          the rest of the file system is not accessible.
    404 - If the file or directory is not found.
    """
    root_directory = current_app.config["root_directory"].resolve()
    full_file_path = (root_directory / path).resolve()

    if full_file_path != root_directory and root_directory not in full_file_path.parents:
        return (
            jsonify({"message": f"Cannot delete paths that are outside of the root directory: {path}"}),
            HTTPStatus.FORBIDDEN,
        )

    if not full_file_path.exists():
        return jsonify({"message": f"Could not find file path {path}"}), HTTPStatus.NOT_FOUND

    # Since Path.resolve() computes both relative paths (i.e. "..") and follows symlinks,
    # and since we only want to remove the source of the symlink, not the destination, we
    # need to check if the raw path is a symlink, and if so, use that instead of the resolved
    # path.
    full_file_path_or_link_source = (root_directory / path) if (root_directory / path).is_symlink() else full_file_path

    if full_file_path_or_link_source.is_dir():
        shutil.rmtree(full_file_path_or_link_source)
        return jsonify({"message": f"Deleted directory {path}"}), HTTPStatus.OK

    # In the unlikely case that 2 concurrent requests delete the file at the same time, we allow
    # the file to be missing here since it must have existed a few lines before, and the file not
    # existing at this point is not an issue.
    full_file_path_or_link_source.unlink(missing_ok=True)
    return jsonify({"message": f"Deleted file {path}"}), HTTPStatus.OK
