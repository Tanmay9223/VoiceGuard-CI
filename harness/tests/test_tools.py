import pytest
from harness.tools import get_quote, _QUOTE_FIXTURES

def test_get_quote_success():
    """Test get_quote with valid vehicle and zip_code."""
    vehicle = "2020 Honda Civic"
    zip_code = "12345"

    quote = get_quote(vehicle, zip_code)

    # Verify the returned quote matches the default fixture but with updated vehicle and zip_code
    assert quote["vehicle"] == vehicle
    assert quote["zip_code"] == zip_code

    # Verify other fields from default fixture
    default_fixture = _QUOTE_FIXTURES["default"]
    assert quote["monthly_premium"] == default_fixture["monthly_premium"]
    assert quote["annual_premium"] == default_fixture["annual_premium"]
    assert quote["coverage"] == default_fixture["coverage"]
    assert quote["deductible"] == default_fixture["deductible"]
    assert quote["disclaimer"] == default_fixture["disclaimer"]

def test_get_quote_missing_vehicle():
    """Test get_quote raises ValueError when vehicle is empty string."""
    with pytest.raises(ValueError, match="get_quote requires both 'vehicle' and 'zip_code' args."):
        get_quote("", "12345")

def test_get_quote_missing_zip_code():
    """Test get_quote raises ValueError when zip_code is empty string."""
    with pytest.raises(ValueError, match="get_quote requires both 'vehicle' and 'zip_code' args."):
        get_quote("2020 Honda Civic", "")

def test_get_quote_none_vehicle():
    """Test get_quote raises ValueError when vehicle is None."""
    with pytest.raises(ValueError, match="get_quote requires both 'vehicle' and 'zip_code' args."):
        get_quote(None, "12345") # type: ignore

def test_get_quote_none_zip_code():
    """Test get_quote raises ValueError when zip_code is None."""
    with pytest.raises(ValueError, match="get_quote requires both 'vehicle' and 'zip_code' args."):
        get_quote("2020 Honda Civic", None) # type: ignore
