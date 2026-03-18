import click


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Spec Executor — generate implementations from specs, iterate until tests pass."""
    pass
