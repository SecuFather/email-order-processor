from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from api import app
import gus

client = TestClient(app)

MOCK_LOGIN_XML = """
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body>
    <ZalogujResponse xmlns="http://CIS/BIR/PUBL/2014/07">
      <ZalogujResult>test-session-id-123</ZalogujResult>
    </ZalogujResponse>
  </s:Body>
</s:Envelope>
"""

MOCK_SEARCH_XML = """
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body>
    <DaneSzukajPodmiotyResponse xmlns="http://CIS/BIR/PUBL/2014/07">
      <DaneSzukajPodmiotyResult>&lt;root&gt;&lt;dane&gt;&lt;Regon&gt;123456789&lt;/Regon&gt;&lt;Nip&gt;5260250274&lt;/Nip&gt;&lt;Nazwa&gt;TEST FIRMA SP. Z O.O.&lt;/Nazwa&gt;&lt;Wojewodztwo&gt;MAZOWIECKIE&lt;/Wojewodztwo&gt;&lt;Powiat&gt;warszawski&lt;/Powiat&gt;&lt;Gmina&gt;Warszawa&lt;/Gmina&gt;&lt;Miejscowosc&gt;Warszawa&lt;/Miejscowosc&gt;&lt;KodPocztowy&gt;00-001&lt;/KodPocztowy&gt;&lt;Ulica&gt;ul. Kwiatowa&lt;/Ulica&gt;&lt;NrNieruchomosci&gt;5&lt;/NrNieruchomosci&gt;&lt;NrLokalu&gt;2&lt;/NrLokalu&gt;&lt;/dane&gt;&lt;/root&gt;</DaneSzukajPodmiotyResult>
    </DaneSzukajPodmiotyResponse>
  </s:Body>
</s:Envelope>
"""

MOCK_LOGOUT_XML = """
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body>
    <WylogujResponse xmlns="http://CIS/BIR/PUBL/2014/07">
      <WylogujResult>true</WylogujResult>
    </WylogujResponse>
  </s:Body>
</s:Envelope>
"""


@pytest.mark.anyio
async def test_fetch_gus_company_success():
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_login = AsyncMock(text=MOCK_LOGIN_XML)
        mock_search = AsyncMock(text=MOCK_SEARCH_XML)
        mock_logout = AsyncMock(text=MOCK_LOGOUT_XML)
        mock_post.side_effect = [mock_login, mock_search, mock_logout]

        res = await gus.fetch_gus_company("5260250274")
        assert res["nip"] == "5260250274"
        assert res["name"] == "TEST FIRMA SP. Z O.O."
        assert res["address"] == "ul. Kwiatowa 5/2"
        assert res["zip_code"] == "00-001"
        assert res["city"] == "Warszawa"
        assert "regon" not in res


def test_lookup_company_api_invalid_nip():
    res = client.get("/api/companies/lookup/12345")
    assert res.status_code == 400
    assert res.json()["detail"] == "Invalid NIP"


def test_lookup_company_api_success():
    with patch("gus.fetch_gus_company", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {
            "nip": "5260250274",
            "name": "TEST FIRMA SP. Z O.O.",
            "address": "ul. Kwiatowa 5/2",
            "zip_code": "00-001",
            "city": "Warszawa",
        }
        res = client.get("/api/companies/lookup/5260250274")
        assert res.status_code == 200
        assert res.json()["name"] == "TEST FIRMA SP. Z O.O."
