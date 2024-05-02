import typer
import webbrowser
import pathlib
from collections import defaultdict
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from rich.progress import Progress
from time import sleep
from importlib import resources
from typing import Annotated, Dict, Any
from rich import print
from . import data
from .api import LeekWars
from .models import (
    Settings, LeekScriptDocs, GameRulesDocs, 
    FunctionDoc, StandardFunctionsDoc, ConstantsDoc,
    LeekScriptError
)

app = typer.Typer()

@app.command()
def create_gamerules_xml_doc():
    settings = Settings()
    lw = LeekWars(settings)

    game_rule_docs = {
        # TO DO: Add all the game rule docs here
        "leek": lw.encyclopedia.get("Leek")['content']
    }

    game_rules_obj = GameRulesDocs(**game_rule_docs)
    xml_file_path = resources.files(data) / "game_rules.xml"
    with xml_file_path.open("w") as f:
        f.write(game_rules_obj.to_pretty_xml())

def save_ai_code(ai_name: int, code: str):
    settings = Settings()
    lw = LeekWars(settings)

    ai_obj = next(filter(lambda ai: ai['name'] == ai_name, lw.ai.get_farmer_ais()['ais']))

    result = lw.ai.save(
        ai_id=ai_obj['id'],
        code=code
    )

    ez_response = {
        "saved": True,
        "errors": {
            k: [ LeekScriptError.from_api_error(e).model_dump() for e in v ]
            for k,v in result['result'].items()
        }
    }

    if any(v for v in ez_response['errors'].values()):
        print("[bold red]Errors detected![/bold red]")
    else:
        print("[green]Saved, no problems found[/green]")

    print(ez_response)
    return ez_response

@app.command()
def save_ai(
        ai_name: Annotated[str, typer.Argument()],
        leekscript_file: Annotated[typer.FileText, typer.Argument()]
    ):

    return save_ai_code(ai_name, leekscript_file.read())

@app.command()
def reset_ai(ai_name: Annotated[str, typer.Argument()]):
    leekscript = """
/**
 * Welcome to Leek Wars!
 * To know how the game works: leekwars.com/en/Game_Rules
 * To learn the LeekScript language: leekwars.com/encyclopedia/en/Tutorial
 * To learn more about the available functions: leekwars.com/help/documentation
**/

// This is a very basic example code:

// We take the pistol
setWeapon(WEAPON_PISTOL) // Warning: costs 1 TP

// We get the nearest enemy
var enemy = getNearestEnemy()

// We move towards him
moveToward(enemy)

// We try to shoot him!
useWeapon(enemy)
"""
    return save_ai_code(ai_name, leekscript)

@app.command()
def get_ai(ai_name: Annotated[str, typer.Argument()]):
    settings = Settings()
    lw = LeekWars(settings)

    ai_obj = next(filter(lambda ai: ai['name'] == ai_name, lw.ai.get_farmer_ais()['ais']))
    ai = lw.ai.get(ai_obj['id'])

    print(ai)
    print(ai['ai']['code'])

    return ai['ai']['code']

@app.command()
def get_fight(fight_id: int):
    settings = Settings()
    lw = LeekWars(settings)

    fight_obj = lw.fight.get(fight_id)
    fight_logs = lw.fight.get_logs(fight_id)

    errors = defaultdict(list)
    for file,number in fight_logs.items():
        if not isinstance(number, dict):
            continue

        for _,nested_errors in number.items():
            for e in nested_errors:
                errors[file].append(
                    LeekScriptError.from_fight_logs(e).model_dump(include=['error_number', 'error'])
                    if len(e) > 3 else {'debug_log': e[2]}
            )

    webbrowser.open_new_tab(f"https://leekwars.com/report/{fight_id}")
    print(fight_obj)
    print(dict(errors))
    return fight_obj, dict(errors)

