class LifeOSApp:
    def __init__(self, context):
        self.context = context
        self.commands = {}

    def register(self, name: str, handler):
        self.commands[name] = handler

    def run(self, argv: list[str]) -> None:
        if not argv:
            print("life-os: no command provided")
            return

        name = argv[0]
        cmd_args = argv[1:]

        handler = self.commands.get(name)
        if handler is None:
            print(f"life-os: unknown command '{name}'")
            print(f"available: {', '.join(sorted(self.commands.keys()))}")
            return

        handler(self.context, cmd_args)
