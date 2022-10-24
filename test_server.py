import base64
from http import HTTPStatus
import os
from pathlib import Path
import tempfile
from typing import Iterable

import pytest

from app import create_app


@pytest.fixture
def root_directory() -> Iterable[Path]:
    with tempfile.TemporaryDirectory() as root_directory:
        yield Path(root_directory)


@pytest.fixture
def test_client(root_directory):
    app = create_app()
    app.config["root_directory"] = root_directory
    return app.test_client()


def test_get_path_outside_of_root_returns_forbidden(test_client):
    illegal_path = "../some_file.txt"
    response = test_client.get(f"/{illegal_path}")
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json == {"message": f"Cannot access paths that are outside of the root directory: {illegal_path}"}


def test_get_non_existant_file_returns_404(test_client):
    file_name = "does-not-exist.txt"
    response = test_client.get(f"/{file_name}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json == {"message": f"Could not find file path {file_name}"}


def test_get_empty_directory_returns_empty_list(test_client):
    response = test_client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"directory_contents": []}


def test_get_directory_returns_list_of_files(test_client, root_directory):
    file1_name = "foo.txt"
    file1_contents = "file 1 contents"
    file2_name = "bar.txt"
    file2_contents = "file 2 contents"
    with open(root_directory / file1_name, "w+") as file:
        file.write(file1_contents)

    with open(root_directory / file2_name, "w+") as file:
        file.write(file2_contents)

    response = test_client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert response.json == {
        "directory_contents": [
            {
                "file_name": file1_name,
                "owner": os.getlogin(),
                "size_in_bytes": len(file1_contents),
                "permissions_octal": "644",
                "permissions_human": "-rw-r--r--",
            },
            {
                "file_name": file2_name,
                "owner": os.getlogin(),
                "size_in_bytes": len(file2_contents),
                "permissions_octal": "644",
                "permissions_human": "-rw-r--r--",
            },
        ],
    }


def test_get_file_returns_file_contents(test_client, root_directory):
    file_name = "foo.txt"
    file_contents = "some file contents"
    with open(root_directory / file_name, "w+") as file:
        file.write(file_contents)
    response = test_client.get(f"/{file_name}")
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"file_contents": file_contents}


def test_post_path_outside_of_root_returns_forbidden(test_client, root_directory):
    illegal_path = "../some_file.txt"
    response = test_client.post(f"/{illegal_path}", json={"contents": "contents"})
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json == {"message": f"Cannot access paths that are outside of the root directory: {illegal_path}"}
    full_file_path = (root_directory / illegal_path).resolve()
    assert not full_file_path.exists()


def test_post_existing_file_returns_bad_request(test_client, root_directory):
    file_name = "foo.txt"
    file_contents = "foo contents"
    updated_contents = "foo contents"
    test_client.post(f"/{file_name}", json={"contents": file_contents})
    response = test_client.post(f"/{file_name}", json={"contents": updated_contents})
    assert response.json == {
        "message": f"Path already exists. If you want to override, please use PUT instead: {file_name}"
    }
    assert response.status_code == HTTPStatus.BAD_REQUEST

    full_file_path = root_directory / file_name
    assert full_file_path.exists()
    assert full_file_path.read_text() == file_contents


def test_post_new_file_without_contents_returns_bad_request(test_client, root_directory):
    file_name = "foo.txt"
    response = test_client.post(f"/{file_name}", json={})
    assert response.json == {"message": "No file contents specified"}
    assert response.status_code == HTTPStatus.BAD_REQUEST

    full_file_path = root_directory / file_name
    assert not full_file_path.exists()


def test_post_new_file_creates_file_with_contents(test_client, root_directory):
    file_name = "foo.txt"
    file_contents = "foo contents"
    response = test_client.post(f"/{file_name}", json={"contents": file_contents})
    assert response.json == {"message": f"Created file {file_name}"}
    assert response.status_code == HTTPStatus.OK

    full_file_path = root_directory / file_name
    assert full_file_path.exists()
    assert full_file_path.read_text() == file_contents


def test_post_new_file_creates_file_with_base64_contents(test_client, root_directory):
    file_name = "foo.txt"
    file_contents = b"\x00"
    base64_contents = base64.b64encode(file_contents).decode("utf-8")
    response = test_client.post(f"/{file_name}", json={"base64_contents": base64_contents})
    assert response.json == {"message": f"Created file {file_name}"}
    assert response.status_code == HTTPStatus.OK

    full_file_path = root_directory / file_name
    assert full_file_path.exists()
    assert full_file_path.read_bytes() == file_contents


def test_put_new_file_creates_file_with_contents(test_client, root_directory):
    file_name = "foo.txt"
    file_contents = "foo contents"
    response = test_client.put(f"/{file_name}", json={"contents": file_contents})
    assert response.json == {"message": f"Created file {file_name}"}
    assert response.status_code == HTTPStatus.OK

    full_file_path = root_directory / file_name
    assert full_file_path.exists()
    assert full_file_path.read_text() == file_contents


def test_put_existing_file_updates_file_with_contents(test_client, root_directory):
    file_name = "foo.txt"
    file_contents = "foo contents"
    updated_file_contents = "updated foo contents"
    # create the file
    test_client.post(f"/{file_name}", json={"contents": file_contents})
    # update the file
    response = test_client.put(f"/{file_name}", json={"contents": updated_file_contents})
    assert response.json == {"message": f"Created file {file_name}"}
    assert response.status_code == HTTPStatus.OK

    full_file_path = root_directory / file_name
    assert full_file_path.exists()
    assert full_file_path.read_text() == updated_file_contents


def test_delete_file_deletes_the_file(test_client, root_directory):
    file_name = "foo.txt"
    file_contents = "foo contents"
    # create the file
    test_client.post(f"/{file_name}", json={"contents": file_contents})
    # delete the file
    response = test_client.delete(f"/{file_name}")
    assert response.json == {"message": f"Deleted file {file_name}"}
    assert response.status_code == HTTPStatus.OK

    full_file_path = root_directory / file_name
    assert not full_file_path.exists()


def test_delete_file_deletes_a_symlink_but_not_source_file(test_client, root_directory):
    file_name = "foo.txt"
    file_contents = "foo contents"
    full_source_path = root_directory / file_name
    # create destination file
    test_client.post(f"/{file_name}", json={"contents": file_contents})

    lint_file_name = "foo_link.txt"
    full_destination_path = root_directory / lint_file_name
    os.symlink(full_source_path, full_destination_path)
    # delete the file
    response = test_client.delete(f"/{lint_file_name}")
    assert response.json == {"message": f"Deleted file {lint_file_name}"}
    assert response.status_code == HTTPStatus.OK

    assert not full_destination_path.exists()
    assert full_source_path.exists()


def test_delete_file_deletes_a_directory(test_client, root_directory):
    directory_name = "my_dir"
    file_name = "foo.txt"
    file_contents = "foo contents"
    # create the file
    test_client.post(f"/{directory_name}/{file_name}", json={"contents": file_contents})
    # delete the file
    response = test_client.delete(f"/{directory_name}")
    assert response.json == {"message": f"Deleted directory {directory_name}"}
    assert response.status_code == HTTPStatus.OK

    full_file_path = root_directory / directory_name
    assert not full_file_path.exists()
