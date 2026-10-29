"""One-way backup of a folder, and the app's own files, to Nextcloud over WebDAV.

Every file under the local folder is uploaded to ``<remote folder>/<same path>`` on the server
(``/remote.php/dav/files/<user>/...``), and each extra source (a file or folder the app needs
outside it: settings, event definitions, ...) to ``<remote folder>/_app/<its name>``, unless the server already has it with the same size and
modification time (uploads set it with ``X-OC-Mtime``, so the next sync skips them). Nothing is
deleted on either side. Pull goes the other way: each group of the backup (the recordings, each
``_app`` item) is downloaded to a local destination the user checked (``PullTarget``); files
the same size and time locally are skipped, and so are local files newer than the server's
(unless overwriting them is asked for). Log in with an app password (Nextcloud: Settings > Security > Devices &
sessions > Create new app password).
"""

from __future__ import annotations

import io
import os
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Callable
from urllib.parse import quote, unquote, urlparse

import requests

CHUNK = 1 << 20  # bytes read (and reported) at a time while uploading
TIMEOUT_S = 60.0
# Files not backed up (half-written ones).
SKIP_SUFFIXES = (".tmp", ".part")
# Remote folder (in the remote folder) of the extra sources.
APP_DIR = "_app"
DAV = "{DAV:}"
PROPFIND_BODY = (
    '<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop>'
    "<d:getcontentlength/><d:getlastmodified/><d:resourcetype/></d:prop></d:propfind>"
)


class Cancelled(Exception):
    pass


@dataclass
class NextcloudConfig:
    url: str = ""  # e.g. https://cloud.example.com
    user: str = ""
    password: str = ""  # app password
    remote_dir: str = "LeapXELA/demonstrations"
    local_dir: str = ""

    def dav_root(self) -> str:
        """WebDAV URL of the remote folder (no trailing slash)."""
        parts = [p for p in self.remote_dir.strip("/").split("/") if p]
        path = "/".join(quote(p) for p in [self.user, *parts])
        return f"{self.url.rstrip('/')}/remote.php/dav/files/{path}"


@dataclass
class SyncResult:
    uploaded: int = 0
    skipped: int = 0  # already on the server
    failed: list[tuple[str, str]] = field(default_factory=list)  # (path, why)
    bytes_sent: int = 0
    cancelled: bool = False


def _session(cfg: NextcloudConfig) -> requests.Session:
    s = requests.Session()
    s.auth = (cfg.user, cfg.password)
    s.headers["OCS-APIRequest"] = "true"
    return s


def _check(r: requests.Response, what: str) -> None:
    if r.status_code in (401, 403):
        raise RuntimeError(f"{what}: not allowed ({r.status_code}); check the user and app password")
    if r.status_code >= 400:
        raise RuntimeError(f"{what}: HTTP {r.status_code} {r.reason}")


def test_connection(cfg: NextcloudConfig) -> str:
    """Logs in and returns a short description; raises with the reason if it cannot."""
    if not cfg.url or not cfg.user or not cfg.password:
        raise RuntimeError("Fill in the server, user and app password")
    root = f"{cfg.url.rstrip('/')}/remote.php/dav/files/{quote(cfg.user)}"
    r = _session(cfg).request(
        "PROPFIND", root, data=PROPFIND_BODY, headers={"Depth": "0"}, timeout=TIMEOUT_S
    )
    _check(r, "Log in")
    return f"Logged in to {urlparse(cfg.url).netloc} as {cfg.user}"


def _propfind(s: requests.Session, url: str) -> list[tuple[str, bool, int, float]] | None:
    """(href path, is folder, size, mtime) of a folder and its children; None if it is
    missing."""
    r = s.request("PROPFIND", url + "/", data=PROPFIND_BODY, headers={"Depth": "1"},
                  timeout=TIMEOUT_S)
    if r.status_code == 404:
        return None
    _check(r, f"List {url}")
    out = []
    for resp in ET.fromstring(r.content).iter(f"{DAV}response"):
        href = unquote(urlparse(resp.findtext(f"{DAV}href", "")).path).rstrip("/")
        # A folder has no length: servers answer it in a propstat of its own (404).
        props = resp.findall(f"{DAV}propstat/{DAV}prop")
        if not props:
            continue
        folder = any(p.find(f"{DAV}resourcetype/{DAV}collection") is not None for p in props)
        size = int(next((p.findtext(f"{DAV}getcontentlength") for p in props
                         if p.findtext(f"{DAV}getcontentlength")), 0))
        modified = next((p.findtext(f"{DAV}getlastmodified") for p in props
                         if p.findtext(f"{DAV}getlastmodified")), None)
        mtime = parsedate_to_datetime(modified).timestamp() if modified else 0.0
        out.append((href, folder, size, mtime))
    return out


