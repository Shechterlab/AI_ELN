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
        shutil.copytree(REPO_ROOT / "sandbox" / "alex", self.root)

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
        self.assertEqual([n["id"] for n in found["structuredContent"]["notes"]], ["ALXe0004", "ALXe0005"])

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
        # a notebook that does not say whose it is: with no initials anywhere, creating a record is refused
        book = self.root / "notebook.md"
        book.write_bytes(book.read_bytes().replace(b"initials: ALX", b"initials:").replace(b"owner: Alex Example", b"owner:"))
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
                       "rebuild_index", "render_snapshot"):
            self.assertNotIn(writer, names)
        # the brief and the export are offered, and refuse to save
        self.assertIn("Lab meeting brief", client.call("meeting_brief")["content"][0]["text"])
        self.assertFalse(client.call("export_notes", {"status": "active"})["isError"])
        for name, args in (("meeting_brief", {"save": True}), ("export_notes", {"status": "active", "save": True}),
                           ("export_notes", {"status": "active", "format": "eln"})):
            refused = client.call(name, args)
            self.assertTrue(refused["isError"], name)
            self.assertIn("read-only", refused["content"][0]["text"])
        self.assertTrue(client.call("export_notes", {"status": "active", "format": "eln", "return_bytes": True})["structuredContent"]["bytes"]["base64"].startswith("UEsD"))
        before = sorted(p.as_posix() for p in self.root.rglob("*"))
        self.assertEqual(client.request("tools/call", {"name": "create_experiment", "arguments": {"title": "x", "initials": "ZZ"}})["error"]["code"], -32602)
        client.call("check_notebook")
        client.call("verify_files")
        self.assertEqual(sorted(p.as_posix() for p in self.root.rglob("*")), before)
        client.close()

    def test_hostile_arguments_do_no_damage(self):
        """Found by a role-played hostile client; each of these once wrote something it should not have."""
        client, _ = self.start("--initials", "ZZ")
        outside = self.root.parent / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("SECRET", encoding="utf-8")
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())

        # a date is a date: it cannot carry a path into the file name
        for date in ("../../../../../probe", "2026-02-30", "2026-01-01\nx", "a/../../x"):
            r = client.call("add_file", {"id": "ALXe0004", "subfolder": "3-code", "original_name": "p.R", "description": "p", "text": "x", "date": date})
            self.assertTrue(r["isError"], date)
        # names: no folders, no control characters, no trailing dots or spaces
        for name, expected in (("x.R\n", "ALXe0004_d.R"), ("trail.R. ", "ALXe0004_d.R"), ("../evil.R", "ALXe0004_d.R")):
            r = client.call("add_file", {"id": "ALXe0004", "subfolder": "3-code", "original_name": name, "description": "d", "text": "x"})
            self.assertTrue(r["structuredContent"]["path"].endswith("3-code/" + expected), r)
            (self.root / r["structuredContent"]["path"]).unlink()
        for bad in ("!!!notbase64***", "data:text/plain;base64,QQ=="):
            self.assertTrue(client.call("add_file", {"id": "ALXe0004", "subfolder": "3-code", "original_name": "b.bin", "base64": bad})["isError"])
        self.assertEqual(sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()), before)

        # line breaks in a header value become a space; the header stays whole
        made = client.call("create_experiment", {"title": "x\n---\n## Hacked", "notebook": "a\u2028b", "tags": "t\nstatus: complete"})["structuredContent"]
        note = client.call("read_note", {"id": made["id"]})["structuredContent"]
        self.assertEqual(note["fields"]["title"], "x --- ## Hacked")
        self.assertEqual(note["fields"]["status"], "active")
        self.assertEqual(note["fields"]["researcher"], "ZZ")
        client.call("set_field", {"id": made["id"], "field": "title", "value": "a\n---\nb"})
        note = client.call("read_note", {"id": made["id"]})["structuredContent"]
        self.assertEqual((note["fields"]["title"], note["fields"]["status"], note["fields"]["date_started"] != ""), ("a --- b", "active", True))

        # set_field: only real fields, real dates, text values; lists can be added to and cleared
        for args, expected in (({"field": "nonsense", "value": "x"}, "is not a header field"),
                               ({"field": "date_started", "value": "2026-13-45"}, "YYYY-MM-DD"),
                               ({"field": "tags", "value": {"a": 1}}, "must be text"),
                               ({"field": "title", "value": "x", "mode": "add"}, "not a list")):
            r = client.call("set_field", {"id": made["id"], **args})
            self.assertTrue(r["isError"], args)
            self.assertIn(expected, r["content"][0]["text"])
        client.call("set_field", {"id": made["id"], "field": "tags", "value": "[one, two]"})
        client.call("set_field", {"id": made["id"], "field": "tags", "value": "meeting", "mode": "add"})
        client.call("set_field", {"id": made["id"], "field": "tags", "value": ["ONE"], "mode": "remove"})
        client.call("set_field", {"id": made["id"], "field": "notebook_reference", "value": ""})
        note = client.call("read_note", {"id": made["id"]})["structuredContent"]
        self.assertEqual((note["fields"]["tags"], note["fields"]["notebook_reference"]), (["two", "meeting"], ""))

        # a section cannot smuggle in another section; update_note cannot break the header
        r = client.call("write_section", {"id": made["id"], "section": "results", "text": "ok line\n## Interpretation\nfake"})
        self.assertTrue(r["isError"])
        self.assertFalse(client.call("write_section", {"id": made["id"], "section": "results", "text": "matched without capitals"})["isError"])
        self.assertIn("Its sections are: Objective", client.call("write_section", {"id": made["id"], "section": "Nope", "text": "x"})["content"][0]["text"])
        text = client.call("read_note", {"id": made["id"]})["structuredContent"]["text"]
        for broken in (text.replace("status: active", "status: banana"), text.replace("type: experiment", "type: sample"),
                       "\n".join(l for l in text.splitlines() if not l.startswith("researcher:"))):
            self.assertTrue(client.call("update_note", {"id": made["id"], "text": broken})["isError"])

        # someone else's initials do not get this person's name; bad initials are named as bad
        other = client.call("create_experiment", {"title": "t", "initials": "JSR"})["structuredContent"]
        self.assertEqual(client.call("read_note", {"id": other["id"]})["structuredContent"]["fields"]["researcher"], "JSR")
        self.assertIn("must be 2 to 4 letters", client.call("create_experiment", {"title": "t", "initials": "ABCDE"})["content"][0]["text"])

        # names that cannot live on every computer
        for name, args in (("create_protocol", {"name": "westernblot"}), ("create_project", {"project_id": "prmt5-chromatinrelease"}),
                           ("create_project", {"project_id": "CON"}), ("create_protocol", {"name": "B" * 300}),
                           ("create_experiment", {"title": "t", "project": "two words"})):
            self.assertTrue(client.call(name, args)["isError"], (name, args))
        ok = client.call("create_experiment", {"title": "uses a bare protocol name", "protocol": "WesternBlot", "project": "Nope", "samples": "ALXz9999"})["structuredContent"]
        self.assertEqual(client.call("read_note", {"id": ok["id"]})["structuredContent"]["fields"]["protocols"], ["P_WesternBlot"])
        self.assertEqual(len(ok["extra"]), 1)
        self.assertEqual(len(ok["warnings"]), 2)

        # links out of the folder are not followed, for reading or for writing
        if hasattr(os, "symlink"):
            try:
                os.symlink(outside / "secret.txt", self.root / "linkfile.txt")
                os.symlink(outside, self.root / "linkdir", target_is_directory=True)
                folder = next(p for p in (self.root / "Experiments").iterdir() if p.name.startswith("ALXe0004"))
                shutil.rmtree(folder / "3-code")
                os.symlink(outside, folder / "3-code", target_is_directory=True)
            except OSError:
                folder = None  # no permission to make links (Windows without developer mode)
            if folder is not None:
                for path in ("linkfile.txt", "linkdir/secret.txt"):
                    r = client.call("read_file", {"path": path})
                    self.assertTrue(r["isError"], path)
                    self.assertNotIn("SECRET", r["content"][0]["text"])
                r = client.call("add_file", {"id": "ALXe0004", "subfolder": "3-code", "original_name": "y.R", "text": "print(2)"})
                self.assertTrue(r["isError"])
                self.assertEqual(sorted(p.name for p in outside.iterdir()), ["secret.txt"])
        self.assertFalse(client.call("notebook_overview")["isError"])
        self.assertNotIn(str(self.root), client.call("notebook_overview")["content"][0]["text"])
        client.close()

    def test_malformed_requests_get_an_answer(self):
        client, _ = self.start()
        for line, code in (("null", -32600), ("123", -32600), ("[]", -32600), ('{"jsonrpc":"2.0","id":2}', -32600),
                           ('{"jsonrpc":"2.0","id":3,"method":5}', -32600),
                           ('{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"find_notes","arguments":"x"}}', -32602),
                           ('{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{}}', -32602)):
            client.proc.stdin.write(line + "\n")
            client.proc.stdin.flush()
            self.assertEqual(json.loads(client.proc.stdout.readline())["error"]["code"], code, line)
        self.assertTrue(client.call("meeting_brief", {"days": 0})["isError"])
        self.assertEqual(client.close().count("\n"), 1, "nothing but the start-up line on stderr")

    def test_a_missing_folder_or_damaged_settings_file_is_an_error(self):
        run = lambda env, *a: subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), *a], capture_output=True, text=True,  # noqa: E731
                                             encoding="utf-8", env=dict(os.environ, **env))
        missing = self.root.parent / "typo"
        out = run({"AI_ELN_CONFIG": str(self.root / "none.json")}, "--root", str(missing), "create_experiment", '{"title": "x", "initials": "ZZ"}')
        self.assertEqual(out.returncode, 1)
        self.assertIn("there is no folder at", out.stderr)
        self.assertFalse(missing.exists())
        self.assertEqual(run({"AI_ELN_CONFIG": str(self.root / "none.json")}, "--root", str(missing), "check_notebook").returncode, 1)
        settings = self.root.parent / "cfg.json"
        settings.write_bytes(b"\xef\xbb\xbf" + json.dumps({"root": str(self.root), "initials": "bom"}).encode())
        ok = run({"AI_ELN_CONFIG": str(settings)}, "find_notes", '{"kind": "protocol"}')
        self.assertEqual((ok.returncode, json.loads(ok.stdout)["count"]), (0, 3), "a byte-order mark in the settings file is fine")
        settings.write_text("{not json", encoding="utf-8")
        bad = run({"AI_ELN_CONFIG": str(settings)}, "find_notes")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("is damaged", bad.stderr)

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
