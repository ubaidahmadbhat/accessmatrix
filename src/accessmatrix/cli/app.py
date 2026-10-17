"""AccessMatrix command-line application."""

import threading
import webbrowser
from typing import Annotated

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from accessmatrix import __version__
from accessmatrix.application.health import build_health
from accessmatrix.core.settings import get_settings

app = typer.Typer(
    name="accessmatrix",
    help="API authorization regression testing platform.",
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print the installed version and exit."""

    if value:
        console.print(f"AccessMatrix {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Display the installed AccessMatrix version.",
        ),
    ] = False,
) -> None:
    """AccessMatrix API authorization regression tester."""

    del version


@app.command()
def doctor() -> None:
    """Check the local AccessMatrix environment."""

    health = build_health()

    table = Table(title="AccessMatrix Environment")
    table.add_column("Property", style="bold")
    table.add_column("Value")

    for key, value in health.items():
        label = key.replace("_", " ").title()
        table.add_row(label, value)

    console.print(table)
    console.print("[green]Environment check passed.[/green]")


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option(help="Address on which the local API will listen."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(min=1, max=65535, help="Local API port."),
    ] = 8765,
    reload: Annotated[
        bool,
        typer.Option(help="Reload the API when source files change."),
    ] = False,
) -> None:
    """Start the local AccessMatrix API."""

    console.print(f"Starting AccessMatrix API on http://{host}:{port}")

    uvicorn.run(
        "accessmatrix.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def gui(
    host: Annotated[
        str,
        typer.Option(help="Address on which the local application will listen."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(min=1, max=65535, help="Local application port."),
    ] = 8765,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Do not open the browser automatically."),
    ] = False,
) -> None:
    """Start AccessMatrix and open its local browser interface."""

    settings = get_settings()
    url = f"http://{host}:{port}"

    console.print(f"Starting {settings.app_name} at {url}")
    console.print("Press Ctrl+C to stop the application.")

    if not no_browser:
        browser_timer = threading.Timer(
            interval=1.2,
            function=webbrowser.open,
            args=(url,),
        )
        browser_timer.daemon = True
        browser_timer.start()

    uvicorn.run(
        "accessmatrix.api.app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    app()
