import html
import re
import xml.etree.ElementTree as ET
import httpx
import config

SOAP_HEADERS = {"Content-Type": "application/soap+xml; charset=utf-8"}


async def fetch_gus_company(nip: str) -> dict:
    key = config.GUS_API_KEY
    url = config.GUS_URL
    clean_nip = re.sub(r"\D", "", nip)

    login_xml = (
        f'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ns="http://CIS/BIR/PUBL/2014/07">'
        f'<soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">'
        f"<wsa:To>{url}</wsa:To>"
        f"<wsa:Action>http://CIS/BIR/PUBL/2014/07/IUslugaBIRzewnPubl/Zaloguj</wsa:Action>"
        f"</soap:Header>"
        f"<soap:Body><ns:Zaloguj><ns:pKluczUzytkownika>{key}</ns:pKluczUzytkownika></ns:Zaloguj></soap:Body>"
        f"</soap:Envelope>"
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(url, content=login_xml, headers=SOAP_HEADERS)
        sid_match = re.search(r"<ZalogujResult>(.*?)</ZalogujResult>", res.text)
        sid = sid_match.group(1) if sid_match else ""
        if not sid:
            raise ValueError("GUS authentication failed. Invalid API key.")

        try:
            search_xml = (
                f'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ns="http://CIS/BIR/PUBL/2014/07" xmlns:dat="http://CIS/BIR/PUBL/2014/07/DataContract">'
                f'<soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">'
                f"<wsa:To>{url}</wsa:To>"
                f"<wsa:Action>http://CIS/BIR/PUBL/2014/07/IUslugaBIRzewnPubl/DaneSzukajPodmioty</wsa:Action>"
                f"</soap:Header>"
                f"<soap:Body><ns:DaneSzukajPodmioty><ns:pParametryWyszukiwania><dat:Nip>{clean_nip}</dat:Nip></ns:pParametryWyszukiwania></ns:DaneSzukajPodmioty></soap:Body>"
                f"</soap:Envelope>"
            )
            res2 = await client.post(
                url,
                content=search_xml,
                headers={**SOAP_HEADERS, "sid": sid},
            )
            data_match = re.search(r"<DaneSzukajPodmiotyResult>(.*?)</DaneSzukajPodmiotyResult>", res2.text, re.DOTALL)
            if not data_match:
                raise ValueError("No data returned from GUS")

            xml_content = html.unescape(data_match.group(1))
            root = ET.fromstring(xml_content)
            dane = root.find("dane")
            if dane is None or dane.find("ErrorCode") is not None:
                err_msg = dane.findtext("ErrorMessagePl") if dane is not None else "Podmiot nie został odnaleziony"
                raise ValueError(err_msg or "Podmiot nie został odnaleziony")

            street = (dane.findtext("Ulica") or "").strip()
            house = (dane.findtext("NrNieruchomosci") or "").strip()
            flat = (dane.findtext("NrLokalu") or "").strip()
            number_part = f"{house}/{flat}" if flat else house
            address = f"{street} {number_part}".strip() if (street and number_part) else (street or number_part)

            return {
                "nip": clean_nip,
                "name": (dane.findtext("Nazwa") or "").strip(),
                "address": address,
                "zip_code": (dane.findtext("KodPocztowy") or "").strip(),
                "city": (dane.findtext("Miejscowosc") or "").strip(),
            }
        finally:
            logout_xml = (
                f'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ns="http://CIS/BIR/PUBL/2014/07">'
                f'<soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">'
                f"<wsa:To>{url}</wsa:To>"
                f"<wsa:Action>http://CIS/BIR/PUBL/2014/07/IUslugaBIRzewnPubl/Wyloguj</wsa:Action>"
                f"</soap:Header>"
                f"<soap:Body><ns:Wyloguj><ns:pIdentyfikatorSesji>{sid}</ns:pIdentyfikatorSesji></ns:Wyloguj></soap:Body>"
                f"</soap:Envelope>"
            )
            await client.post(url, content=logout_xml, headers={**SOAP_HEADERS, "sid": sid})
