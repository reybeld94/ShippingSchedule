from ShippingClient.core.api_client import RobustApiClient


def test_api_client():
    # Test con servidor inválido (debe manejar error gracefully)
    client = RobustApiClient("http://invalid-server:9999", "fake-token")
    response = client.get_shipments()

    print(f"Success: {response.success}")
    print(f"Error: {response.error}")

    assert not response.success
    assert response.error

    print("\u2705 Test b\u00e1sico pasado")


def test_api_client_without_token():
    """El cliente debe poder inicializarse sin token para el login"""
    client = RobustApiClient("http://invalid-server:9999")
    response = client.login("user", "pass")

    print(f"Success: {response.success}")
    print(f"Error: {response.error}")

    assert not response.success
    assert response.error

    print("\u2705 Test sin token pasado")


if __name__ == "__main__":
    test_api_client()
