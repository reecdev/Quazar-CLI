import docker
import ollama
import random
import os
import time

workspace_path = "/home/user1/Downloads/Quazar_Workspace"

client = docker.from_env()

container = client.containers.run(
    "ubuntu:latest",
    command="sleep infinity",
    detach=True,
    mem_limit="512m",
    network_mode="bridge",
    volumes={
        f"{workspace_path}": {
            "bind": "/workspace",
            "mode": "rw"
        }
    },
    working_dir="/workspace",
    name="my-agent-container"
)

print(f"Container started: {container.id[:12]}")

# -

model = "qwen3.5:4b"

# -

tool_registry = {}
tool_registry2 = []

def tool(func_or_name=None):
    def decorator(func):
        name = func_or_name if isinstance(func_or_name, str) else func.__name__
        tool_registry[name] = func
        tool_registry2.append(func)
        return func

    if callable(func_or_name):
        return decorator(func_or_name)

    return decorator

def type_text(text):
    for c in list(text):
        print(f"\033[3m\033[90m{c}\033[0m", end="", flush=True)
        time.sleep(random.uniform(0.0025, 0.05))
    time.sleep(0.25)
    print("")

@tool
def run_command(bash_command: str) -> str:
    print("\033[3m\033[90msh-5.2$\033[0m ", end="", flush=True)
    type_text(bash_command)
    global container
    exit_code, output = container.exec_run(
        cmd=["bash", "-c", bash_command],
        stdout=True,
        stderr=True,
    )
    print(f"\033[3m\033[90m{output.decode("utf-8").strip()}\033[0m")
    return "```\n" + output.decode("utf-8").strip() + "\n```\n\nFinished executing "+ bash_command +". Proceed with your next action."

def chat(messages):
    finished = False
    while finished == False:
        print("")
        ou = ""
        toolCalls = []
        stream = ollama.chat(model=model, messages=messages, tools=tool_registry2, stream=True)
        for chunk in stream:
            ch = chunk["message"]

            if ch.get("content"):
                if ch["content"].strip():
                    ou += ch["content"]
                    print(ch["content"], end="", flush=True)

            if ch.get("tool_calls"):
                toolCalls.extend(ch["tool_calls"])
        messages.append({"role": "assistant", "content": ou, "tool_calls": toolCalls})
        for toolcall in toolCalls:
            if toolcall.function.name in tool_registry:
                messages.append({"role": "tool", "content": tool_registry[toolcall.function.name](**toolcall.function.arguments)})
                ou = ""
        if ou != "":
            finished = ou
        print("\n\n")

messages = [{"role": "system", "content": "You are a helpful AI assistant named Quasar controlling a VM running Ubuntu 24.04 Server. You are using the 'root' user, which means you do not need to use 'sudo'. Your job is to take orders from the user and run commands on their behalf. Additional notes: Use as many toolcalls in one message as needed."}]

os.system('cls' if os.name == 'nt' else 'clear')

print(f"Quazar running on {model}")

while True:
    u = input(">> ")
    if u == "":
        break
    messages.append({"role": "user", "content": u})
    chat(messages)

container.kill()
container.remove()
