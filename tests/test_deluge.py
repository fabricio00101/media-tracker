from unittest.mock import patch, MagicMock

@patch("routes.deluge.requests.Session")
@patch("routes.deluge.config.DELUGE_URL", "http://deluge:8112")
@patch("routes.deluge.config.DELUGE_PASSWORD", "mock_pass")
def test_add_to_deluge_magnet_success(mock_session_cls, client):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    
    # Mock Auth Response
    mock_auth_res = MagicMock()
    mock_auth_res.status_code = 200
    mock_auth_res.json.return_value = {"result": True}
    
    # Mock Add Response
    mock_add_res = MagicMock()
    mock_add_res.status_code = 200
    mock_add_res.json.return_value = {"result": True}
    
    # session.post returns mock_auth_res first, then mock_add_res
    mock_session.post.side_effect = [mock_auth_res, mock_add_res]
    
    response = client.post("/api/deluge/add", json={"magnet": "magnet:?xt=urn:btih:123"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Añadido exitosamente a Deluge."
