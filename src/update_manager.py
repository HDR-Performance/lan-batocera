import json
import os
import re
import subprocess
import urllib.request


REPOSITORY = "HDR-Performance/lan-batocera"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
INSTALLER_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/"
    f"{REPOSITORY}/v{{version}}/standalone-install.sh"
)
SEMANTIC_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
NETWORK_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 1024 * 1024
USER_AGENT = f"LAN-Batocera-Updater (+https://github.com/{REPOSITORY})"


def version_tuple(version: str) -> tuple[int, int, int]:
    if not SEMANTIC_VERSION.fullmatch(version):
        raise ValueError("GitHub returned an invalid release version.")
    return tuple(int(part) for part in version.split("."))


class UpdateManager:
    def __init__(self, current_version, status_path="/userdata/system/lan-batocera-update.json",
                 temporary_root="/tmp", log_path="/userdata/system/logs/lan-batocera-update.log"):
        self.current_version = current_version
        self.status_path = status_path
        self.temporary_root = temporary_root
        self.log_path = log_path

    def check(self, opener=urllib.request.urlopen) -> dict:
        request = urllib.request.Request(
            LATEST_RELEASE_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
        )
        with opener(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise RuntimeError("GitHub's release response was unexpectedly large.")
        release = json.loads(payload)
        latest_version = str(release.get("tag_name", "")).removeprefix("v")
        current = version_tuple(self.current_version)
        latest = version_tuple(latest_version)
        return {
            "currentVersion": self.current_version,
            "latestVersion": latest_version,
            "updateAvailable": latest > current,
            "releaseUrl": str(release.get("html_url", "")),
            "releaseName": str(release.get("name", "")),
        }

    def status(self) -> dict:
        try:
            with open(self.status_path, encoding="utf-8") as status_file:
                status = json.load(status_file)
        except (OSError, ValueError):
            return {"status": "idle", "currentVersion": self.current_version}
        status["currentVersion"] = self.current_version
        if status.get("targetVersion") == self.current_version:
            status["status"] = "complete"
        return status

    def start(self, target_version: str, opener=urllib.request.urlopen,
              process_launcher=subprocess.Popen) -> dict:
        if version_tuple(target_version) <= version_tuple(self.current_version):
            raise ValueError("The selected release is not newer than the installed version.")

        latest = self.check(opener)
        if latest["latestVersion"] != target_version or not latest["updateAvailable"]:
            raise ValueError("The selected release is not GitHub's current stable release.")

        installer_path = os.path.join(self.temporary_root, "lan-batocera-update-install.sh")
        runner_path = os.path.join(self.temporary_root, "lan-batocera-update-runner.sh")
        installer_url = INSTALLER_URL_TEMPLATE.format(version=target_version)
        request = urllib.request.Request(installer_url, headers={"User-Agent": USER_AGENT})
        with opener(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            installer = response.read(MAX_RESPONSE_BYTES + 1)
        expected_version = f'LAN_BATOCERA_VERSION="{target_version}"'.encode()
        if len(installer) > MAX_RESPONSE_BYTES or expected_version not in installer:
            raise RuntimeError("The tagged installer failed version validation.")

        self._write_file(installer_path, installer, 0o700)
        runner = self._runner_script(installer_path, self.log_path, target_version)
        self._write_file(runner_path, runner.encode(), 0o700)
        self._write_status({"status": "installing", "targetVersion": target_version})
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "ab") as log_file:
            process_launcher([runner_path], stdin=subprocess.DEVNULL, stdout=log_file,
                             stderr=subprocess.STDOUT, start_new_session=True)
        return self.status()

    def _runner_script(self, installer_path: str, log_path: str, target_version: str) -> str:
        status_directory = os.path.dirname(self.status_path)
        return f'''#!/bin/sh
set -u
if "{installer_path}" >> "{log_path}" 2>&1; then
  result='{{"status":"complete","targetVersion":"{target_version}"}}'
else
  result='{{"status":"failed","targetVersion":"{target_version}","error":"Installation failed. Review the update log over SSH."}}'
fi
mkdir -p "{status_directory}"
printf '%s\n' "$result" > "{self.status_path}.tmp"
mv "{self.status_path}.tmp" "{self.status_path}"
'''

    def _write_status(self, status: dict) -> None:
        os.makedirs(os.path.dirname(self.status_path), exist_ok=True)
        temporary_path = f"{self.status_path}.tmp"
        with open(temporary_path, "w", encoding="utf-8") as status_file:
            json.dump(status, status_file)
        os.replace(temporary_path, self.status_path)

    @staticmethod
    def _write_file(path: str, content: bytes, mode: int) -> None:
        with open(path, "wb") as output:
            output.write(content)
        os.chmod(path, mode)
