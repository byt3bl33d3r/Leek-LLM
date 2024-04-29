import re
import json
from . import data as pkgdata
from importlib import resources
from xml.etree import ElementTree as ET
from typing import List, Optional
from markdownify import markdownify as md
from pydantic import BaseModel, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_xml import BaseXmlModel, element

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    username: str
    password: SecretStr
    openai_api_key: SecretStr

class LeekScriptError(BaseModel):
    error_number: int
    error: str
    line: int
    start: int
    end: int

    @classmethod
    def from_api_error(cls, data):
        with (resources.files(pkgdata) / "leekscript.json").open() as f:
            leekscript_errors = json.load(f)

        formatted_error=leekscript_errors[f"error_{data[6]}"]
        if len(data) == 8 and isinstance(data[7], list):
            formatted_error = formatted_error.format(*data[7])

        return cls(
            error_number=data[6],
            error=formatted_error,
            line=data[2],
            start=data[3],
            end=data[5]
        )

class XmlModel(BaseXmlModel):
    def to_pretty_xml(self) -> str:
        tree = self.to_xml_tree()
        ET.indent(tree, "   ")
        pretty_encoded_xml = ET.tostring(tree).decode()
        return pretty_encoded_xml.replace("&lt;", "<").replace("&gt;", ">")

class XmlDoc(XmlModel):
    @model_validator(mode='before')
    @classmethod
    def cleanup_and_markdownify(cls, data):
        cleaned_data = {}

        for k,v in data.items():
            cleaned_text = v

            if isinstance(v, str):
                v = v.replace('\n\n', '')
                cleaned_text = re.sub(r'{{.*?}}', '', v)

            cleaned_data[k] = cleaned_text

        return cleaned_data

class XmlDocWithHtml(XmlModel):
    @model_validator(mode='before')
    @classmethod
    def cleanup_and_markdownify(cls, data):
        cleaned_data = {}

        for k,v in data.items():
            cleaned_text = re.sub(r'{{.*?}}', '', v)
            cleaned_data[k] = md(cleaned_text)
        
        return cleaned_data

class ConstantDoc(XmlDoc):
    id: int = element()
    name: str = element()
    value: str = element()
    type: int = element()
    category: int = element()
    deprecated: bool = element()
    replacement: Optional[int] = None

class FunctionDoc(XmlDoc):
    name: str = element()
    description: str = element()
    params: str = element()
    returns: str = element()
    notes: str = element()
    examples: str = element()

class LeekScriptDocs(XmlDocWithHtml):
    leekscript_4: str = element()
    cheet_sheet: str = element()
    variables: str = element()
    standard_functions: str = element()
    conditions: str = element()
    booleans_and_null: str = element()
    operators: str = element()
    strings: str = element()
    loops: str = element()
    lists: str = element()
    create_your_functions: str = element()

class GameRulesDocs(XmlDocWithHtml):
    leek: str = element()

class StandardFunctionsDoc(XmlModel):
    StandardFunctions: List[FunctionDoc]

class ConstantsDoc(XmlModel):
    constants: List[ConstantDoc]
