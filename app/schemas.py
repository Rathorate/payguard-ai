from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Credentials(Input):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize(cls, value):
        return value.lower()


class Registration(Credentials):
    company: str = Field(min_length=2, max_length=100)


class NewDispute(Input):
    paypal_id: str = Field(min_length=1, max_length=255, pattern=r'^[A-Za-z0-9-]+$')
    customer: str = Field(min_length=1, max_length=100)
    reason: Literal['MERCHANDISE_OR_SERVICE_NOT_RECEIVED', 'MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED', 'UNAUTHORISED', 'UNAUTHORIZED_TRANSACTION', 'NOT_RECOGNISED', 'NOT_RECOGNIZED', 'INQUIRY']
    amount_cents: int = Field(strict=True, gt=0, le=1000000000)
    currency: Literal['USD', 'EUR', 'GBP', 'CAD', 'AUD'] = 'USD'
    due_at: int = Field(strict=True, gt=0)


class NewEvidence(Input):
    title: str = Field(min_length=2, max_length=160)
    kind: Literal['INVOICE', 'TRACKING', 'COMMUNICATION', 'OTHER']
    content: str = Field(min_length=5, max_length=8000)
    version: int = Field(gt=0)


class Version(Input):
    version: int = Field(strict=True, gt=0)


class DraftEdit(Version):
    text: str = Field(min_length=20, max_length=12000)


class Approval(Version):
    reviewed: Literal[True]

    @field_validator('reviewed', mode='before')
    @classmethod
    def explicit_review(cls, value):
        if value is not True:
            raise ValueError('Explicit human review is required')
        return value


class SubmissionInput(Version):
    confirmed: Literal[True]

    @field_validator('confirmed', mode='before')
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True:
            raise ValueError('Explicit submission confirmation is required')
        return value
