# Static Code Analyzer
# Author: Jason Tolbert (https://github.com/jasonalantolbert)
# Python Version: 3.9


import argparse
import ast
import os
import re
from collections import OrderedDict


def line_length_check(line_number, line):
    # lines should be no longer than 79 characters
    if len(line) > 79:
        return line_number, "S001 Too long"


def indentation_check(line_number, line):
    # identation must be a multiple of four
    indents = len(str(line)) - len(str(line).lstrip(" "))
    if indents % 4 != 0 and indents != 0:
        return line_number, "S002 Indentation is not a multiple of four"


def semicolon_check(line_number, line):
    # no semicolons after non-comments
    line = re.sub("(?s)#.*", "", line)
    line = str(line).rstrip(" ")
    if re.search(";$", line):
        return line_number, "S003 Unnecessary semicolon after a statement"


def comment_space_check(line_number, line):
    # at least two spaces before inline comments
    try:
        comment = re.findall("\S *#", line)[0]
        if len(re.findall("( )", comment)) < 2:
            return line_number, "S004 At least two spaces before inline comments required"
    except IndexError:
        pass


def todo_check(line_number, line):
    # no todos
    if re.search("#.*TODO", line, re.IGNORECASE):
        return line_number, "S005 TODO found"


def construction_space_check(line_number, line):
    # no more than one space between def/class and object name
    if re.match("^ *(def|class)", line):
        construction_name = re.findall("(?! )\w*", line)[0]
        if not re.match("^ *(def|class) [\w]", line):
            return line_number, f"S007 Too many spaces after {construction_name}"


def class_case_check(line_number, line):
    # class names should use CamelCase
    if re.match("^class", line):
        class_name = re.sub("^__|__$", "", re.findall("(?! )\w*", line)[1])
        if not re.match("^[A-Z][A-Za-z]*$", class_name):
            return line_number, f"S008 Class name {class_name} should use CamelCase"


def blank_line_check(file):
    # no more than two blank lines between statements
    num_blanks = 0
    blanks_dict = {}
    blank_pattern = re.compile("^\s*$")

    for line_number, line in enumerate(file):
        if num_blanks <= 2:
            if re.match(blank_pattern, line):
                num_blanks += 1
            else:
                num_blanks = 0
        else:
            if not re.match(blank_pattern, line):
                blanks_dict[line_number + 1] = "S006 More than two blank lines used before this line"
                num_blanks = 0
    return blanks_dict


def ast_checks(tree):
    ast_errors_dict = {}
    snake_case = re.compile("^[a-z0-9_]+$")

    def function_case_check(func):
        # function names should be written in snake_case
        if not re.match(snake_case, func.name):
            ast_errors_dict[func.lineno] = f"S009 Function name {func.name} should use snake_case"

    def argument_case_check(agm):
        if not re.match(snake_case, agm.arg):
            # function argument names should be written in snake_case
            ast_errors_dict[agm.lineno] = f"S010 Argument name {agm.arg} should be snake_case"

    def variable_case_check(var):
        try:
            if not re.match(snake_case, var.targets[0].id):
                # variable names should be written in snake_case
                ast_errors_dict[var.lineno] = f"S011 Variable name {var.targets[0].id} should use snake_case"
        except AttributeError:
            pass

    def defval_multability_check(dval):
        # default values for function arguments should not be mutable
        if isinstance(dval, (ast.List, ast.Set, ast.Dict)):
            ast_errors_dict[dval.lineno] = f"S012 Default argument value is mutable"
            return True

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_case_check(node)
        elif isinstance(node, ast.arguments):
            for arg in node.args:
                argument_case_check(arg)
            for defval in node.defaults:
                if defval_multability_check(defval):
                    break
        elif isinstance(node, ast.Assign):
            variable_case_check(node)

    return ast_errors_dict


def check_file(file):
    errors_in_file = {}

    for line_number, line in enumerate(file):
        for check in [line_length_check, indentation_check, semicolon_check, comment_space_check, todo_check,
                      construction_space_check, class_case_check]:
            try:
                ln, msg = check(line_number + 1, line)
                try:
                    errors_in_file[ln]
                except KeyError:
                    errors_in_file[ln] = []
                finally:
                    errors_in_file[ln].append(msg)
            except TypeError:
                continue
    file.seek(0)
    blank_lines = blank_line_check(file)
    for ln, msg in blank_lines.items():
        try:
            errors_in_file[ln]
        except KeyError:
            errors_in_file[ln] = []
        finally:
            errors_in_file[ln].append(msg)
    file.seek(0)
    ast_errors = ast_checks(ast.parse(file.read()))
    for ln, msg in ast_errors.items():
        try:
            errors_in_file[ln]
        except KeyError:
            errors_in_file[ln] = []
        finally:
            errors_in_file[ln].append(msg)

    return errors_in_file


def print_results(all_errors):
    for path, errors_dict in all_errors.items():
        for line, error_list in OrderedDict(sorted(errors_dict.items())).items():
            for error in sorted(error_list):
                print(f"{path}: Line {line}: {error}")


def main():
    all_errors = {}

    parser = argparse.ArgumentParser()
    cli_args = ["path"]
    for arg in cli_args:
        parser.add_argument(arg)
    args = parser.parse_args()

    path = str(args.path)

    if path.endswith(".py"):
        with open(path, "r") as file:
            all_errors[path] = check_file(file)
        print_results(all_errors)
    else:
        for file_name in os.listdir(path):
            if file_name.endswith(".py"):
                with open(f"{path}{os.sep}{file_name}", "r") as file:
                    all_errors[f"{path}{os.sep}{file_name}"] = check_file(file)
        print_results(all_errors)


main()
