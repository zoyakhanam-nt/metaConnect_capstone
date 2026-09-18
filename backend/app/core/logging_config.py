import logging
import sys


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]

    # keep noisy libraries quieter
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)