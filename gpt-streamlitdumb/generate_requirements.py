import os
from dotenv import load_dotenv

load_dotenv()

user = os.environ['NEXUS_USER']
password = os.environ['NEXUS_PASSWORD']

url_encoded = f"https://{user}:{password}@nexusrepodirect.thehartford.com/repository/pypi/simple/"

with open("requirements.template.txt") as f:
    content = f.read()

content = content.replace("${NEXUS_USER}", user).replace("${NEXUS_PASSWORD}", password)

with open("requirements.txt", "w") as f:
    f.write(content)
