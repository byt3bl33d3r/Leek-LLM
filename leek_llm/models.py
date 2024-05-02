import re
import json
from enum import Enum
from . import data as pkgdata
from importlib import resources
from xml.etree import ElementTree as ET
from typing import List, Optional, Union
from markdownify import markdownify as md
from pydantic import BaseModel, SecretStr, model_validator, field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_xml import BaseXmlModel, element

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    username: str
    password: SecretStr
    openai_api_key: SecretStr

class ActionType(int, Enum):
	START_FIGHT = 0
	USE_WEAPON_OLD = 1
	USE_CHIP_OLD = 2
	SET_WEAPON_OLD = 3
	END_FIGHT = 4
	PLAYER_DEAD = 5
	NEW_TURN = 6
	LEEK_TURN = 7
	END_TURN = 8
	SUMMON = 9
	MOVE_TO = 10
	KILL = 11
	USE_CHIP = 12
	SET_WEAPON = 13
	STACK_EFFECT = 14
	OPEN_CHEST = 15
	USE_WEAPON = 16
	TP_LOST = 100
	LIFE_LOST = 101
	MP_LOST = 102
	CARE = 103
	BOOST_VITA = 104
	RESURRECTION = 105
	NOVA_DAMAGE = 107
	DAMAGE_RETURN = 108
	LIFE_DAMAGE = 109
	POISON_DAMAGE = 110
	AFTEREFFECT = 111
	NOVA_VITALITY = 112
	SAY_OLD = 200
	LAMA = 201
	SHOW_OLD = 202
	SAY = 203
	SHOW = 205
	ADD_WEAPON_EFFECT = 301
	ADD_CHIP_EFFECT = 302
	REMOVE_EFFECT = 303
	UPDATE_EFFECT = 304
	ADD_STACKED_EFFECT = 305
	REDUCE_EFFECTS = 306
	REMOVE_POISONS = 307
	REMOVE_SHACKLES = 308
	BUG = 1002

class Action(BaseModel):
    action_type: ActionType
    action_data: List[Union[int, str, List[int]]] = []

class FightData(BaseModel):
    actions: List[Action]

    @classmethod
    def from_api(cls, data):
        return cls(
            actions=[
                Action(
                    action_type=action[0],
                    action_data=action[1:]
                )
                for action in data['actions']
            ]
        )

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

    @classmethod
    def from_fight_logs(cls, data):
        with (resources.files(pkgdata) / "leekscript.json").open() as f:
            leekscript_errors = json.load(f)

        formatted_error = leekscript_errors[f"error_{data[3]}"]
        formatted_error = data[2] + formatted_error.format(*data[4])

        return cls(
            error_number=data[3],
            error=formatted_error,
            line=0,
            start=0,
            end=0,
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
