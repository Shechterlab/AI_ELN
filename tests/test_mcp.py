"""
The MCP server (mcp/server.mjs) and the one-shot command (mcp/call.mjs).

A small client written here speaks the protocol the way the specification describes it (JSON-RPC 2.0,
one message per line on stdin and stdout): initialize, the initialized notification, tools/list,
tools/call. Skipped when Node is not installed.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")


class Client:
    def __init__(self, root: Path, *flags: str):
        env = dict(os.environ, AI_ELN_CONFIG=str(root / "no-such-config.json"))
        for key in ("AI_ELN_ROOT", "AI_ELN_INITIALS", "AI_ELN_RESEARCHER"):
            env.pop(key, None)
        self.proc = subprocess.Popen([NODE, str(REPO_ROOT / "mcp" / "server.mjs"), "--root", str(root), *flags],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, encoding="utf-8", env=env)
        self.next_id = 0

    def send(self, message: dict) -> None:
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params=None) -> dict:
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        line = self.proc.stdout.readline()
        assert "\n" not in line.rstrip("\n")
        reply = json.loads(line)
        assert reply["jsonrpc"] == "2.0" and reply["id"] == self.next_id, reply
        return reply

    def call(self, name: str, arguments=None) -> dict:
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})["result"]

    def close(self) -> str:
        self.proc.stdin.close()
        self.proc.wait(timeout=10)
        self.proc.stdout.close()
        err = self.proc.stderr.read()
        self.proc.stderr.close()
        return err


@unittest.skipIf(NODE is None, "node not available")
class TestMcpServer(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "nb"
        shutil.copytree(REPO_ROOT / "sandbox", self.root)

    def start(self, *flags, version="2025-06-18"):
        client = Client(self.root, *flags)
        self.addCleanup(lambda: client.proc.poll() is None and client.proc.kill())
        init = client.request("initialize", {"protocolVersion": version, "capabilities": {},
                                             "clientInfo": {"name": "test", "version": "0"}})["result"]
        client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return client, init

    def test_handshake_and_tool_list(self):
        client, init = self.start()
        self.assertEqual(init["protocolVersion"], "2025-06-18")
        self.assertIn("tools", init["capabilities"])
        self.assertEqual(init["serverInfo"]["name"], "ai-eln")
        self.assertIn("Cite the experiment ID", init["instructions"])
        self.assertEqual(client.request("ping")["result"], {})
        tools = client.request("tools/list")["result"]["tools"]
        names = [t["name"] for t in tools]
        self.assertEqual(len(names), len(set(names)))
        for expected in ("get_conventions", "find_notes", "read_note", "create_experiment", "write_section",
                         "check_notebook", "complete_experiment", "verify_files", "export_notes", "meeting_brief"):
            self.assertIn(expected, names)
        for t in tools:
            self.assertRegex(t["name"], r"^[a-z][a-z_]*$")
            self.assertTrue(t["description"])
            schema = t["inputSchema"]
            self.assertEqual(schema["type"], "object")
            self.assertFalse(schema["additionalProperties"])
            self.assertTrue(set(schema["required"]) <= set(schema["properties"]))
            for prop in schema["properties"].values():
                self.assertIn("description", prop)
            self.assertIn("readOnlyHint", t["annotations"])
        self.assertEqual(client.close().count("\n"), 1, "only the start-up line goes to stderr")

    def test_an_older_or_unknown_protocol_version(self):
        client, init = self.start(version="2024-11-05")
        self.assertEqual(init["protocolVersion"], "2024-11-05")
        self.assertNotIn("structuredContent", client.call("notebook_overview"))
        client.close()
        client, init = self.start(version="1999-01-01")
        self.assertEqual(init["protocolVersion"], "2025-06-18")
        client.close()

    def test_reading_and_writing_through_tools(self):
        client, _ = self.start("--initials", "ZZ", "--researcher", "Zed Zed")
        found = client.call("find_notes", {"status": "active"})
        self.assertFalse(found["isError"])
        self.assertEqual(found["structuredContent"], json.loads(found["content"][0]["text"]))
        self.assertEqual([n["id"] for n in found["structuredContent"]["notes"]], ["ALXe0004"])

        note = client.call("read_note", {"id": "ALXe0002"})["structuredContent"]
        self.assertEqual(note["fields"]["status"], "complete")
        self.assertIn("## Results", note["text"])
        self.assertIn("ALXe0002_chromatin-fraction.csv", note["files"]["4-data_processed"])
        csv = client.call("read_file", {"path": note["folder"] + "/4-data_processed/ALXe0002_chromatin-fraction.csv"})
        self.assertIn(",", csv["structuredContent"]["text"])

        made = client.call("create_experiment", {"title": "Made over MCP", "project": "PRMT5-ChromatinRelease", "protocol": "P_WesternBlot"})
        new = made["structuredContent"]
        self.assertEqual(new["id"], "ZZe0001")
        self.assertTrue((self.root / new["path"]).exists())
        self.assertEqual(len(new["extra"]), 1)
        self.assertIn("researcher: Zed Zed", (self.root / new["path"]).read_text(encoding="utf-8"))

        client.call("write_section", {"id": "ZZe0001", "section": "Results", "text": "Band at 28 kDa in all lanes."})
        client.call("write_section", {"id": "ZZe0001", "section": "Results", "text": "Second line.", "mode": "append"})
        client.call("write_section", {"id": "ZZe0001", "section": "Interpretation", "text": "Antibody works."})
        client.call("set_field", {"id": "ZZe0001", "field": "tags", "value": ["meeting"]})
        text = (self.root / new["path"]).read_text(encoding="utf-8")
        self.assertIn("## Results\n\nBand at 28 kDa in all lanes.\n\nSecond line.\n\n## Interpretation\n\nAntibody works.\n\n## Decision", text)
        self.assertIn("tags: [meeting]          # add meeting", text)
        added = client.call("add_file", {"id": "ZZe0001", "subfolder": "4-data_processed", "original_name": "quant.csv",
                                         "text": "lane,signal\n1,2.0\n", "description": "band quantification"})
        self.assertTrue(added["structuredContent"]["path"].endswith("4-data_processed/ZZe0001_band-quantification.csv"))
        done = client.call("complete_experiment", {"id": "ZZe0001", "date": "2026-10-01"})["structuredContent"]
        self.assertTrue((self.root / done["snapshot"]).exists())
        self.assertTrue(client.call("verify_files", {"id": "ZZe0001"})["structuredContent"]["ok"])
        check = client.call("check_notebook")["structuredContent"]
        self.assertEqual((check["errors"], check["warnings"]), (0, 0), check["text"])
        brief = client.call("meeting_brief")["structuredContent"]["markdown"]
        self.assertIn("ZZe0001 - Made over MCP", brief)
        self.assertIn("Band at 28 kDa", brief)
        eln_file = client.call("export_notes", {"experiment_ids": ["ZZe0001"], "format": "eln"})["structuredContent"]
        self.assertTrue((self.root / eln_file["path"]).read_bytes().startswith(b"PK"))
        client.close()

    def test_mistakes_are_reported_not_fatal(self):
        client, _ = self.start()
        for name, args, expected in [
            ("read_note", {"id": "NOPEe0001"}, "no note NOPEe0001"),
            ("create_experiment", {"title": "x"}, "initials are needed"),
            ("create_experiment", {}, '"title" is required'),
            ("find_notes", {"colour": "red"}, 'unknown argument "colour"'),
            ("find_notes", {"kind": "wizard"}, "must be one of"),
            ("read_file", {"path": "../outside.txt"}, "inside the notebook folder"),
            ("read_file", {"path": "/etc/passwd"}, "inside the notebook folder"),
            ("set_field", {"id": "ALXe0001", "field": "experiment_id", "value": "X"}, "cannot be changed"),
            ("set_field", {"id": "ALXe0001", "field": "status", "value": "done"}, "status must be one of"),
            ("write_section", {"id": "ALXe0001", "section": "Nope", "text": "x"}, "no '## Nope' section"),
            ("update_note", {"id": "ALXe0001", "text": "no header"}, "Header problem"),
            ("add_file", {"id": "ALXe0001", "subfolder": "9-other", "original_name": "a.txt", "text": "x"}, "must be one of"),
            ("complete_experiment", {"id": "ALXe0004"}, "still empty"),
            ("export_notes", {}, "choose what to export"),
        ]:
            result = client.call(name, args)
            self.assertTrue(result["isError"], name)
            self.assertIn(expected, result["content"][0]["text"], name)
        self.assertEqual(client.request("tools/call", {"name": "delete_everything"})["error"]["code"], -32602)
        self.assertEqual(client.request("resources/list")["error"]["code"], -32601)
        client.proc.stdin.write("this is not json\n")
        client.proc.stdin.flush()
        self.assertEqual(json.loads(client.proc.stdout.readline())["error"]["code"], -32700)
        self.assertFalse(client.call("notebook_overview")["isError"], "still answering after bad input")
        self.assertFalse((self.root.parent / "outside.txt").exists())
        client.close()

    def test_read_only_mode(self):
        client, _ = self.start("--read-only")
        names = [t["name"] for t in client.request("tools/list")["result"]["tools"]]
        self.assertIn("find_notes", names)
        for writer in ("create_experiment", "update_note", "write_section", "set_field", "add_file", "complete_experiment",
                       "rebuild_index", "export_notes", "meeting_brief", "render_snapshot"):
            self.assertNotIn(writer, names)
        before = sorted(p.as_posix() for p in self.root.rglob("*"))
        self.assertEqual(client.request("tools/call", {"name": "create_experiment", "arguments": {"title": "x", "initials": "ZZ"}})["error"]["code"], -32602)
        client.call("check_notebook")
        client.call("verify_files")
        self.assertEqual(sorted(p.as_posix() for p in self.root.rglob("*")), before)
        client.close()

    def test_one_shot_command(self):
        run = lambda *a: subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), *a], capture_output=True, text=True, encoding="utf-8")  # noqa: E731
        listing = run("--list").stdout
        self.assertIn("create_experiment  title [project]", listing)
        functions = json.loads(run("--openai").stdout)
        self.assertEqual(functions[0]["type"], "function")
        self.assertEqual(functions[0]["parameters"]["type"], "object")
        out = run("--root", str(self.root), "find_notes", '{"kind": "protocol"}')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["count"], 3)
        bad = run("--root", str(self.root), "read_note", '{"id": "nope"}')
        self.assertEqual(bad.returncode, 1)
        self.assertIn("no note nope", bad.stderr)


if __name__ == "__main__":
    unittest.main()
