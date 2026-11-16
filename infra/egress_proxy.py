"""Small CONNECT-only proxy pinned to public YouTube addresses."""

from __future__ import annotations

import asyncio
import ipaddress
import socket


def allowed_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    return host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
        "youtubei.googleapis.com",
    } or host.endswith((".googlevideo.com", ".ytimg.com", ".youtube.com"))


def public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return address.is_global and not address.is_multicast and not address.is_unspecified


async def tunnel(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    upstream_writer: asyncio.StreamWriter | None = None
    try:
        header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 8)
        if len(header) > 8192:
            raise ValueError("header too large")
        first = header.split(b"\r\n", 1)[0].decode("ascii").split()
        if len(first) != 3:
            raise ValueError("invalid request")
        method, target, _ = first
        host, port = target.rsplit(":", 1)
        host = host.lower().rstrip(".")
        if method != "CONNECT" or port != "443" or not allowed_host(host):
            raise ValueError("destination denied")
        addresses = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM), timeout=8
        )
        if not addresses or any(not public_address(item[4][0]) for item in addresses):
            raise ValueError("non-public destination")
        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection(addresses[0][4][0], 443), timeout=12
        )
        writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        await writer.drain()

        async def copy(source: asyncio.StreamReader, destination: asyncio.StreamWriter) -> None:
            while data := await asyncio.wait_for(source.read(65536), timeout=45):
                destination.write(data)
                await destination.drain()

        tasks = [
            asyncio.create_task(copy(reader, upstream_writer)),
            asyncio.create_task(copy(upstream_reader, writer)),
        ]
        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except (
        asyncio.IncompleteReadError,
        asyncio.LimitOverrunError,
        TimeoutError,
        OSError,
        ValueError,
    ):
        try:
            writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
        except OSError:
            pass
    finally:
        if upstream_writer:
            upstream_writer.close()
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


async def serve() -> None:
    semaphore = asyncio.Semaphore(64)

    async def bounded(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        async with semaphore:
            await tunnel(reader, writer)

    server = await asyncio.start_server(bounded, "0.0.0.0", 3128, limit=8192)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(serve())
