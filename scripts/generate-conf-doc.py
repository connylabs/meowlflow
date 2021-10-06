import yaml
from meowlflow.config import GCONFIG


print(yaml.safe_dump(GCONFIG.settings, indent=2))
