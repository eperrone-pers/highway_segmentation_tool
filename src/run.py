"""Entry point for launching the GUI application."""

import gui_main


def main() -> None:
    """Start the Highway Segmentation GA graphical interface."""
    print("Highway Segmentation Genetic Algorithm")
    print("=" * 40)
    print("Launching GUI interface...")

    gui_main.main()


if __name__ == "__main__":
	main()