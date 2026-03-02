"""Load ClickUp field config and client registry for option lookups."""

from app.models.clickup import FieldOption
from app.services.yaml_store import yaml_store


class ClickUpFields:
    """Provides lookups for ClickUp custom field options and project mappings."""

    def __init__(self):
        self._fields_data = None
        self._client_data = None

    def _load(self):
        if self._fields_data is None:
            self._fields_data = yaml_store.read("clickup-fields.yaml")
        if self._client_data is None:
            self._client_data = yaml_store.read("client-registry.yaml")

    def reload(self):
        self._fields_data = None
        self._client_data = None
        self._load()

    @property
    def fields_data(self) -> dict:
        self._load()
        return self._fields_data

    @property
    def client_data(self) -> dict:
        self._load()
        return self._client_data

    def statuses(self) -> list[str]:
        return self.fields_data.get("statuses", [])

    def _get_field(self, field_name: str) -> dict | None:
        for f in self.fields_data.get("custom_fields", []):
            if f["name"] == field_name:
                return f
        return None

    def field_id(self, field_name: str) -> str | None:
        f = self._get_field(field_name)
        return f["field_id"] if f else None

    def options(self, field_name: str) -> list[FieldOption]:
        f = self._get_field(field_name)
        if not f:
            return []
        return [FieldOption(**opt) for opt in f.get("options", [])]

    def option_by_name(self, field_name: str, option_name: str) -> FieldOption | None:
        for opt in self.options(field_name):
            if opt.name.lower() == option_name.lower():
                return opt
        return None

    def option_by_id(self, field_name: str, option_id: str) -> FieldOption | None:
        for opt in self.options(field_name):
            if opt.id == option_id:
                return opt
        return None

    def project_options(self) -> list[FieldOption]:
        return self.options("Project")

    def project_keyword_index(self) -> dict[str, FieldOption]:
        """Build keyword→project mapping from client registry + field options."""
        index: dict[str, FieldOption] = {}
        project_opts = {opt.name.lower(): opt for opt in self.project_options()}

        def _add(keywords: list[str], opt: FieldOption):
            for kw in keywords:
                k = kw.lower().strip()
                if k:
                    index[k] = opt

        # Map each project option name as a keyword for itself
        for opt in self.project_options():
            _add([opt.name], opt)

        # Clients
        for client in self.client_data.get("clients", []):
            proj_name = client.get("clickup_project", "")
            opt = project_opts.get(proj_name.lower())
            if not opt:
                continue
            kws = [client["name"], proj_name]
            # First name as shortcut
            first = client["name"].split()[0]
            kws.append(first)
            # Pen name
            if client.get("pen_name"):
                kws.append(client["pen_name"])
                kws.append(client["pen_name"].split()[0])
            _add(kws, opt)

        # Business lines
        for bl in self.client_data.get("business_lines", []):
            proj_name = bl.get("clickup_project", "")
            opt = project_opts.get(proj_name.lower())
            if not opt:
                continue
            kws = [bl["name"], proj_name]
            _add(kws, opt)

        # Organizations
        for org in self.client_data.get("organizations", []):
            proj_name = org.get("clickup_project", "")
            opt = project_opts.get(proj_name.lower())
            if not opt:
                continue
            kws = [org["name"], proj_name]
            _add(kws, opt)

        # Personal entries
        for p in self.client_data.get("personal", []):
            proj_name = p.get("clickup_project", "")
            opt = project_opts.get(proj_name.lower())
            if not opt:
                continue
            kws = [p["name"], proj_name]
            _add(kws, opt)

        # Hard-coded aliases
        aliases = {
            "prg": "Raging Grannies",
            "grannies": "Raging Grannies",
            "newsletter": "Raging Grannies",
            "tda": "Tomahawk Destiny",
            "tomahawk": "Tomahawk Destiny",
            "hod": "Lynn Haller",
            "hallway": "Lynn Haller",
            "doorknobs": "Lynn Haller",
            "dalton": "Dalton Law",
            "nicole": "Dalton Law",
            "lib": "Lingua Ink Books",
            "lim": "Lingua Ink Media",
            "cohort": "Lingua Ink Cohorts",
            "cohorts": "Lingua Ink Cohorts",
            "courses": "Lingua Ink Courses",
            "course": "Lingua Ink Courses",
            "job": "Job Search",
            "jobs": "Job Search",
            "job search": "Job Search",
            "cat daddies": "Daniela Morescalchi",
            "wren": "Daniela Morescalchi",
        }
        for alias, proj_name in aliases.items():
            opt = project_opts.get(proj_name.lower())
            if opt:
                index[alias] = opt

        return index


# Shared instance
clickup_fields = ClickUpFields()
