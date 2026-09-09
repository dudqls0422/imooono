"""``python -m tools.portal_frame_gen`` 실행 시 CLI 로 위임."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
