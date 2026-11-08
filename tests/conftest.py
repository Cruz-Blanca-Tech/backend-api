"""Registra todos los modelos ORM antes de las pruebas (D32).

Las relaciones de SQLAlchemy se declaran por nombre (p. ej.
`relationship("DocumentItemModel")`). Si una prueba importa solo uno de los
modelos, el mapper no encuentra al otro y la prueba falla al ejecutarse sola,
aunque pase dentro de la suite completa. Importar todos los modelos aquí hace
que cada archivo de pruebas funcione igual solo o acompañado.
"""
import importlib
import pathlib

_SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
for _path in sorted(_SRC.glob("contexts/**/persistence/model*/*.py")):
    if _path.name == "__init__.py":
        continue
    _module = ".".join(_path.relative_to(_SRC.parent).with_suffix("").parts)
    importlib.import_module(_module)
