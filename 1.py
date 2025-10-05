import os
from dotenv import load_dotenv
ADMINS=5612345682,5306481482
print(ADMINS)
load_dotenv()
print(os.getenv("ADMINS"))
ADMINS = os.getenv("ADMINS")
print(ADMINS)