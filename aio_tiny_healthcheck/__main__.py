import sys
from urllib import request


def health_check():
    try:
        try:
            url = sys.argv[1]
        except IndexError:
            url = "http://localhost:8000/healthcheck"
        request.urlopen(url)
    except Exception as exc:
        print(repr(exc))
        sys.exit(1)


if __name__ == "__main__":
    health_check()
