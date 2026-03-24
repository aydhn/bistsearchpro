import pytest
from core.universe import SymbolUniverse

def test_map_symbol_tv():
    universe = SymbolUniverse()
    assert universe.map_symbol("THYAO", source="tv") == "BIST:THYAO"
    assert universe.map_symbol("GARAN", source="TV") == "BIST:GARAN"
    assert universe.map_symbol("ASELS", source="tV") == "BIST:ASELS"

def test_map_symbol_yf():
    universe = SymbolUniverse()
    assert universe.map_symbol("THYAO", source="yf") == "THYAO.IS"
    assert universe.map_symbol("GARAN", source="YF") == "GARAN.IS"
    assert universe.map_symbol("ASELS", source="Yf") == "ASELS.IS"

def test_map_symbol_other():
    universe = SymbolUniverse()
    assert universe.map_symbol("THYAO", source="other") == "THYAO"
    assert universe.map_symbol("GARAN", source="unknown") == "GARAN"
    assert universe.map_symbol("ASELS", source="") == "ASELS"