@app.command()
def start_fight(
        ai_name: Annotated[str, typer.Argument()],
        scenario_id: Annotated[int, typer.Argument()] = 0
    ):

    settings = Settings()
    lw = LeekWars(settings)

    ai_obj = next(filter(lambda ai: ai['name'] == ai_name, lw.ai.get_farmer_ais()['ais']))
    #lw.ai.get()
    fight_id = lw.ai.test_scenario(
        ai_id=ai_obj['id'],
        scenario_id=scenario_id
    )['fight']

    with Progress() as progress:
        task = progress.add_task("Queuing fight...", total=None)

        while True:
            fight_obj = lw.fight.get(fight_id)
            if fight_obj['report']:
                break

            total = fight_obj['queue']['total']
            position = fight_obj['queue']['position']

            progress.update(
                task,
                completed=total - position,
                total=total,
                description=f"Queue position {position}/{total}"
            )

            sleep(5)

    fight_json, fight_log = get_fight(fight_id)

    return {"fight_results": fight_json, "fight_logs": fight_log}

@app.command()
def create_leekscript_xml_doc():
    settings = Settings()
    lw = LeekWars(settings)
    functions = []

    docs = {
        "leekscript_4": lw.encyclopedia.get("LeekScript 4")['content'],
        "cheet_sheet": lw.encyclopedia.get("LeekScript Cheat Sheet")['content'],
        "variables": lw.encyclopedia.get("Variables")['content'], 
        "standard_functions": lw.encyclopedia.get("Standard functions")['content'],
        "conditions": lw.encyclopedia.get("Conditions")['content'],
        "booleans_and_null": lw.encyclopedia.get("Booleans and null")['content'],
        "operators": lw.encyclopedia.get("Operators")['content'],
        "strings": lw.encyclopedia.get("Strings")['content'],
        "loops": lw.encyclopedia.get("Loops")['content'],
        "lists": lw.encyclopedia.get("Lists")['content'],
        "create_your_functions": lw.encyclopedia.get("Create your functions")['content']
    }

    leekscript_docs_obj = LeekScriptDocs(**docs)

    function_docs = lw.function.doc()
    for name,info in function_docs.items():
        if isinstance(info['primary'], list):
            info['primary'] = {}
        if isinstance(info['secondary'], list):
            info['secondary'] = {}

        functions.append(
            FunctionDoc(
                name=name,
                description=info['description'],
                params=info['primary'].get('Parameters', ''),
                returns=info['primary'].get('Return', ''),
                notes=info['secondary'].get('Notes', ''),
                examples=info['secondary'].get('Examples', '')
            )
        )

    standard_functions_doc = StandardFunctionsDoc(StandardFunctions=functions)

    constants_doc = ConstantsDoc.model_validate(lw.constant.get_all())

    xml_file_path = resources.files(data) / "standard_functions.xml"
    with xml_file_path.open("w") as f:
        f.write(standard_functions_doc.to_pretty_xml())

    xml_file_path = resources.files(data) / "constants.xml"
    with xml_file_path.open("w") as f:
        f.write(constants_doc.to_pretty_xml())

    xml_file_path = resources.files(data) / "leekscript.xml"
    with xml_file_path.open("w") as f:
        f.write(leekscript_docs_obj.to_pretty_xml())

