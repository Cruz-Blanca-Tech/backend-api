from dataclasses import dataclass

@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str

    def __post_init__(self):
        if not self.access_token or not self.refresh_token:
            raise ValueError("Ambos tokens son obligatorios para establecer la sesión.")