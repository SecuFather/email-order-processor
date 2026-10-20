import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ.get("HOST")
PORT = int(p) if (p := os.environ.get("PORT")) else None
SSL_CERTFILE = os.environ.get("SSL_CERTFILE")
SSL_KEYFILE = os.environ.get("SSL_KEYFILE")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST")
WOOCOMMERCE_URL = os.environ.get("WOOCOMMERCE_URL")
WOOCOMMERCE_CONSUMER_KEY = os.environ.get("WOOCOMMERCE_CONSUMER_KEY")
WOOCOMMERCE_CONSUMER_SECRET = os.environ.get("WOOCOMMERCE_CONSUMER_SECRET")
MY_NIP = os.environ.get("MY_NIP")
MY_EMAIL = os.environ.get("MY_EMAIL")
FAKTUROWNIA_URL = os.environ.get("FAKTUROWNIA_URL")
FAKTUROWNIA_API_TOKEN = os.environ.get("FAKTUROWNIA_API_TOKEN")
FAKTUROWNIA_WOOCOMMERCE_META_KEY = os.environ.get("FAKTUROWNIA_WOOCOMMERCE_META_KEY", "_woo_fakturownia_faktura")
FAKTUROWNIA_WOOCOMMERCE_HASH_META_KEY = os.environ.get("FAKTUROWNIA_WOOCOMMERCE_HASH_META_KEY", "_woo_fakturownia_faktura_hash")
FAKTUROWNIA_SELLER_PERSON = os.environ.get("FAKTUROWNIA_SELLER_PERSON", "")
DB_PATH = os.environ["DB_PATH"]
GUS_API_KEY = os.environ["GUS_API_KEY"]
GUS_URL = os.environ["GUS_URL"]
