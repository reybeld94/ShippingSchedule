import sys
import types


def test_suffix_is_trimmed(monkeypatch):
    executed = []

    class DummyCursor:
        def execute(self, query, params):
            executed.append(params[0])
        def fetchone(self):
            return {
                "ShippingAddress1": "Addr1",
                "ShippingAddressCity": "City",
                "ShippingAddressStateDescription": "ST",
                "ShippingAddressZipCode": "12345",
            }

    class DummyConn:
        def cursor(self, as_dict=True):
            return DummyCursor()
        def close(self):
            pass

    dummy_pymssql = types.SimpleNamespace(connect=lambda *args, **kwargs: DummyConn())
    sys.modules["pymssql"] = dummy_pymssql
    from ShippingClient.core import mie_trak_client

    address = mie_trak_client.get_mie_trak_address("12345.1")
    assert executed[0] == "12345"
    assert "Addr1" in address
