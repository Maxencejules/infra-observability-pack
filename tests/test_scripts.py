"""Execute shell entry points with fake local tools; never a real cluster."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")

@unittest.skipUnless(BASH, "Bash required")
class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="script-check-", dir=ROOT/".local")
        self.directory = Path(self.scratch.name)
        self.bin = self.directory/"bin"
        self.bin.mkdir()
        self.log = self.directory/"calls.txt"
        for command in ("kubectl","docker","kind"):
            script = self.bin/command
            script.write_text("""#!/usr/bin/env bash
printf '%s\\n' """ + command + """' '"$*" >> "$CALL_LOG"
if [[ "$1 $2" == "get clusters" ]]; then printf '%s\\n' "${MOCK_CLUSTERS:-portfolio-observability}"; fi
""", encoding="utf-8", newline="\n")
            script.chmod(0o755)
        self.env = {**os.environ, "CALL_LOG":str(self.log), "CLUSTER_NAME":"portfolio-observability",
                    "KUBECONFIG_PATH":str(self.directory/"private-config")}

    def tearDown(self):
        self.scratch.cleanup()

    def run_script(self, name, args=(), extra=None):
        # Git Bash's own /usr/bin must precede Windows System32/bash.exe (WSL).
        env = {**self.env, **(extra or {}), "TEST_BIN":str(self.bin), "TEST_SCRIPT":str(ROOT/name)}
        return subprocess.run([BASH,"-c",'export PATH="$(cygpath -u "$TEST_BIN" 2>/dev/null || printf "%s" "$TEST_BIN"):/usr/bin:$PATH"; exec "$BASH" "$TEST_SCRIPT" "$@"',"test",*args],
                              env=env,capture_output=True,text=True,timeout=90)

    def test_every_deploy_operation_has_explicit_private_context(self):
        result = self.run_script("scripts/deploy-all.sh")
        self.assertEqual(result.returncode,0,result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertGreater(len(calls),5)
        for call in calls:
            self.assertTrue(call.startswith("kubectl --kubeconfig "),call)
            self.assertIn("--context kind-portfolio-observability ",call)
        self.assertTrue(any("--dry-run=server -k " in call for call in calls))

    def test_existing_cluster_exports_only_private_kubeconfig(self):
        result = self.run_script("scripts/setup-cluster.sh")
        self.assertEqual(result.returncode,0,result.stderr)
        calls = self.log.read_text()
        self.assertIn("kind export kubeconfig --name portfolio-observability --kubeconfig",calls)
        self.assertNotIn("kind create",calls)
        self.assertIn("--context kind-portfolio-observability cluster-info",calls)

    def test_app_builds_preserve_caller_files(self):
        app_paths = [self.directory/name for name in ("procurement app","integrations app")]
        before = {}
        for path in app_paths:
            path.mkdir()
            for name,content in (("Dockerfile",b"FROM caller-base\n"),("requirements.txt",b"caller-package\n"),("main.py",b"caller_source = True\n")):
                file = path/name
                file.write_bytes(content)
                before[file] = content
        result = self.run_script("scripts/build-images.sh",["--apps"],
                                 {"PROCUREMENT_PATH":str(app_paths[0]),"INTEGRATIONS_PATH":str(app_paths[1])})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual({p:p.read_bytes() for p in before},before)
        self.assertIn("kind load docker-image procurement-platform:local integrations-hub:local --name portfolio-observability",self.log.read_text())

    def test_invalid_cluster_label_stops_before_tools(self):
        result = self.run_script("scripts/deploy-all.sh",extra={"CLUSTER_NAME":"../other"})
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.log.exists())

    def test_automatic_proof_refuses_existing_cluster_without_cleanup(self):
        result = self.run_script("ci/kind-proof.sh", extra={"MOCK_CLUSTERS":"portfolio-observability"})
        self.assertNotEqual(result.returncode,0)
        self.assertIn("already exists",result.stderr)
        self.assertEqual(self.log.read_text().splitlines(),["kind get clusters"])

if __name__ == "__main__":
    unittest.main()
