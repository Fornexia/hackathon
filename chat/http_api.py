"""HTTPS do worker com DNS IPv4 e validação normal de certificado/SNI.

A rota IPv6 da hospedagem apresentou handshakes instáveis. A seleção de família
fica restrita a este cliente; não altera DNS, TLS nem sockets do restante do processo.
"""
import http.client
import socket
import urllib.request


def conectar_ipv4(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    host, port = address
    ultimo = None
    for family, kind, proto, _, endpoint in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
        sock = socket.socket(family, kind, proto)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(endpoint)
            return sock
        except OSError as erro:
            ultimo = erro
            sock.close()
    raise ultimo or OSError('Nenhum endereço IPv4 disponível para a API.')


class ConexaoHTTPSIPv4(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = conectar_ipv4


class HTTPSIPv4(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(ConexaoHTTPSIPv4, req, context=self._context)


def criar_cliente():
    return urllib.request.build_opener(HTTPSIPv4())
