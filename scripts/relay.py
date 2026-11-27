"""最小 TCP 中继：bench 容器所在的 internal 网络只能经此访问本机模型代理。

用法: python scripts/relay.py [listen_port] [upstream_host] [upstream_port]
默认 0.0.0.0:8317 -> host.docker.internal:8317。只转发字节，不解析、不记录内容。
"""

import asyncio
import sys

LISTEN_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8317
UPSTREAM = (
    sys.argv[2] if len(sys.argv) > 2 else 'host.docker.internal',
    int(sys.argv[3]) if len(sys.argv) > 3 else 8317,
)


async def pipe(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()


async def handle(client_reader, client_writer):
    try:
        up_reader, up_writer = await asyncio.open_connection(*UPSTREAM)
    except OSError:
        client_writer.close()
        return
    await asyncio.gather(pipe(client_reader, up_writer), pipe(up_reader, client_writer))


async def main():
    server = await asyncio.start_server(handle, '0.0.0.0', LISTEN_PORT)
    print(f'relay :{LISTEN_PORT} -> {UPSTREAM[0]}:{UPSTREAM[1]}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
