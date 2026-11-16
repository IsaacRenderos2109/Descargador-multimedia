"""PyInstaller entry point; freeze_support runs before GUI imports."""

import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from video_downloader.__main__ import main

    raise SystemExit(main())
