# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

from conveyor.views import _normalize_filename


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename, expected",
    [
        ("Flask-Common-0.2.0.tar.gz", "flask-common-0.2.tar.gz"),
        ("websocket_client-0.52.0.tar.gz", "websocket-client-0.52.tar.gz"),
        ("Sphinx-7.1.1.tar.gz", "sphinx-7.1.1.tar.gz"),
        ("Foo_Bar-24.0.0.0.tar.gz", "foo-bar-24.tar.gz"),
        ("Foo_Bar-24.0.0.0-py3-none-any.whl", "foo-bar-24-py3-none-any.whl"),
        ("foo-24-py3-none-any.whl", "foo-24-py3-none-any.whl"),
        (
            "spam-1.0-420yolo-py3-none-any.whl",
            "spam-1-420yolo-py3-none-any.whl",
        ),  # Build tag
        ("Foo_bar-24.0.0.0.zip", "foo-bar-24.zip"),
    ],
)
async def test_normalize_filename(filename, expected):
    result = await _normalize_filename(filename)

    assert result == expected
