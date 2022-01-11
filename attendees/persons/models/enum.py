from enum import Enum

# Todo: use Django 3 choice https://stackoverflow.com/a/58051918


class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return [(choice.name, choice.value) for choice in cls]


class GenderEnum(ChoiceEnum):
    MALE = "male"
    FEMALE = "female"
    UNSPECIFIED = "unspecified"
