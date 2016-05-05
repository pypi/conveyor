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

import os

import aiohttp
import aiohttp.web

from .views import redirect


async def session_close(app):
    await app["http.session"].close()


def configure():
    app = aiohttp.web.Application()

    # Pull configuration out of the environment
    app["settings"] = {
        "endpoint": os.environ["CONVEYOR_ENDPOINT"],
    }

    # Setup a HTTP session for our clients to share connections with and
    # register a shutdown callback to close the session.
    app["http.session"] = aiohttp.ClientSession(
        headers={"User-Agent": "conveyor"},
    )
    app.on_shutdown.append(session_close)

    # Add routes and views to our application
    app.router.add_route(
        "GET",
        "/packages/{python_version}/{project_l}/{project_name}/{filename}",
        redirect,
    )
    app.router.add_route(
        "HEAD",
        "/packages/{python_version}/{project_l}/{project_name}/{filename}",
        redirect,
    )

    return app
