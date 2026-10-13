"""Local Proxy Forwarder for Anti-Detect Browsers.

Transforms authenticated SOCKS5, SOCKS4, and HTTP/HTTPS proxies into a local,
zero-authentication HTTP proxy (http://127.0.0.1:<port>).

Solves two core browser limitations:
1. Firefox / Camoufox: 'Browser does not support socks5 proxy authentication'.
2. Chromium: '--proxy-server' command line does not support username/password auth.
"""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import logging
import struct
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .models import ProxyConfig

logger = logging.getLogger("camoufox_pm.proxy_forwarder")


class LocalProxyForwarder:
    """Lightweight local HTTP-to-SOCKS/HTTP proxy bridge.

    Runs on 127.0.0.1 with an OS-assigned dynamic port, providing transparent
    credential injection and protocol translation.
    """

    def __init__(
        self,
        upstream_type: str,
        upstream_server: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.upstream_type = upstream_type.lower().strip()
        self.upstream_server = upstream_server.strip()
        self.username = username
        self.password = password
        self.server: Optional[asyncio.Server] = None
        self.local_port: int = 0
        self._active_tasks: set[asyncio.Task[None]] = set()
        self._is_running = False

    @classmethod
    def from_proxy_config(cls, proxy: ProxyConfig) -> LocalProxyForwarder:
        p_type = proxy.type.value if hasattr(proxy.type, "value") else str(proxy.type)
        return cls(
            upstream_type=p_type,
            upstream_server=proxy.server,
            username=proxy.username,
            password=proxy.password,
        )

    @property
    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.local_port}"

    def _parse_upstream(self) -> tuple[str, int]:
        srv = self.upstream_server
        if "://" in srv:
            srv = srv.split("://", 1)[1]
        srv = srv.rstrip("/")
        if ":" in srv:
            h, p = srv.rsplit(":", 1)
            try:
                return h, int(p)
            except ValueError:
                pass
        return srv, 1080 if "socks" in self.upstream_type else 8080

    async def start(self) -> str:
        """Start local HTTP forwarder on 127.0.0.1 on an available OS port."""
        if self._is_running and self.server:
            return self.local_url

        self.server = await asyncio.start_server(
            self._handle_client,
            host="127.0.0.1",
            port=0,
        )
        self.local_port = self.server.sockets[0].getsockname()[1]
        self._is_running = True
        logger.info(
            f"Started LocalProxyForwarder at {self.local_url} "
            f"forwarding to {self.upstream_type}://{self.upstream_server}"
        )
        return self.local_url

    async def stop(self) -> None:
        """Stop local forwarder and terminate all active forwarded sockets."""
        self._is_running = False
        if self.server:
            self.server.close()
            try:
                await self.server.wait_closed()
            except Exception:
                pass
            self.server = None

        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()
        self._active_tasks.clear()
        logger.info(f"Stopped LocalProxyForwarder on port {self.local_port}")

    async def _handle_client(
        self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task:
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

        try:
            req_line = await client_reader.readline()
            if not req_line:
                client_writer.close()
                return

            line_str = req_line.decode("latin1", errors="ignore").strip()
            parts = line_str.split()
            if len(parts) < 2:
                client_writer.close()
                return

            method = parts[0].upper()
            target = parts[1]

            # Read remaining headers
            headers: list[bytes] = []
            while True:
                h_line = await client_reader.readline()
                if not h_line or h_line in (b"\r\n", b"\n"):
                    break
                if not h_line.lower().startswith(b"proxy-authorization"):
                    headers.append(h_line)

            if method == "CONNECT":
                # HTTPS Tunneling
                if ":" in target:
                    dst_host, dst_port_str = target.rsplit(":", 1)
                    dst_port = int(dst_port_str)
                else:
                    dst_host, dst_port = target, 443

                remote_reader, remote_writer = await self._connect_upstream(dst_host, dst_port)
                client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await client_writer.drain()

                await self._pipe(client_reader, client_writer, remote_reader, remote_writer)
            else:
                # Plain HTTP Request
                dst_host = ""
                dst_port = 80
                if target.startswith("http://"):
                    from urllib.parse import urlparse

                    parsed = urlparse(target)
                    dst_host = parsed.hostname or ""
                    dst_port = parsed.port or 80
                    path = parsed.path or "/"
                    if parsed.query:
                        path += f"?{parsed.query}"
                    proto = parts[2] if len(parts) > 2 else "HTTP/1.1"
                    req_line = f"{method} {path} {proto}\r\n".encode("latin1")
                else:
                    for h in headers:
                        if h.lower().startswith(b"host:"):
                            val = h.split(b":", 1)[1].strip().decode("latin1")
                            if ":" in val:
                                dst_host, p_str = val.rsplit(":", 1)
                                dst_port = int(p_str)
                            else:
                                dst_host = val
                            break

                if not dst_host:
                    client_writer.close()
                    return

                remote_reader, remote_writer = await self._connect_upstream(dst_host, dst_port)
                remote_writer.write(req_line)
                for h in headers:
                    remote_writer.write(h)
                remote_writer.write(b"\r\n")
                await remote_writer.drain()

                await self._pipe(client_reader, client_writer, remote_reader, remote_writer)
        except Exception as exc:
            logger.debug(f"Proxy forwarder stream ended: {exc}")
        finally:
            try:
                client_writer.close()
                await client_writer.wait_closed()
            except Exception:
                pass

    async def _connect_upstream(
        self, dst_host: str, dst_port: int
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        u_host, u_port = self._parse_upstream()

        if "socks" in self.upstream_type:
            return await self._connect_socks5(u_host, u_port, dst_host, dst_port)
        else:
            return await self._connect_http_proxy(u_host, u_port, dst_host, dst_port)

    async def _connect_socks5(
        self, u_host: str, u_port: int, dst_host: str, dst_port: int
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        reader, writer = await asyncio.open_connection(u_host, u_port)

        try:
            # 1. Version identifier and auth method selection (RFC 1928)
            if self.username:
                # 0x00: NO AUTHENTICATION REQUIRED, 0x02: USERNAME/PASSWORD
                writer.write(b"\x05\x02\x00\x02")
            else:
                writer.write(b"\x05\x01\x00")
            await writer.drain()

            ver_method = await reader.readexactly(2)
            if ver_method[0] != 0x05:
                raise ConnectionError(f"Invalid SOCKS version: {ver_method[0]}")

            # 2. Subnegotiation authentication (RFC 1929)
            if ver_method[1] == 0x02:
                if not self.username:
                    raise ConnectionError("Upstream SOCKS5 proxy requires credentials")
                u_bytes = self.username.encode("utf-8")
                p_bytes = (self.password or "").encode("utf-8")
                auth_payload = (
                    b"\x01" + bytes([len(u_bytes)]) + u_bytes + bytes([len(p_bytes)]) + p_bytes
                )
                writer.write(auth_payload)
                await writer.drain()

                auth_res = await reader.readexactly(2)
                if auth_res[0] != 0x01 or auth_res[1] != 0x00:
                    raise ConnectionError("Upstream SOCKS5 proxy authentication failed")
            elif ver_method[1] != 0x00:
                raise ConnectionError(f"Unsupported SOCKS5 auth method: {ver_method[1]}")

            # 3. SOCKS5 request details
            try:
                ip = ipaddress.IPv4Address(dst_host)
                atyp = b"\x01"
                addr = ip.packed
            except ValueError:
                try:
                    ip6 = ipaddress.IPv6Address(dst_host)
                    atyp = b"\x04"
                    addr = ip6.packed
                except ValueError:
                    h_bytes = dst_host.encode("utf-8")
                    atyp = b"\x03"
                    addr = bytes([len(h_bytes)]) + h_bytes

            req = b"\x05\x01\x00" + atyp + addr + struct.pack("!H", dst_port)
            writer.write(req)
            await writer.drain()

            # 4. SOCKS5 response header
            resp = await reader.readexactly(4)
            if resp[0] != 0x05 or resp[1] != 0x00:
                err_codes = {
                    1: "General failure",
                    2: "Connection not allowed",
                    3: "Network unreachable",
                    4: "Host unreachable",
                    5: "Connection refused",
                    6: "TTL expired",
                    7: "Command not supported",
                    8: "Address type not supported",
                }
                msg = err_codes.get(resp[1], f"error {resp[1]}")
                raise ConnectionError(f"SOCKS5 connect to {dst_host}:{dst_port} failed: {msg}")

            bnd_atyp = resp[3]
            if bnd_atyp == 1:
                await reader.readexactly(4 + 2)
            elif bnd_atyp == 3:
                d_len = (await reader.readexactly(1))[0]
                await reader.readexactly(d_len + 2)
            elif bnd_atyp == 4:
                await reader.readexactly(16 + 2)

            return reader, writer
        except Exception:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            raise

    async def _connect_http_proxy(
        self, u_host: str, u_port: int, dst_host: str, dst_port: int
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        reader, writer = await asyncio.open_connection(u_host, u_port)
        try:
            auth_header = ""
            if self.username:
                creds = base64.b64encode(
                    f"{self.username}:{self.password or ''}".encode()
                ).decode()
                auth_header = f"Proxy-Authorization: Basic {creds}\r\n"

            connect_req = (
                f"CONNECT {dst_host}:{dst_port} HTTP/1.1\r\n"
                f"Host: {dst_host}:{dst_port}\r\n"
                f"{auth_header}\r\n"
            )
            writer.write(connect_req.encode("latin1"))
            await writer.drain()

            # Read response status
            resp_line = await reader.readline()
            if not resp_line:
                raise ConnectionError("Empty response from upstream HTTP proxy")
            parts = resp_line.decode("latin1", errors="ignore").split()
            if len(parts) < 2 or parts[1] != "200":
                raise ConnectionError(
                    f"Upstream HTTP proxy CONNECT failed: {resp_line.decode('latin1', errors='ignore').strip()}"
                )

            while True:
                h = await reader.readline()
                if not h or h in (b"\r\n", b"\n"):
                    break

            return reader, writer
        except Exception:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            raise

    async def _pipe(
        self,
        c_reader: asyncio.StreamReader,
        c_writer: asyncio.StreamWriter,
        r_reader: asyncio.StreamReader,
        r_writer: asyncio.StreamWriter,
    ) -> None:
        async def forward(src: asyncio.StreamReader, dst: asyncio.StreamWriter):
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        t1 = asyncio.create_task(forward(c_reader, r_writer))
        t2 = asyncio.create_task(forward(r_reader, c_writer))
        self._active_tasks.add(t1)
        self._active_tasks.add(t2)
        try:
            await asyncio.gather(t1, t2, return_exceptions=True)
        finally:
            self._active_tasks.discard(t1)
            self._active_tasks.discard(t2)
            try:
                r_writer.close()
            except Exception:
                pass
