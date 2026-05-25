from environs import Env


env = Env()
env.read_env()

TOKEN = env.str("TOKEN")
DEVELOPERS = [int(i) for i in env.list("DEVELOPERS")]
ADMINS = [int(i) for i in env.list("ADMINS")]
API_ID = env.int("API_ID")
API_HASH = env.str("API_HASH")
BANK_CARD = "<code>" + env.str("BANK_CARD") + "</code>"
PRICE_1_MONTH = 1500
PRICE_3_MONTHS = 4275
PRICE_6_MONTHS = 8100
PRICE_12_MONTHS = 15300
