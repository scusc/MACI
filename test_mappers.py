from sqlalchemy.orm import configure_mappers
from maci_core.database import Base
import maci_core.models

try:
    configure_mappers()
    print("SUCCESS: All SQLAlchemy mappers configured correctly.")
except Exception as e:
    print("ERROR configuring mappers:")
    print(e)
