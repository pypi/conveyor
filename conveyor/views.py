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

import mimetypes

import urllib.parse

import botocore

from aiohttp import web
from botocore.config import Config as BotoCoreConfig
from packaging.utils import parse_sdist_filename, parse_wheel_filename
from packaging.utils import canonicalize_name, canonicalize_version

ANON_CONFIG = BotoCoreConfig(signature_version=botocore.UNSIGNED)


async def health(request):
    return web.Response(status=200)


async def not_found(request):
    return web.Response(status=404)


async def _normalize_filename(filename):
    if filename.endswith(".whl"):
        name, ver, build, tags = parse_wheel_filename(filename)
        return (
            "-".join(
                [
                    canonicalize_name(name),
                    canonicalize_version(ver),
                ]
                + (["".join(str(x) for x in build)] if build else [])
                + [
                    "-".join(str(x) for x in tags),
                ]
            )
            + ".whl"
        )
    elif filename.endswith(".tar.gz"):
        name, ver = parse_sdist_filename(filename)
        return (
            "-".join(
                [
                    canonicalize_name(name),
                    canonicalize_version(ver),
                ]
            )
            + ".tar.gz"
        )
    elif filename.endswith(".zip"):
        name, ver = parse_sdist_filename(filename)
        return (
            "-".join(
                [
                    canonicalize_name(name),
                    canonicalize_version(ver),
                ]
            )
            + ".zip"
        )
    else:
        return filename


async def redirect(request):
    python_version = request.match_info["python_version"]
    project_l = request.match_info["project_l"]
    project_name = request.match_info["project_name"]
    filename = request.match_info["filename"]

    # If the letter bucket doesn't match the first letter of the project, then
    # there is no point to going any further since it will be a 404 regardless.
    # Allow specifiying the exact first character of the actual filename (which
    # might not be lowercase, to maintain backwards compatibility
    if project_l != project_name[0].lower() and project_l != project_name[0]:
        return web.Response(status=404, headers={"Reason": "Incorrect project bucket"})

    # If the filename we're looking for is a signature, then we'll need to turn
    # this into the *real* filename and a note that we're looking for the
    # signature.
    if filename.endswith(".asc"):
        filename = filename[:-4]
        signature = True
    else:
        signature = False

    json_url = urllib.parse.urljoin(
        request.app["settings"]["endpoint"],
        "/pypi/{}/json".format(project_name),
    )

    async with request.app["http.session"].get(json_url) as resp:
        if 400 <= resp.status < 500:
            return web.Response(status=resp.status)
        elif 500 <= resp.status < 600:
            return web.Response(status=503)

        # It shouldn't be possible to get a status code other than 200 here.
        assert resp.status == 200

        # Get the JSON data from our request.
        data = await resp.json()

    # Look at all of the files listed in the JSON response, and see if one
    # matches our filename and Python version. If we find one, then return a
    # 302 redirect to that URL.
    for release in data.get("releases", {}).values():
        for file_ in release:
            if (
                # Prefer that the normalized filename has been specified
                _normalize_filename(file_["filename"]) == filename
                # But also allow specifying the exact filename, to maintain
                # backwards compatiblity
                or file_["filename"] == filename
            ) and file_["python_version"] == python_version:
                # If we've found our filename, but we were actually looking for
                # the *signature* of that file, then we need to check if it has
                # a signature associated with it, and if so redirect to that,
                # and if not return a 404.
                if signature:
                    if file_.get("has_sig"):
                        return web.Response(
                            status=302,
                            headers={
                                "Location": file_["url"] + ".asc",
                                "Cache-Control": "max-age=604800, public",
                            },
                        )
                    else:
                        return web.Response(
                            status=404, headers={"Reason": "missing signature file"}
                        )
                # If we've found our filename, then we'll redirect to it.
                else:
                    return web.Response(
                        status=302,
                        headers={
                            "Location": file_["url"],
                            "Cache-Control": "max-age=604800, public",
                        },
                    )

    # If we've gotten to this point, it means that we couldn't locate an url
    # to redirect to so we'll jsut 404.
    return web.Response(status=404, headers={"Reason": "no file found"})


async def fetch_key(s3, request, bucket, key):
    resp = await s3.get_object(
        Bucket=bucket,
        Key=key,
    )
    return resp


async def index(request):
    bucket = request.app["settings"]["docs_bucket"]
    session = request.app["boto.session"]()
    path = "index.html"

    async with session.create_client("s3", config=ANON_CONFIG) as s3:
        try:
            key = await fetch_key(s3, request, bucket, path)
        except botocore.exceptions.ClientError:
            return web.Response(status=404)

        content_type, content_encoding = mimetypes.guess_type(path)
        response = web.StreamResponse(status=200, reason="OK")
        response.content_type = content_type
        response.content_encoding = content_encoding
        body = key["Body"]
        await response.prepare(request)
        while True:
            data = await body.read(4096)
            await response.write(data)
            await response.drain()
            if not data:
                body.close()
                break

        return response


async def documentation_top(request):
    project_name = request.match_info["project_name"]
    return web.HTTPMovedPermanently(location=f"/{project_name}/")


async def documentation(request):
    project_name = request.match_info["project_name"]
    path = request.match_info.get("path", "")

    if project_name in request.app["redirects"]:
        location = request.app["redirects"][project_name]["base_uri"]
        if request.app["redirects"][project_name]["include_path"]:
            location = f"{location}/{path}"
        return web.Response(
            status=302,
            headers={
                "Location": location,
            },
        )

    path = f"{project_name}/{path}"
    if path.endswith("/"):
        path += "index.html"

    bucket = request.app["settings"]["docs_bucket"]
    session = request.app["boto.session"]()

    async with session.create_client("s3", config=ANON_CONFIG) as s3:
        try:
            key = await fetch_key(s3, request, bucket, path)
        except botocore.exceptions.ClientError:
            try:
                key = await fetch_key(s3, request, bucket, path + "/index.html")
            except botocore.exceptions.ClientError:
                return web.Response(status=404)
            else:
                return web.HTTPMovedPermanently(location="/" + path + "/")

        content_type, content_encoding = mimetypes.guess_type(path)
        response = web.StreamResponse(status=200, reason="OK")
        response.content_type = content_type
        response.content_encoding = content_encoding
        body = key["Body"]
        await response.prepare(request)
        while True:
            data = await body.read(4096)
            await response.write(data)
            await response.drain()
            if not data:
                body.close()
                break

        return response
