import asyncio
import inspect
import time

class TelnetCli(asyncio.Protocol):
    def __init__(self, line_handler):
        self.handle_line = line_handler

    def connection_made(self, transport):
        self.buf = '';
        self.transport = transport

    def data_received(self, data):
        data = data.decode()
        self.buf += data

        lines = self.buf.split('\n')

        for line in lines[:-1]:
            self.transport.write((self.handle_line(line) + "\n").encode('utf-8'))

        self.buf = lines[-1]

def cli_builder(cmds):
    cmds = { f.__name__ : f for f in cmds }

    def handler(line):
        cmd, *args = line.split(' ')

        args = [arg.strip() for arg in args]
        cmd = cmd.strip()

        if cmd in cmds:
            cmd_function = cmds[cmd]
            params_with_parameters = inspect.signature(cmd_function).parameters
            params = []
            num_required = 0
            num_max = 0

            for param in params_with_parameters.values():
                if param.name not in ["args", "kwargs"]:
                    num_max += 1
                    if param.default is inspect._empty:
                        num_required += 1

                    params.append((param.name, param.default, param.annotation))

            if len(args) > num_max or len(args) < num_required:
                help_text = ""
                help_text += f"invalid arguments for command {cmd}, usage info:\n"
                params_help = []
                for name, default, annotation in params:
                    param_help = name

                    if annotation is not inspect._empty:
                        param_help += ": " + annotation.__name__

                    if default is not inspect._empty:
                        param_help += " = " + str(default)

                    params_help.append(param_help)

                help_text += f"{cmd} " + ", ".join(params_help)

                return help_text
            else:
                converted_args = []
                for arg, (param_name, param_default, param_annotation) in zip(args, params):
                    if param_annotation is not inspect._empty:
                        arg = param_annotation(arg)

                    converted_args.append(arg)

                return cmd_function(*converted_args)
        else:
            return f"unknown command {cmd}, available: {', '.join(cmds.keys())}"

    return handler

async def cli_main(cli_handler):
    loop = asyncio.get_running_loop()

    cli_server = await loop.create_server(
        lambda: TelnetCli(cli_handler),
        '127.0.0.1', 8888)

    cli_server_task = asyncio.create_task(cli_server.serve_forever())
    await cli_server_task
