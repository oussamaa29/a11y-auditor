def fake_resolver(*addresses):
    """Remplace socket.getaddrinfo : renvoie les adresses données, sans réseau."""

    def resolve(host, port):
        return [(None, None, None, "", (address, 0)) for address in addresses]

    return resolve
