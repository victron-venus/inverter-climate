"""Stable package publication must distinguish absent releases from denied reads."""

import importlib.util
import io
import os

# Offline fixtures construct results; subprocess execution is mocked.
import subprocess  # nosec B404
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
SPEC = importlib.util.spec_from_file_location(
    "setuphelper_http_publication", SCRIPTS / "publish_setuphelper.py"
)
publisher = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC.loader.exec_module(publisher)
finally:
    sys.path.remove(str(SCRIPTS))


class StableLookupHTTPTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"RELEASE_REQUIRE_WORKFLOW_SCOPE": ""})
        environment.start()
        self.addCleanup(environment.stop)

    def response(self, status, body=b"{}"):
        def run(command, **_kwargs):
            self.assertEqual(command[:2], ["gh", "api"])
            self.assertIn("--include", command)
            self.assertEqual(command[command.index("--method") + 1], "GET")
            self.assertEqual(
                command[-2:], ["--", "repos/victron-venus/inverter-climate/releases/latest"]
            )
            return subprocess.CompletedProcess(
                command,
                int(status >= 400),
                f"HTTP/2.0 {status} Response\nContent-Type: application/json\r\n\r\n".encode()
                + body,
                b"gh: HTTP 404: misleading upstream diagnostic\n",
            )

        return run

    def test_genuinely_absent_stable_release_skips_without_publication(self):
        with patch.object(publisher.subprocess, "run", side_effect=self.response(404)) as run:
            with (
                patch.object(publisher, "verified_assets") as verify,
                redirect_stdout(io.StringIO()) as output,
            ):
                publisher.publish("victron-venus/inverter-climate", "", execute=False)
        run.assert_called_once()
        verify.assert_not_called()
        self.assertIn("publication skipped", output.getvalue())

    def test_denied_or_failed_lookup_is_not_an_absent_stable_release(self):
        for status in (401, 403, 429, 503):
            with (
                self.subTest(status=status),
                patch.object(
                    publisher.subprocess,
                    "run",
                    side_effect=self.response(status, b'{"errors":"HTTP 404"}'),
                ) as run,
                patch.object(publisher, "verified_assets") as verify,
            ):
                with self.assertRaises(publisher.ReleaseError) as error:
                    publisher.publish("victron-venus/inverter-climate", "", execute=False)
            self.assertFalse(error.exception.not_found)
            run.assert_called_once()
            verify.assert_not_called()

    def test_successful_lookup_returns_body_without_headers(self):
        with patch.object(
            publisher.subprocess,
            "run",
            side_effect=self.response(200, b'{"id":42,"tag_name":"v1.2.3"}'),
        ):
            value = publisher.SetupHelperGitHub("victron-venus/inverter-climate").api(
                publisher.LATEST_RELEASE_PATH
            )
        self.assertEqual(value, {"id": 42, "tag_name": "v1.2.3"})

    def test_explicit_tag_must_exist_as_latest_stable(self):
        with patch.object(publisher.subprocess, "run", side_effect=self.response(404)) as run:
            with patch.object(publisher, "verified_assets") as verify:
                with self.assertRaisesRegex(publisher.ReleaseError, "current latest stable"):
                    publisher.publish("victron-venus/inverter-climate", "v1.2.3", execute=False)
        run.assert_called_once()
        verify.assert_not_called()

    def test_write_to_lookup_endpoint_rejected_before_execution(self):
        with patch.object(publisher.subprocess, "run") as run:
            with self.assertRaises(publisher.ReleaseError):
                publisher.SetupHelperGitHub("victron-venus/inverter-climate").request(
                    publisher.LATEST_RELEASE_PATH, "POST", {}
                )
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
