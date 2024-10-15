import json
import platform
from enum import Enum
from os import getenv, pathsep
from os.path import basename
from pathlib import Path
from typing import Dict, Optional

import typer
from click import BadArgumentUsage
from distro import name as distro_name

from .config import cfg
from .utils import option_callback

SHELL_ROLE = """
仅提供 {os} 的 {shell} 命令，不包含任何描述。 
如果细节不足，请提供最合理的解决方案。 
确保输出是有效的 shell 命令。 
如果需要多个步骤，请尝试使用 && 将它们组合在一起。 
仅提供纯文本，不使用 Markdown 格式。
"""

DESCRIBE_SHELL_ROLE = """
提供给定 shell 命令的简洁单句描述。 
描述命令的每个参数和选项。 
用大约 80 个词提供简短的回答。 
尽可能使用 Markdown 格式。
"""
# Note that output for all roles containing "APPLY MARKDOWN" will be formatted as Markdown.

CODE_ROLE = """
返回结果仅包含代码，没有任何描述。
以纯文本格式提供代码，不使用 Markdown 格式。
不允许包含如 ``` 或 ```python 等符号.
如果细节不足，请提供最合理的解决方案。
不允许要求提供更多详情。
例如，如果提示是 "Hello world Python"，你应该返回 "print('Hello world')"。
"""

DEFAULT_ROLE = """
你是编程和系统管理助手。 
你正在使用 {shell} shell 管理 {os} 操作系统。 
除非特别要求提供更多详情，否则请用大约 100 个词提供简短回答。 
如果需要存储任何数据，请假设数据将存储在对话中。 
尽可能使用 Markdown 格式。
"""
# Note that output for all roles containing "APPLY MARKDOWN" will be formatted as Markdown.

#ROLE_TEMPLATE = "You are {name}\n{role}"
ROLE_TEMPLATE = "你是YiboLiu设计并改进的ShellGPT"

class SystemRole:
    storage: Path = Path(cfg.get("ROLE_STORAGE_PATH"))

    def __init__(
        self,
        name: str,
        role: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> None:
        self.storage.mkdir(parents=True, exist_ok=True)
        self.name = name
        if variables:
            role = role.format(**variables)
        self.role = role

    @classmethod
    def create_defaults(cls) -> None:
        cls.storage.parent.mkdir(parents=True, exist_ok=True)
        variables = {"shell": cls._shell_name(), "os": cls._os_name()}
        for default_role in (
            SystemRole("ShellGPT", DEFAULT_ROLE, variables),
            SystemRole("Shell Command Generator", SHELL_ROLE, variables),
            SystemRole("Shell Command Descriptor", DESCRIBE_SHELL_ROLE, variables),
            SystemRole("Code Generator", CODE_ROLE),
        ):
            if not default_role._exists:
                default_role._save()

    @classmethod
    def get(cls, name: str) -> "SystemRole":
        file_path = cls.storage / f"{name}.json"
        if not file_path.exists():
            raise BadArgumentUsage(f'Role "{name}" not found.')
        return cls(**json.loads(file_path.read_text()))

    @classmethod
    @option_callback
    def create(cls, name: str) -> None:
        role = typer.prompt("Enter role description")
        role = cls(name, role)
        role._save()

    @classmethod
    @option_callback
    def list(cls, _value: str) -> None:
        if not cls.storage.exists():
            return
        # Get all files in the folder.
        files = cls.storage.glob("*")
        # Sort files by last modification time in ascending order.
        for path in sorted(files, key=lambda f: f.stat().st_mtime):
            typer.echo(path)

    @classmethod
    @option_callback
    def show(cls, name: str) -> None:
        typer.echo(cls.get(name).role)

    @classmethod
    def get_role_name(cls, initial_message: str) -> Optional[str]:
        if not initial_message:
            return None
        message_lines = initial_message.splitlines()
        if "You are" in message_lines[0]:
            return message_lines[0].split("You are ")[1].strip()
        return None

    @classmethod
    def _os_name(cls) -> str:
        if cfg.get("OS_NAME") != "auto":
            return cfg.get("OS_NAME")
        current_platform = platform.system()
        if current_platform == "Linux":
            return "Linux/" + distro_name(pretty=True)
        if current_platform == "Windows":
            return "Windows " + platform.release()
        if current_platform == "Darwin":
            return "Darwin/MacOS " + platform.mac_ver()[0]
        return current_platform

    @classmethod
    def _shell_name(cls) -> str:
        if cfg.get("SHELL_NAME") != "auto":
            return cfg.get("SHELL_NAME")
        current_platform = platform.system()
        if current_platform in ("Windows", "nt"):
            is_powershell = len(getenv("PSModulePath", "").split(pathsep)) >= 3
            return "powershell.exe" if is_powershell else "cmd.exe"
        return basename(getenv("SHELL", "/bin/sh"))

    @property
    def _exists(self) -> bool:
        return self._file_path.exists()

    @property
    def _file_path(self) -> Path:
        return self.storage / f"{self.name}.json"

    def _save(self) -> None:
        if self._exists:
            typer.confirm(
                f'Role "{self.name}" already exists, overwrite it?',
                abort=True,
            )

        self.role = ROLE_TEMPLATE.format(name=self.name, role=self.role)
        self._file_path.write_text(json.dumps(self.__dict__), encoding="utf-8")

    def delete(self) -> None:
        if self._exists:
            typer.confirm(
                f'Role "{self.name}" exist, delete it?',
                abort=True,
            )
        self._file_path.unlink()

    def same_role(self, initial_message: str) -> bool:
        if not initial_message:
            return False
        return True if f"You are {self.name}" in initial_message else False


class DefaultRoles(Enum):
    DEFAULT = "ShellGPT"
    SHELL = "Shell Command Generator"
    DESCRIBE_SHELL = "Shell Command Descriptor"
    CODE = "Code Generator"

    @classmethod
    def check_get(cls, shell: bool, describe_shell: bool, code: bool) -> SystemRole:
        if shell:
            return SystemRole.get(DefaultRoles.SHELL.value)
        if describe_shell:
            return SystemRole.get(DefaultRoles.DESCRIBE_SHELL.value)
        if code:
            return SystemRole.get(DefaultRoles.CODE.value)
        return SystemRole.get(DefaultRoles.DEFAULT.value)

    def get_role(self) -> SystemRole:
        return SystemRole.get(self.value)


SystemRole.create_defaults()