def remote_files(s: requests.Session, root: str) -> tuple[dict[str, tuple[int, float]], set[str]]:
    """{relative path: (size, mtime)} of the files under ``root`` and its folders' relative
    paths ("" is ``root``; empty if it does not exist)."""
    base = unquote(urlparse(root).path).rstrip("/")
    files: dict[str, tuple[int, float]] = {}
    folders: set[str] = set()
    pending = [""]
    while pending:
        rel = pending.pop()
        url = root + "".join("/" + quote(p) for p in rel.split("/") if p)
        entries = _propfind(s, url)
        if entries is None:
            continue
        folders.add(rel)
        for href, folder, size, mtime in entries:
            child = href[len(base):].strip("/") if href.startswith(base) else None
            if child is None or child == rel:
                continue
            if folder:
                pending.append(child)
            else:
                files[child] = (size, mtime)
    return files, folders


def local_files(local_dir: str) -> dict[str, tuple[int, float]]:
    """{relative path (with /): (size, mtime)} of the files under ``local_dir``."""
    return {rel: (size, mtime) for rel, (_, size, mtime) in _gather(local_dir, "").items()}


def _gather(local: str, prefix: str) -> dict[str, tuple[str, int, float]]:
    """{remote relative path: (local path, size, mtime)} of a file, or of the files under a
    folder, sent under ``prefix`` (a folder's files keep their path in it)."""
    out = {}
    if os.path.isfile(local):
        st = os.stat(local)
        out["/".join(p for p in (prefix, os.path.basename(local)) if p)] = (
            local, st.st_size, st.st_mtime
        )
        return out
    for dirpath, _, names in os.walk(local):
        for name in names:
            if name.endswith(SKIP_SUFFIXES):
                continue
            path = os.path.join(dirpath, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            rel = os.path.relpath(path, local).replace(os.sep, "/")
            out["/".join(p for p in (prefix, rel) if p)] = (path, st.st_size, st.st_mtime)
    return out


# A file's content -> what is uploaded instead (e.g. without a password).
Redact = Callable[[bytes], bytes]


def sources_files(
    local_dir: str, extras: list[tuple[str, str]], redact: dict[str, Redact] | None = None,
) -> dict[str, tuple[str | bytes, int, float]]:
    """{remote relative path: (local path, size, mtime)}: the local folder's files, and each
    extra (local file or folder, name) under ``APP_DIR``/name (a file: ``APP_DIR``/name/its
    file name); extras that do not exist are left out. A file in ``redact`` (by its real
    path) is sent as what its function makes of it: (that content, its size, mtime)."""
    out = _gather(local_dir, "")
    for local, name in extras:
        if os.path.exists(local):
            out.update(_gather(local, f"{APP_DIR}/{name}"))
    by_path = {os.path.realpath(k): f for k, f in (redact or {}).items()}
    for rel, (path, _, mtime) in out.items():
        f = by_path.get(os.path.realpath(path))
        if f is not None:
            with open(path, "rb") as fh:
                data = f(fh.read())
            out[rel] = (data, len(data), mtime)
    return out


def needs_upload(local: tuple[int, float], remote: tuple[int, float] | None) -> bool:
    return remote is None or remote[0] != local[0] or abs(remote[1] - int(local[1])) > 1.0


class _Reader:
    """A file read in ``CHUNK``s for ``requests`` (which sends its ``len`` as
    Content-Length), reporting each chunk and stopping when ``stop`` is set."""

    def __init__(self, path: str | bytes, size: int, sent: Callable[[int], None],
                 stop: threading.Event) -> None:
        self._f = io.BytesIO(path) if isinstance(path, bytes) else open(path, "rb")
        self._size, self._sent, self._stop = size, sent, stop

    def __len__(self) -> int:
        return self._size

    def read(self, n: int = -1) -> bytes:
        if self._stop.is_set():
            raise Cancelled()
        data = self._f.read(CHUNK if n is None or n < 0 else min(n, CHUNK))
        self._sent(len(data))
        return data

    def close(self) -> None:
        self._f.close()


def sync(
    cfg: NextcloudConfig,
    progress: Callable[[int, int, int, int, str], None],
    stop: threading.Event,
    extras: list[tuple[str, str]] = (),
    redact: dict[str, Redact] | None = None,
) -> SyncResult:
    """Uploads what the server does not have yet, of the local folder and the ``extras``
    ((local file or folder, name under ``APP_DIR``); files in ``redact`` are sent as its
function makes them). ``progress(bytes done, bytes to send,
    files done, files to send, current file)`` is called as it goes."""
    if not os.path.isdir(cfg.local_dir):
        raise RuntimeError(f"No local folder {cfg.local_dir}")
    s = _session(cfg)
    root = cfg.dav_root()
    progress(0, 0, 0, 0, "listing the server...")
    remote, folders = remote_files(s, root)
    local = sources_files(cfg.local_dir, list(extras), redact)
    todo = sorted(rel for rel, (_, *info) in local.items()
                  if needs_upload(tuple(info), remote.get(rel)))
    result = SyncResult(skipped=len(local) - len(todo))
    total = sum(local[rel][1] for rel in todo)
    done = 0

    def ensure_folder(rel: str) -> None:
        parts = [p for p in rel.split("/") if p]
        # The remote folder itself may be several levels deep, created from the user's root.
        base = [p for p in cfg.remote_dir.strip("/").split("/") if p]
        user_root = f"{cfg.url.rstrip('/')}/remote.php/dav/files/{quote(cfg.user)}"
        for i in range(1, len(base) + 1):
            if "" not in folders:
                url = user_root + "".join("/" + quote(p) for p in base[:i])
                r = s.request("MKCOL", url, timeout=TIMEOUT_S)
                if r.status_code not in (201, 405):  # 405: it exists
                    _check(r, f"Create {'/'.join(base[:i])}")
        folders.add("")
        for i in range(1, len(parts) + 1):
            sub = "/".join(parts[:i])
            if sub in folders:
                continue
            r = s.request("MKCOL", root + "".join("/" + quote(p) for p in parts[:i]),
                          timeout=TIMEOUT_S)
            if r.status_code not in (201, 405):
                _check(r, f"Create {sub}")
            folders.add(sub)

    for i, rel in enumerate(todo):
        if stop.is_set():
            result.cancelled = True
            break
        path, size, mtime = local[rel]
        progress(done, total, i, len(todo), rel)
        start = done

        def sent(n: int, i=i, rel=rel) -> None:
            nonlocal done
            done += n
            progress(done, total, i, len(todo), rel)

        try:
            ensure_folder(os.path.dirname(rel))
            body = _Reader(path, size, sent, stop)
            try:
                r = s.put(
                    root + "".join("/" + quote(p) for p in rel.split("/")), data=body,
                    headers={"X-OC-Mtime": str(int(mtime))}, timeout=TIMEOUT_S,
                )
            finally:
                body.close()
            _check(r, f"Upload {rel}")
            result.uploaded += 1
            result.bytes_sent += size
        except Cancelled:
            result.cancelled = True
            break
        except (OSError, RuntimeError, requests.RequestException) as e:
            result.failed.append((rel, str(e)))
        done = start + size  # whatever was counted for it, as if sent
    progress(done, total, result.uploaded + len(result.failed), len(todo), "")
    return result


# ---- Pull ---------------------------------------------------------------------------------


@dataclass
class PullTarget:
    """A group of the backup and where it goes: the remote files under ``prefix`` ("" is the
    recordings, i.e. everything not under ``APP_DIR``) go to ``dest``, keeping their path
    under ``prefix``; with ``is_file`` the group is one file and ``dest`` is that file."""

    label: str
    prefix: str
    dest: str
    is_file: bool = False


@dataclass
class PullFile:
    rel: str  # remote relative path
    dest: str  # local path
    size: int
    mtime: float
    state: str  # "new", "changed", "local newer" or "same"


@dataclass
class PullResult:
    downloaded: int = 0
    skipped: int = 0  # the same locally
    kept_newer: int = 0  # local files newer than the server's, left as they are
    failed: list[tuple[str, str]] = field(default_factory=list)
    bytes_received: int = 0
    cancelled: bool = False


def list_backup(cfg: NextcloudConfig) -> dict[str, tuple[int, float]]:
    """{relative path: (size, mtime)} of every file in the remote folder."""
    return remote_files(_session(cfg), cfg.dav_root())[0]


def _in_group(rel: str, prefix: str) -> str | None:
    """``rel`` relative to the group ``prefix`` (None if not in it)."""
    if not prefix:
        return None if rel == APP_DIR or rel.startswith(APP_DIR + "/") else rel
    if rel.startswith(prefix + "/"):
        return rel[len(prefix) + 1:]
    return None


def plan_pull(
    remote: dict[str, tuple[int, float]], targets: list[PullTarget],
    redact: dict[str, Redact] | None = None,
) -> list[PullFile]:
    """Where each remote file of the ``targets`` goes and whether it needs downloading; a
    local file in ``redact`` is compared as Sync sent it (so leaving its password out does
    not make it look changed)."""
    by_path = {os.path.realpath(k): f for k, f in (redact or {}).items()}
    out = []
    for target in targets:
        for rel, (size, mtime) in sorted(remote.items()):
            sub = _in_group(rel, target.prefix)
            if sub is None:
                continue
            dest = (os.path.expanduser(target.dest) if target.is_file
                    else os.path.join(os.path.expanduser(target.dest), *sub.split("/")))
            try:
                st = os.stat(dest)
                local_size = st.st_size
                f = by_path.get(os.path.realpath(dest))
                if f is not None:
                    with open(dest, "rb") as fh:
                        local_size = len(f(fh.read()))
            except (OSError, ValueError):
                state = "new" if not os.path.exists(dest) else "changed"
            else:
                if not needs_upload((local_size, st.st_mtime), (size, mtime)):
                    state = "same"
                elif st.st_mtime > mtime + 1.0:
                    state = "local newer"
                else:
                    state = "changed"
            out.append(PullFile(rel, dest, size, mtime, state))
            if target.is_file:
                break  # one file
    return out


def pull(
    cfg: NextcloudConfig,
    files: list[PullFile],
    progress: Callable[[int, int, int, int, str], None],
    stop: threading.Event,
    overwrite_newer: bool = False,
) -> PullResult:
    """Downloads the planned ``files`` that are new or changed (and local newer ones with
    ``overwrite_newer``), each to a temporary file then into place, with the server's
    modification time (so the next Sync does not send it back)."""
    s = _session(cfg)
    root = cfg.dav_root()
    get = {"new", "changed", "local newer"} if overwrite_newer else {"new", "changed"}
    todo = [f for f in files if f.state in get]
    result = PullResult(
        skipped=sum(f.state == "same" for f in files),
        kept_newer=0 if overwrite_newer else sum(f.state == "local newer" for f in files),
    )
    total = sum(f.size for f in todo)
    done = 0
    for i, f in enumerate(todo):
        if stop.is_set():
            result.cancelled = True
            break
        progress(done, total, i, len(todo), f.dest)
        start = done
        tmp = f.dest + ".part"
        try:
            os.makedirs(os.path.dirname(f.dest) or ".", exist_ok=True)
            url = root + "".join("/" + quote(p) for p in f.rel.split("/"))
            with s.get(url, stream=True, timeout=TIMEOUT_S) as r:
                _check(r, f"Download {f.rel}")
                with open(tmp, "wb") as out:
                    for chunk in r.iter_content(CHUNK):
                        if stop.is_set():
                            raise Cancelled()
                        out.write(chunk)
                        done += len(chunk)
                        progress(done, total, i, len(todo), f.dest)
            os.utime(tmp, (f.mtime, f.mtime))
            os.replace(tmp, f.dest)
            result.downloaded += 1
            result.bytes_received += f.size
        except Cancelled:
            result.cancelled = True
            break
        except (OSError, RuntimeError, requests.RequestException) as e:
            result.failed.append((f.rel, str(e)))
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        done = start + f.size
    progress(done, total, result.downloaded + len(result.failed), len(todo), "")
    return result
