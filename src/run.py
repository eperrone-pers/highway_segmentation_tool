"""CLI entrypoint to launch the GUI."""

import gui_main


def main() -> None:
	# Highway Segmentation GA - GUI Launcher
	print("Highway Segmentation Genetic Algorithm")
	print("=" * 40)
	print("Launching GUI interface...")

	gui_main.main()


if __name__ == "__main__":
	main()