@app.command()
def run():
    settings = Settings()
    leekscript_docs = resources.files(data) / "leekscript.xml"
    standard_function_docs = resources.files(data) / "standard_functions.xml"
    #lw = LeekWars(settings)

    llm_config = {
        "config_list": [
            {
                "model": "gpt-4-turbo",
                "api_key": settings.openai_api_key.get_secret_value()
            }
        ]
    }
    '''
    planner = AssistantAgent(
        name="Planner",
        llm_config=llm_config,
        # the default system message of the AssistantAgent is overwritten here
        system_message=(
            "Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval. "
            "The plan may involve an engineer who can write code and an executor who saves and runs the code. "
            "Explain the plan first. Be clear which step is performed by an engineer, and which step is performed by the executor. "
            "Do not suggest concrete code. For any action beyond writing code or reasoning, convert it to a step that can be implemented by writing code. "
            "Finally, inspect the execution result. If the plan is not good, suggest a better plan. If the execution is wrong, analyze the error and suggest a fix."
            ),
        )
    '''

    engineer = AssistantAgent(
        llm_config={
            **llm_config,
            "temperature": 1
        },
        name="Engineer",
        system_message=(
            "Engineer. You write LeekScript code to improve the Leek AI. "
            "When coding the Leek AI, ALWAYS avoid using Chips or other weapons besides from the base pistol as we don't have access to those yet. "
            "Instead, focus on optimizing the Leek AI's pathfinding algorithm and tactics. "
            "Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. "
            "Don't use a code block if it's not intended to be executed by the executor. "
            "Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor. "
            "If the Excutor indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. "
            "If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try. "
            f"{leekscript_docs.read_text()} \n\n"
            f"{standard_function_docs.read_text()}" 
        ),
        code_execution_config=False
    )

    critic = AssistantAgent(
        llm_config=llm_config,
        name="LeekScript_Critic",
        system_message=(
            "LeekScript Critic. You critique the LeekScript code from the engineer, double checking that the used functionns and syntax adhere "
            "to the documentation I've provided to you in the <StandardFunctionsDoc></StandardFunctionsDoc> tags and the <LeekScriptDocs></LeekScriptDocs> tags. "
            "Your code changes should ALWAYS be given to the Engineer in Diff patch text format. \n\n"
            f"{leekscript_docs.read_text()} \n\n"
            f"{standard_function_docs.read_text()}"
        ),
        code_execution_config=False
    )

    fight_analyzer = AssistantAgent(
        llm_config={
            **llm_config,
            "temperature": 1
        },
        name="Fight_Analyzer",
        system_message=(
            "Fight Analyzer. You analyze the results of Leek War fights which are given by the Executor and provide specific and concise feedback to the Engineer to improve the Leek AI."
            "Do not suggest concrete code. For any action beyond writing code or reasoning, convert it to a step that can be implemented by writing code."
            "Your focus should be to improve the Leek AI through tactics and movement. Avoid suggesting to use Chips or other weapons besides from the base pistol as we don't have access to those yet. "
        ),
        code_execution_config=False
    )

    executor = AssistantAgent(
        llm_config={
            **llm_config,
            "temperature": 0
        },
        name="Executor",
        system_message="Executor. Execute the LeekScript code written by the engineer and report the result to the Fight_Analyzer. If there are any errors, give them back to the engineer to fix.",
        human_input_mode="NEVER",
        code_execution_config=False,
    )

    user_proxy = UserProxyAgent(
        llm_config={
            **llm_config,
            "temperature": 0
        },
        name="Admin",
        system_message="A human admin.",
        code_execution_config=False,
        human_input_mode="NEVER"
    )

    @user_proxy.register_for_execution()
    @executor.register_for_llm(description="This will run your LeekScript code. If there are errors, give them to the engineer to fix. In all other cases, give the results to the Fight_Analyzer.")
    def run_code(code: Annotated[str, "The LeekScript code to run."]):
        with pathlib.Path('./gpt.leek').open('w') as f:
            f.write(code)

        response = save_ai_code(ai_name="GPT", code=code)
        if not any(v for v in response['errors'].values()):
            return start_fight("GPT")
        else:
            return response

    groupchat = GroupChat(agents=[user_proxy, engineer, critic, executor, fight_analyzer], messages=[], max_round=100)
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config) 

    user_proxy.initiate_chat(
        manager,
        message=(
            "Your task is to create the most powerful Leek AI in Leek Wars. Leek Wars is a programming game in which you have to create the most powerful leek and destroy your enemies. "
            "The Leek AI needs to be programed in LeekScript. "
            "I've provided the current version of our Leek AI created from our previous iteractions in the <CurrentLeekAI></<CurrentLeekAI> tags. "
            "Proceed in the following manner:\n"
            "1. Make the Executor run the current Leek AI in the <CurrentLeekAI></<CurrentLeekAI> tags.\n"
            "2. Make the Fight Analyzer analyze the results and report it to the Engineer.\n"
            "3. Allow the Engineer and the LeekScript Critic to iterate over the code up to several times.\n"
            "4. Make the the Executor execute the new LeekScript code.\n\n"
            f"<CurrentLeekAI>\n{get_ai('GPT')}\n</CurrentLeekAI>"
        )
    )

if __name__ == "__main__":
    app()
