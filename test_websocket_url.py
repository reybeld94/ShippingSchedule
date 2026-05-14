from ShippingClient.core.websocket_url import normalize_websocket_url


def test_websocket_url_adds_default_path_for_root_urls():
    assert normalize_websocket_url("ws://10.0.0.77:8000") == "ws://10.0.0.77:8000/ws"
    assert normalize_websocket_url("ws://10.0.0.77:8000/") == "ws://10.0.0.77:8000/ws"


def test_websocket_url_accepts_server_url_inputs():
    assert normalize_websocket_url("http://server.example:8000") == "ws://server.example:8000/ws"
    assert normalize_websocket_url("https://server.example") == "wss://server.example/ws"
    assert normalize_websocket_url("server.example:8000") == "ws://server.example:8000/ws"


def test_websocket_url_preserves_custom_non_root_paths():
    assert normalize_websocket_url("wss://server.example/realtime/") == "wss://server.example/realtime"
    assert normalize_websocket_url("ws://server.example/ws?token=abc") == "ws://server.example/ws?token=abc"
