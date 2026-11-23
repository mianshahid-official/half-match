"""
Match the Halves — Main Entry Point.
Runs the PySide6 Desktop GUI application or provides CLI options.
"""

import sys
import os
import argparse

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import engine

def cli_generate(args):
    """Headless CLI generation option for automated pipelines."""
    categories, warnings = engine.discover_categories(args.sets)
    for w in warnings:
        print(f"Warning: {w}")

    if args.category not in categories:
        print(f"Error: Category '{args.category}' not found in '{args.sets}'. Available: {list(categories.keys())}")
        sys.exit(1)

    cat_items = categories[args.category]
    if len(cat_items) < args.count:
        print(f"Error: Category '{args.category}' has {len(cat_items)} items, but {args.count} requested.")
        sys.exit(1)

    selected_items = cat_items[:args.count]
    if args.items:
        # User specified items
        item_map = {it["name"]: it for it in cat_items}
        chosen = []
        for name in args.items.split(","):
            name = name.strip()
            if name in item_map:
                chosen.append(item_map[name])
            else:
                print(f"Error: Item '{name}' not found in category '{args.category}'.")
                sys.exit(1)
        if len(chosen) != args.count:
            print(f"Error: Expected {args.count} items, got {len(chosen)}.")
            sys.exit(1)
        selected_items = chosen

    print(f"Generating {args.count}-item video for '{args.category}' -> {args.output}")
    engine.generate_video(
        items=selected_items,
        background_path=args.background,
        symbols_dir=args.symbols,
        output_path=args.output,
        audio_mode=args.audio_mode,
        custom_audio_path=args.music_file,
        music_volume=args.volume,
        progress_callback=lambda f, t: print(f"[{int(f*100)}%] {t}")
    )
    print("Done!")

def main():
    parser = argparse.ArgumentParser(description="Match the Halves — Kids Video Generator")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode instead of GUI")
    parser.add_argument("--sets", default="sets", help="Path to sets directory")
    parser.add_argument("--category", default="fruits", help="Category name")
    parser.add_argument("--count", type=int, choices=[3, 4], default=3, help="Item count (3 or 4)")
    parser.add_argument("--items", default=None, help="Comma-separated item names in stack order")
    parser.add_argument("--background", default=None, help="Background image path")
    parser.add_argument("--symbols", default="symbols", help="Symbols directory")
    parser.add_argument("--output", default="output.mp4", help="Output MP4 file path")
    parser.add_argument("--audio-mode", choices=["builtin", "custom", "mute"], default="builtin")
    parser.add_argument("--music-file", default=None, help="Path to music file if custom")
    parser.add_argument("--volume", type=float, default=0.5, help="Music volume (0.0 to 1.0)")

    # If any specific CLI argument was passed, run CLI; otherwise launch GUI
    if len(sys.argv) > 1 and ("--cli" in sys.argv or "--category" in sys.argv or "--output" in sys.argv):
        args = parser.parse_args()
        cli_generate(args)
    else:
        try:
            from gui import main as run_gui
        except ImportError as e:
            print(f"Error: Could not load GUI dependencies ({e}).")
            print("PySide6 is required to run the desktop GUI.")
            print("Please install PySide6: pip install PySide6")
            sys.exit(1)
        run_gui()

if __name__ == "__main__":
    main()
