from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from stagecoach.checks import Severity


HANDBOOK_URL = (
    "https://goldenplanetaryhealthlab.github.io/"
    "01_orientation/start-here.html#the-working-philosophy"
)


def banner(console: Console, message: str) -> None:
    """
    Render a highlighted banner message.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    message : str
        Message to display inside the banner panel.
    """
    console.print(
        Panel.fit(
            message,
            style="bold cyan",
            border_style="cyan",
        )
    )


def success(console: Console, message: str) -> None:
    """
    Render a success message.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    message : str
        Message body to print.
    """
    console.print(f"[bold green]✓[/bold green] {escape(message)}")


def warning(console: Console, message: str) -> None:
    """
    Render a warning message.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    message : str
        Message body to print.
    """
    console.print(f"[bold yellow]⚠[/bold yellow] {escape(message)}")


def error(console: Console, message: str) -> None:
    """
    Render an error message.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    message : str
        Message body to print.
    """
    console.print(f"[bold red]✖[/bold red] {escape(message)}")


def info(console: Console, message: str) -> None:
    """
    Render an informational message.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    message : str
        Message body to print.
    """
    console.print(f"[bold cyan]•[/bold cyan] {escape(message)}")


def failure_panel(console: Console, message: str) -> None:
    """
    Render an error message inside a bordered panel.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    message : str
        Message body to print.
    """
    console.print(
        Panel.fit(
            f"[bold red]✖[/bold red] {escape(message)}",
            border_style="red",
        )
    )


def handbook_note(console: Console) -> None:
    """
    Print a link to the Frontier handbook principles.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    """
    console.print(
        "[dim]See handbook for explanation of principles:[/dim] "
        f"[link={HANDBOOK_URL}]{HANDBOOK_URL}[/link]"
    )


def format_principle(principle: int | list[int]) -> str:
    """
    Format one or more principle identifiers for display.

    Parameters
    ----------
    principle : int | list[int]
        Principle number or collection of principle numbers.

    Returns
    -------
    str
        Comma-separated principle identifiers.
    """
    if isinstance(principle, list):
        return ", ".join(str(item) for item in principle)

    return str(principle)


def check_result(console: Console, result) -> None:
    """
    Render a manifest check result using severity-specific styling.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    result
        Object with ``name``, ``state``, ``message``, and ``principle``
        attributes, typically a ``CheckResult`` instance.
    """
    principle = format_principle(result.principle)

    if result.state == Severity.PASS:
        console.print(
            f"[bold green]✓ {escape(result.name)}[/bold green] "
            f"[dim]principle {principle}[/dim]\n"
            f"  {escape(result.message)}"
        )

    elif result.state == Severity.WARNING:
        console.print(
            f"[bold yellow]⚠ {escape(result.name)}[/bold yellow] "
            f"[dim]principle {principle}[/dim]\n"
            f"  {escape(result.message)}"
        )

    else:
        console.print(
            f"[bold red]✖ {escape(result.name)}[/bold red] "
            f"[dim]principle {principle}[/dim]\n"
            f"  {escape(result.message)}"
        )
