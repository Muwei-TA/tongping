"""Local development entry point; explicitly opt into fictional demo data."""
import argparse
import os
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run Tongping locally")
    parser.add_argument("--demo", action="store_true", help="Enable fictional users; never expose publicly")
    parser.add_argument("--db", default="data/tongping.sqlite")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.demo and args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("Demo must bind to loopback. Use a controlled tunnel for device testing.")
    os.environ["TONGPING_DEMO"] = "1" if args.demo else "0"
    os.environ["TONGPING_DB"] = args.db
    uvicorn.run("server.app:create_app", factory=True, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
