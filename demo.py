"""Quick demo of Karuvi: dependency tree, classes/scopes, and line-level dependency queries."""

from rich.console import Console
from rich.panel import Panel

import deps
import get_tree

console = Console()

demo_source = '''import os
import socket

base_port = 8000
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def greet(name, port=base_port):
    url = f"http://localhost:{port}"
    data = url + str(sock)
    return data

class Server:
    def __init__(self, host):
        self.host = host

    def start(self, url=greet("me")):
        return socket.gethostname()

Server("local").start()
'''

console.print(
    Panel(
        "\n".join(f"{i:2}  {ln}" for i, ln in enumerate(demo_source.splitlines(), 1)),
        title="Demo source (saved to /tmp/karuvi_demo.py)",
        border_style="cyan",
    )
)

with open("/tmp/karuvi_demo.py", "w") as fh:
    fh.write(demo_source)

console.print("\n[bold]1) Parse -> dependency tree + classes + functions + scopes[/bold]")
get_tree.parse_file("/tmp/karuvi_demo.py")

console.print(
    "\n[bold]2) What does line 7 ('greet') depend on?[/bold]"
)
deps.visualize_dependencies("/tmp/karuvi_demo.py", 7)

console.print(
    "\n[bold]3) Lines 8-10 (greet body: url, data, return) — usages + declarations[/bold]"
)
deps.visualize_dependencies("/tmp/karuvi_demo.py", 8, 10, include_declarations=True)

console.print("\n[bold]4) Cross-module: example_b.py lines 3-5[/bold]")
deps.visualize_dependencies("example_b.py", 3, 5)

console.print("\n[bold]5) Raw records for line 9 (data = url + str(sock))[/bold]")
for r in deps.dependencies_for_lines("/tmp/karuvi_demo.py", 9):
    console.print(
        f"  scope={r.scope_name!r:16} name={r.name!r:10} "
        f"uuid={str(r.uuid)[:12]:12} use={r.use_lineno}:{r.use_colno} "
        f"declared={r.decl_file}:{r.decl_lineno}:{r.decl_colno} kind={r.kind}"
    )