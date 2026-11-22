from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Requirement(StrictModel):
    id: str = Field(pattern=r"^REQ-[A-Z0-9-]{1,30}$")
    text: str = Field(min_length=10, max_length=2000)


class GenerateRequest(StrictModel):
    requirements: list[Requirement] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [item.id for item in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("Requirement IDs must be unique")
        return self


class Category(StrEnum):
    positive = "positive"
    negative = "negative"
    boundary = "boundary"


class TestCase(StrictModel):
    id: str = Field(pattern=r"^TC-[A-Z0-9-]{1,50}$")
    requirement_id: str
    title: str = Field(min_length=5, max_length=200)
    category: Category
    preconditions: list[str] = Field(min_length=1, max_length=10)
    steps: list[str] = Field(min_length=1, max_length=15)
    expected_result: str = Field(min_length=5, max_length=2000)
    priority: str = Field(pattern="^(P1|P2|P3)$")


class TestSuite(StrictModel):
    cases: list[TestCase] = Field(min_length=1, max_length=60)


class GenerateResponse(StrictModel):
    schema_version: str = "1.0"
    provider: str
    requires_review: bool = True
    suite: TestSuite


def validate_traceability(suite: TestSuite, request: GenerateRequest) -> TestSuite:
    expected = {r.id for r in request.requirements}
    actual = {case.requirement_id for case in suite.cases}
    ids = [case.id for case in suite.cases]
    if expected != actual:
        raise ValueError("Generated cases must cover exactly the submitted requirement IDs")
    if len(ids) != len(set(ids)):
        raise ValueError("Generated case IDs must be unique")
    for requirement_id in expected:
        categories = {c.category for c in suite.cases if c.requirement_id == requirement_id}
        if categories != set(Category):
            raise ValueError("Each requirement needs positive, negative, and boundary cases")
    return suite
