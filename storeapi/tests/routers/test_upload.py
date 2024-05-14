import contextlib
import os
import pathlib
import tempfile

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture


@pytest.fixture()
def sample_image(fs) -> pathlib.Path:
    path = (pathlib.Path(__file__).parent / "assets" / "my_file.png").resolve()
    fs.create_file(path)
    return path


@pytest.fixture(autouse=True)
async def mock_b2_upload_file(mocker: MockerFixture):
    return mocker.patch(
        "storeapi.routers.upload.b2_upload_file", return_value="https://fakeurl.com"
    )


@pytest.fixture(autouse=True)
async def aiofiles_mock_open(mocker: MockerFixture, fs):
    mock_open = mocker.patch("aiofiles.open")

    @contextlib.asynccontextmanager
    async def async_file_open(filename: str, mode: str = "r"):
        out_fs_mock = mocker.AsyncMock(name=f"async_file_open:{filename!r}/{mode!r}")

        with open(filename, mode=mode) as fin:
            out_fs_mock.read.side_effect = fin.read
            out_fs_mock.write.side_effect = fin.write
            yield out_fs_mock

    mock_open.side_effect = async_file_open
    return mock_open


async def call_upload_endpoint(asynch_client: AsyncClient, token: str, sample_image: pathlib.Path):
    return await asynch_client.post(
        '/upload',
        files={"file": open(sample_image, "rb")},
        headers={"Authorization": f"Bearer {token}"}
    )


@pytest.mark.anyio
async def test_upload_image(async_client: AsyncClient, logged_in_token: str, sample_image: pathlib):
    response = await call_upload_endpoint(async_client, logged_in_token, sample_image)

    assert response.status_code == 201
    assert response.json()['file_url'] == "https://fakeurl.com"


@pytest.mark.anyio
async def test_temp_file_removed_after_upload(
        async_client: AsyncClient, logged_in_token: str, sample_image: pathlib.Path, mocker: MockerFixture
):
    named_temp_file_spy = mocker.spy(tempfile, "NamedTemporaryFile")
    response = await call_upload_endpoint(async_client, logged_in_token, sample_image)

    assert response.status_code == 201

    created_temp_file = named_temp_file_spy.spy_return

    assert not os.path.exists(created_temp_file.name)
