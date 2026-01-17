from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.padding import Padding

console = Console()

def _render_status_bar(text: str):
    """Render a full-width status bar using Padding"""
    # Padding alone might not set background if the content itself doesn't fill
    # But expand=True on Padding should work?
    # Actually, Padding(renderable, pad, style=...) applies style to padding area.
    
    # Let's try formatting text with spaces? 
    # Or rely on Text alignment?
    
    # Best approach for full width inverted bar:
    # Text with justify="center" and style, but Text doesn't expand.
    # We can wrap Text in a Panel(box=None) - oh wait that failed.
    
    # Let's try Panel(box=box.HORIZONTALS) but suppress border? No.
    
    # Try: Padding with expand=True?
    bar = Padding(
        Text(f"{text}", justify="center", style="bold white on cyan"),
        (0, 0),
        style="bold white on cyan",
        expand=True
    )
    return bar

try:
    print(f"Console width: {console.width}")
    bar = _render_status_bar("Test Status Bar")
    console.print(bar)
    print("Render success")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
