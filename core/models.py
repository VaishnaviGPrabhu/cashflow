from dataclasses import dataclass
@dataclass
class ValidationIssue:
    severity:str; dataset:str; message:str; row:int|None=None; field:str|None=None
