from pathlib import Path
import yaml


class Context:
    def __init__(self, verbose: bool = False, spec_path: Path | None = None):
        self.verbose = verbose
        self.cwd = Path.cwd()
        self.home = Path.home()

        resolved_spec_path = spec_path or (
            Path(__file__).resolve().parent.parent / "data" / "life-os.spec.yaml"
        )
        self.spec = self._load_spec(resolved_spec_path)

        fs = self.spec["filesystem"]
        self.workspace = self._expand(fs["workspace"]["path"])
        self.system = self._expand(fs["system"]["path"])
        self.documents = self._expand(fs["documents"]["path"])
        self.desktop = self._expand(fs.get("desktop", {}).get("path", "~/Desktop"))
        self.downloads = self._expand(fs.get("downloads", {}).get("path", "~/Downloads"))

        self.expected_workspace_folders = set(fs["workspace"].get("required_folders", []))
        self.expected_system_folders = set(fs["system"].get("required_folders", []))
        self.expected_documents_folders = set(fs["documents"].get("required_folders", []))
        self.expected_documents_subfolders = fs["documents"].get("subfolders", {})

        self.hygiene = self.spec.get("hygiene", {})

    def _load_spec(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _expand(self, raw: str) -> Path:
        # Expand "~" without relying on shell
        return Path(raw.replace("~", str(self.home)))
