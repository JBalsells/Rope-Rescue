"""
Tests de integridad del framework: garantizan que el auto-descubrimiento
encuentra las simulaciones y que cada una cumple el contrato (backend válido,
entrypoint invocable, key derivada del módulo). Si alguien suelta una sim mal
decorada en sims/, falla aquí.
"""

import importlib
import pkgutil

import pytest

import registry
import framework
import sims as sims_pkg


def _registered():
    return registry.all_sims()


def test_descubre_todas_las_sims():
    """Hay una sim registrada por cada módulo de sims/ (salvo privados)."""
    en_disco = {m.name for m in pkgutil.iter_modules(sims_pkg.__path__)
                if not m.name.startswith('_')}
    registradas = {s.key for s in _registered()}
    assert registradas == en_disco, (
        f'sin registrar: {en_disco - registradas}; '
        f'de más: {registradas - en_disco}')


def test_keys_unicas():
    ks = registry.keys()
    assert len(ks) == len(set(ks))


def test_backends_validos():
    for s in _registered():
        assert s.backend in registry.VALID_BACKENDS


@pytest.mark.parametrize('sim', _registered(), ids=lambda s: s.key)
def test_entrypoint_invocable(sim):
    assert callable(sim.entrypoint)


@pytest.mark.parametrize('sim', _registered(), ids=lambda s: s.key)
def test_key_coincide_con_modulo(sim):
    """La key se deriva del nombre del módulo (convención del Plugin)."""
    module = importlib.import_module(f'sims.{sim.key}')
    assert module.main is sim.entrypoint


def test_get_desconocida_lanza():
    with pytest.raises(KeyError):
        registry.get('no_existe')


def test_orden_del_menu_es_estable():
    orders = [s.order for s in _registered()]
    assert orders == sorted(orders)


def test_clases_base_exponen_hooks():
    for hook in ('setup', 'handle_event', 'update', 'draw', 'run', 'launch'):
        assert hasattr(framework.PygameSim, hook)
    for hook in ('build', 'redraw', 'run', 'launch'):
        assert hasattr(framework.MplSim, hook)
