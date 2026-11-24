from typing import Annotated

from pydantic import AfterValidator, EmailStr

NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]
