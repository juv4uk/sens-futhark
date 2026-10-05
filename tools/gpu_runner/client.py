import argparse
import json
import socket


def call(req, host="127.0.0.1", port=8765):
    payload = (json.dumps(req, separators=(",", ":")) + "\n").encode("utf-8")
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.sendall(payload)
        f = sock.makefile("rb")
        line = f.readline()
        if not line:
            raise RuntimeError("runner closed connection")
        return json.loads(line.decode("utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--ping", action="store_true")
    p.add_argument("--bench", action="store_true")
    p.add_argument("--n", type=int, default=1_000_000)
    p.add_argument("--iters", type=int, default=100)
    p.add_argument("--json")
    args = p.parse_args()

    if args.ping:
        req = {"op": "ping"}
    elif args.bench:
        req = {"op": "benchmark", "n": args.n, "iters": args.iters}
    elif args.json:
        req = json.loads(args.json)
    else:
        p.error("use --ping, --bench, or --json")

    print(json.dumps(call(req, port=args.port), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
