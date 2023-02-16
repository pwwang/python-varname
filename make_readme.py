"""Make README.raw.md to README.md

Allows codeblocks in the input markdown file to be executed
It also formats the inline comments with the variables and outputs

This allows us to check if new commits break the examples listed in README.

Only python/python3 codeblocks are supported, other codeblocks or plain
markdown elements will be kept unchanged.

Supported variables in comments:
1. Any previously defined variable
   >>> a = 'x'  # {a}               # will be compiled into:
   >>> a = 'x'  # x
   >>> a = 'x'  # {a!r}             # will be compiled into:
   >>> a = 'x'  # 'x'
2. Expression results without assignment
   >>> 'x'.upper()  # {_expr}       # will be compiled into:
   >>> 'x'.upper()  # X
   >>> 'x'.upper()  # {_expr!r}     # will be compiled into:
   >>> 'x'.upper()  # 'X'
3. Stdout
   >>> print('x')   # {_out}        # will be compiled into:
   >>> print('x')   # x
   >>>                              # a new line
   >>> print('x')   # {_out!r}      # will be compiled into:
   >>> print('x')   # "x\n"
4. Exceptions
   >>> 1/0     # {_exc}             # will be compiled into:
   >>> 1/0     # ZeroDivisionError
5. Exceptions with messages
   >>> 1/0     # {_exc_msg}         # will be compiled into:
   >>> 1/0     # ZeroDivisionError: division by zero
6. Hide current line from output
   This is helpful when you need extra codes to run the codeblock, but
   you don't want those lines to be shown in the README file.

Note that all these comments can only be used at top-level statement.
"""
import re
import sys
import tempfile
from os import path
from io import StringIO
from contextlib import redirect_stdout


def printn(line):
    """Shortcut to print without new line"""
    print(line, end="")


class CodeBlock:
    """The code block

    Args:
        indent: The indentation of the codeblock
        backticks: The backticks of the codeblock
            Used to match the closing one
        lang: The language of the codeblock
        index: The index of the codeblock in the markdown file
            0-based.
        envs: The input environment variables

    Attributes:
        indent: See Args
        backticks: See Args
        lang: See Args
        index: See Args
        envs: See Args
        codes: The accumulated codes to execute
        produced: The produced output
        alive: Whether this codeblock is still alive/open
        piece: The piece index of the code to be executed in this block
        stdout: The standard output of current code piece
            It will get overwritten by next code piece
    """

    def __init__(self, indent, backticks, lang, index, envs=None):
        self.indent = indent
        self.backticks = backticks
        self.lang = lang
        self.codes = ""
        self.envs = envs or {}
        self.produced = ""
        self.alive = True
        self.index = index
        self.piece = 0
        self.stdout = ""

    def compile_exec(self, code):
        """Compile and execute the code"""
        sourcefile = path.join(
            tempfile._get_default_tempdir(),
            f"codeblock_{self.index}_{self.piece}-"
            f"{next(tempfile._get_candidate_names())}",
        )
        with open(sourcefile, "w") as fsrc:
            fsrc.write(code)
        code = compile(code, sourcefile, mode="exec")
        sio = StringIO()
        with redirect_stdout(sio):
            exec(code, self.envs)
        self.stdout = sio.getvalue()
        self.piece += 1

    def feed(self, line):
        """Feed a single line to the code block, with line break"""
        if self.lang not in ("python", "python3"):
            self.produced += line

        else:
            if not line.strip():  # empty line
                self.codes += "\n"
                self.produced += line
            else:
                line = line[len(self.indent) :]
                if CodeBlock.should_compile(line):
                    if self.codes:
                        self.compile_exec(self.codes)
                        self.codes = ""
                    self.produced += self.indent + self.compile_line(line)
                else:
                    self.codes += line
                    self.produced += self.indent + line

    def _compile_expr(self, line):
        """Compile {_expr}"""
        varname = "_expr"
        source = f"{varname} = {line}"
        self.compile_exec(source)
        code, comment = line.split("#", 1)
        comment = comment.format(**self.envs)
        return "#".join((code, comment))

    def _compile_out(self, line):
        """Compile {_out}"""
        self.compile_exec(line)
        code, comment = line.split("#", 1)
        comment = comment.format(**self.envs, _out=self.stdout)
        return "#".join((code, comment))

    def _compile_exc(self, line, msg=False):
        """Compile {_exc} and {_exc_msg}"""
        varname = "_exc_msg" if msg else "_exc"
        source = (
            f"{varname} = None\n"
            "try:\n"
            f"    {line}"
            "except Exception as exc:\n"
            f"    {varname} = type(exc).__name__"
        )

        if msg:
            source += " + ': ' + str(exc)"
        source += "\n"
        self.compile_exec(source)
        code, comment = line.split("#", 1)
        comment = comment.format(**self.envs)
        return "#".join((code, comment))

    def _compile_hidden(self, line):
        """Compile {_hidden}"""
        self.compile_exec(line)
        return ""

    def _compile_var(self, line):
        """Compile variables"""
        self.compile_exec(line)
        code, comment = line.split("#", 1)
        comment = comment.format(**self.envs)
        return "#".join((code, comment))

    def compile_line(self, line):
        """Compile a single line"""
        code, comment = line.split("#", 1)
        if not code:
            return "#" + comment.format(**self.envs, _out=self.stdout)
        if "{_hidden}" in comment:
            return self._compile_hidden(line)
        if re.search(r"\{_expr(?:!\w+)?\}", comment):
            return self._compile_expr(line)
        if re.search(r"\{_out(?:!\w+)?\}", comment):
            return self._compile_out(line)
        if "{_exc}" in comment:
            return self._compile_exc(line)
        if "{_exc_msg}" in comment:
            return self._compile_exc(line, msg=True)

        return self._compile_var(line)

    def produce(self):
        """Return the produced output"""
        return self.produced

    @classmethod
    def try_open(cls, line, envs, index):
        """Check if a codeblock starts, if so returns the indent,
        backtick number and language, otherwise returns False

        >>> _codeblock_starts("")
        >>> # False
        >>> _codeblock_starts("  ```python")
        >>> # ("  ", 3, "python")
        """
        line = line.rstrip()
        matches = re.match(r"(^\s*)(```[`]*)([\w -]*)$", line)
        if not matches:
            return None

        indent, backticks, lang = (
            matches.group(1),
            matches.group(2),
            matches.group(3),
        )
        return cls(indent, backticks, lang, index, envs)

    def close(self, line):
        """Try to close the codeblock"""
        line = line.rstrip()
        if line == f"{self.indent}{self.backticks}":
            self.alive = False
            if self.codes:
                self.compile_exec(self.codes)
                self.codes = ""
            return True

        return False

    @staticmethod
    def should_compile(line):
        """Whether we should compile a line or treat it as a plain line"""
        if "#" not in line:
            return False

        comment = line.split("#", 1)[1]
        return re.search(r"\{[^}]+\}", comment)


def compile_readme(rawfile):
    """Compile the raw file line by line"""

    codeblock = None

    with open(rawfile) as fraw:
        for line in fraw:
            if codeblock and codeblock.alive:
                if codeblock.close(line):
                    printn(codeblock.produce())
                    printn(line)
                else:
                    codeblock.feed(line)
            else:
                printn(line)
                envs = codeblock.envs if codeblock else None
                index = codeblock.index + 1 if codeblock else 0
                maybe_codeblock = CodeBlock.try_open(line, envs, index)
                if maybe_codeblock:
                    codeblock = maybe_codeblock


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: make-readme.py README.raw.md > README.md")
        sys.exit(1)

    compile_readme(sys.argv[1])
